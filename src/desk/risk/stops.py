"""
Stop evaluation on TWAP / 1m candle closes (PDF §4 fix #2).

Single-tick -6% stops whipsaw on wide-spread new pairs. We evaluate PnL on a
short TWAP window or the latest completed 1-minute close, and apply extra exit
slippage when simulating stop-outs.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

from desk.config import DeskSettings, StopEvalMode
from desk.models import Position


def twap_price(pos: Position, window_sec: int, now: Optional[datetime] = None) -> float:
    now = now or datetime.utcnow()
    cutoff = now - timedelta(seconds=window_sec)
    samples = [(t, p) for t, p in pos.price_samples if t >= cutoff]
    if not samples:
        return pos.peak_price if pos.price_samples else pos.entry_price
    return sum(p for _, p in samples) / len(samples)


def latest_minute_close(pos: Position, now: Optional[datetime] = None) -> float:
    now = now or datetime.utcnow()
    minute_start = now.replace(second=0, microsecond=0)
    samples = [p for t, p in pos.price_samples if t >= minute_start - timedelta(minutes=1)]
    if not samples:
        return twap_price(pos, 60, now)
    return samples[-1]


def evaluation_price(
    pos: Position, settings: DeskSettings, now: Optional[datetime] = None
) -> float:
    mode = settings.risk_stop_eval_mode
    if mode == StopEvalMode.TICK:
        if pos.price_samples:
            return pos.price_samples[-1][1]
        return pos.entry_price
    if mode == StopEvalMode.CANDLE_1M:
        return latest_minute_close(pos, now)
    return twap_price(pos, settings.risk_twap_window_sec, now)


def should_close_position(
    pos: Position,
    eval_price: float,
    settings: DeskSettings,
) -> tuple[bool, str, float]:
    """
    Returns (close?, reason, raw_pnl_pct from effective entry).
    """
    entry = pos.effective_entry_price
    if entry <= 0:
        return False, "", 0.0

    pnl_pct = (eval_price - entry) / entry
    if eval_price > pos.peak_price:
        pos.peak_price = eval_price

    if pnl_pct >= settings.risk_trail_trigger_pct:
        pos.trailing_active = True

    drawdown_from_peak = (eval_price - pos.peak_price) / pos.peak_price if pos.peak_price else 0

    if pnl_pct <= -settings.risk_hard_stop_pct:
        return True, f"hard stop {pnl_pct*100:.2f}%", pnl_pct

    if pos.trailing_active and drawdown_from_peak <= -settings.risk_trail_drawdown_pct:
        return (
            True,
            f"trailing stop (peak drawdown {drawdown_from_peak*100:.2f}%)",
            pnl_pct,
        )

    return False, "", pnl_pct


def exit_proceeds(size_usd: float, pnl_pct: float, exit_slippage_bps: float) -> float:
    gross = size_usd * (1 + pnl_pct)
    slip = exit_slippage_bps / 10_000.0
    return gross * (1 - slip)