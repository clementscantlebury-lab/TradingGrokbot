"""AGENT 6: LOGGER — SQLite + terminal + recap."""

from __future__ import annotations

from typing import Any

from desk.models import AnalystResult, FilterResult, PaperFill, ScannedPair
from desk.storage.db import DeskDatabase
from desk.ui.terminal import TerminalUI


class LoggerAgent:
    def __init__(self, db: DeskDatabase, ui: TerminalUI) -> None:
        self.db = db
        self.ui = ui

    def log_scan(self, pair: ScannedPair) -> None:
        self.db.log_scan(pair)
        self.ui.activity.add("SCOUT", f"{pair.symbol} {pair.mint[:8]}… vol1h=${pair.volume_h1:.0f}")

    def log_rejection(self, mint: str, symbol: str, result: FilterResult) -> None:
        self.db.log_rejection(mint, result)
        self.ui.activity.add("FILTER", f"REJECT {symbol}: {result.reason}")

    def log_analyst(self, mint: str, symbol: str, result: AnalystResult) -> None:
        self.db.log_analyst(mint, result)
        self.ui.activity.add(
            "ANALYST",
            f"{symbol} score={result.score:.2f} ({result.source})",
        )
        self.ui.set_analyst_mode(result.source)

    def log_fill(self, fill: PaperFill, symbol: str = "") -> None:
        self.db.log_fill(fill)
        self.ui.activity.add(
            "EXECUTOR" if fill.side == "buy" else "RISK",
            f"{fill.side.upper()} {symbol or fill.mint[:8]} ${fill.size_usd:.2f}",
        )

    def log_equity(self, balance: float, open_positions: int) -> None:
        self.db.log_equity(balance, open_positions)
        self.ui.balance = balance
        self.ui.positions_count = open_positions
        self.ui.equity_points.append(balance)
        self.ui.refresh()

    def morning_recap(self) -> str:
        r = self.db.recap()
        lines = [
            "=== Morning Recap (Paper Desk) ===",
            f"Pairs scanned: {r['scans']}",
            f"Rejections: {r['rejections']}",
            f"Fills logged: {r['fills']}",
            f"Last equity: ${r['last_balance']:.2f}" if r["last_balance"] else "Last equity: n/a",
            "",
            "Top rejection reasons:",
        ]
        for reason, count in r.get("top_rejection_reasons", []):
            lines.append(f"  - {count}× {reason}")
        return "\n".join(lines)

    def print_recap(self) -> None:
        text = self.morning_recap()
        self.ui.activity.add("LOGGER", "Recap generated")
        print("\n" + text)