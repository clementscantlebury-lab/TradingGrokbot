"""AGENT 5: RISK — runs first each cycle."""

from __future__ import annotations

from datetime import datetime
from typing import Callable

from desk.config import DeskSettings
from desk.models import PaperFill, Position
from desk.risk.stops import evaluation_price, exit_proceeds, should_close_position


class RiskAgent:
    def __init__(self, settings: DeskSettings) -> None:
        self.settings = settings

    def manage(
        self,
        positions: dict[str, Position],
        price_fetcher: Callable[[str], float],
        balance: float,
    ) -> tuple[float, list[PaperFill], list[str]]:
        events: list[str] = []
        fills: list[PaperFill] = []

        for mint, pos in list(positions.items()):
            tick = price_fetcher(mint)
            if tick > 0:
                pos.add_price_sample(tick)
            eval_px = evaluation_price(pos, self.settings)
            close, reason, pnl_pct = should_close_position(pos, eval_px, self.settings)
            if not close:
                continue

            proceeds = exit_proceeds(
                pos.size_usd, pnl_pct, self.settings.risk_exit_slippage_bps
            )
            balance += proceeds
            slip_bps = self.settings.risk_exit_slippage_bps
            fill = PaperFill(
                mint=mint,
                side="sell",
                size_usd=proceeds,
                price=eval_px,
                slippage_bps=slip_bps,
                fees_usd=pos.size_usd * (slip_bps / 10_000.0),
                score=0.0,
                timestamp=datetime.utcnow(),
            )
            fills.append(fill)
            del positions[mint]
            events.append(
                f"CLOSED {pos.symbol} ({mint[:8]}…) | {reason} | "
                f"equity +${proceeds:.2f}"
            )

        return balance, fills, events