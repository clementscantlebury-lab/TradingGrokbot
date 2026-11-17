from datetime import datetime, timedelta

from desk.config import DeskSettings, StopEvalMode
from desk.models import Position
from desk.risk.stops import (
    evaluation_price,
    exit_proceeds,
    should_close_position,
    twap_price,
)


def test_hard_stop_on_twap_not_single_spike():
    pos = Position(
        mint="m",
        symbol="S",
        entry_price=1.0,
        effective_entry_price=1.015,
        size_usd=22.4,
        peak_price=1.0,
    )
    now = datetime.utcnow()
    pos.price_samples = [
        (now - timedelta(seconds=50), 0.95),
        (now - timedelta(seconds=30), 0.94),
        (now - timedelta(seconds=5), 0.50),
    ]
    settings = DeskSettings(
        RISK_STOP_EVAL_MODE=StopEvalMode.TWAP,
        RISK_TWAP_WINDOW_SEC=60,
        RISK_HARD_STOP_PCT=0.06,
    )
    eval_px = evaluation_price(pos, settings, now)
    assert eval_px > 0.5
    close, reason, pnl = should_close_position(pos, eval_px, settings)
    assert not close or "hard stop" in reason or pnl > -0.06


def test_hard_stop_triggers_on_sustained_loss():
    pos = Position(
        mint="m",
        symbol="S",
        entry_price=1.0,
        effective_entry_price=1.0,
        size_usd=100,
        peak_price=1.0,
    )
    now = datetime.utcnow()
    for i in range(5):
        pos.price_samples.append((now - timedelta(seconds=60 - i * 10), 0.90))
    settings = DeskSettings(RISK_HARD_STOP_PCT=0.06)
    eval_px = evaluation_price(pos, settings, now)
    close, reason, _ = should_close_position(pos, eval_px, settings)
    assert close
    assert "hard stop" in reason


def test_trailing_stop_after_12_percent():
    pos = Position(
        mint="m",
        symbol="S",
        entry_price=1.0,
        effective_entry_price=1.0,
        size_usd=100,
        peak_price=1.20,
        trailing_active=True,
    )
    settings = DeskSettings(
        RISK_TRAIL_TRIGGER_PCT=0.12,
        RISK_TRAIL_DRAWDOWN_PCT=0.06,
    )
    close, reason, _ = should_close_position(pos, 1.10, settings)
    assert close
    assert "trailing" in reason


def test_exit_slippage_reduces_proceeds():
    gross_pnl = 0.10
    proceeds = exit_proceeds(100, gross_pnl, exit_slippage_bps=250)
    assert proceeds < 110
    assert proceeds > 100