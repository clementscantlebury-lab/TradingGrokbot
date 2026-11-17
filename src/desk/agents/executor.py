"""AGENT 4: EXECUTOR — paper fills only, no live trading."""

from __future__ import annotations

from datetime import datetime

from desk.config import DeskSettings
from desk.models import PaperFill, Position


class ExecutorAgent:
    """Simulates entries with slippage + fees. No wallet, no signing, no Jupiter swaps."""

    def __init__(self, settings: DeskSettings) -> None:
        self.settings = settings

    def can_enter(self, mint: str, positions: dict[str, Position], score: float) -> bool:
        if mint in positions:
            return False
        if score < self.settings.analyst_min_score:
            return False
        return True

    def paper_buy(
        self,
        mint: str,
        symbol: str,
        mark_price: float,
        score: float,
        balance: float,
    ) -> tuple[PaperFill | None, Position | None, float]:
        if mark_price <= 0:
            return None, None, balance

        position_usd = round(balance * self.settings.position_size_pct, 2)
        if position_usd <= 0:
            return None, None, balance

        slip = self.settings.entry_slippage_bps / 10_000.0
        fees = position_usd * slip
        net_deployed = position_usd
        effective_price = mark_price * (1 + slip)

        new_balance = balance - position_usd
        fill = PaperFill(
            mint=mint,
            side="buy",
            size_usd=net_deployed,
            price=mark_price,
            slippage_bps=self.settings.entry_slippage_bps,
            fees_usd=fees,
            score=score,
            timestamp=datetime.utcnow(),
        )
        pos = Position(
            mint=mint,
            symbol=symbol,
            entry_price=mark_price,
            effective_entry_price=effective_price,
            size_usd=net_deployed,
            peak_price=mark_price,
        )
        return fill, pos, new_balance