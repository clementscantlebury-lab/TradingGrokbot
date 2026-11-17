"""Rich live terminal dashboard."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import Deque

from rich.console import Group
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text


@dataclass
class ActivityLog:
    lines: Deque[str] = field(default_factory=lambda: deque(maxlen=18))

    def add(self, agent: str, message: str) -> None:
        ts = datetime.utcnow().strftime("%H:%M:%S")
        self.lines.appendleft(f"[{ts}] [{agent}] {message}")


class TerminalUI:
    def __init__(self, starting_balance: float, paper_only: bool = True) -> None:
        self.balance = starting_balance
        self.starting_balance = starting_balance
        self.activity = ActivityLog()
        self.equity_points: list[float] = [starting_balance]
        self.grok_label = "Grok"
        self.positions_count = 0
        self.cycle = 0
        self._live: Live | None = None

    def set_analyst_mode(self, source: str) -> None:
        self.grok_label = "Grok" if source == "grok" else "Rule-based Analyst"

    def render(self) -> Layout:
        layout = Layout()
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="body", ratio=2),
            Layout(name="footer", size=10),
        )
        mode = "PAPER ONLY — NO LIVE TRADING"
        hdr = Text(
            f"Solana Memecoin Desk | {mode} | Balance: ${self.balance:.2f} | "
            f"Positions: {self.positions_count} | Cycle: {self.cycle} | Analyst: {self.grok_label}",
            style="bold green",
        )
        layout["header"].update(Panel(hdr))

        eq_table = Table(title="Equity curve (recent)")
        eq_table.add_column("Point")
        eq_table.add_column("USD")
        for i, v in enumerate(self.equity_points[-12:], start=1):
            eq_table.add_row(str(i), f"{v:.2f}")

        pnl = self.balance - self.starting_balance
        stats = Panel(
            f"Starting: ${self.starting_balance:.2f}\n"
            f"P&L: ${pnl:+.2f} ({(pnl/self.starting_balance)*100:+.2f}%)\n"
            f"Open positions: {self.positions_count}",
            title="Account",
        )
        layout["body"].split_row(Layout(stats), Layout(eq_table))

        act = "\n".join(self.activity.lines) or "(waiting for activity)"
        layout["footer"].update(Panel(act, title="Agent activity"))
        return layout

    def start_live(self) -> Live:
        self._live = Live(self.render(), refresh_per_second=2)
        return self._live

    def refresh(self) -> None:
        if self._live:
            self._live.update(self.render())