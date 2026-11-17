"""CLI entry — paper trading only."""

from __future__ import annotations

import argparse
import sys

from desk.agents.logger import LoggerAgent
from desk.config import load_settings
from desk.orchestrator import TradingDesk
from desk.replay import replay_desk
from desk.storage.db import DeskDatabase
from desk.ui.terminal import TerminalUI


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Solana memecoin paper trading desk (no live trading)"
    )
    parser.add_argument(
        "--cycles",
        type=int,
        default=None,
        help="Stop after N cycles (default: run until SIGINT)",
    )
    parser.add_argument(
        "--replay",
        action="store_true",
        help="Run from fixtures/replay JSON snapshots",
    )
    parser.add_argument(
        "--no-live-ui",
        action="store_true",
        help="Disable Rich live display",
    )
    parser.add_argument(
        "--recap-only",
        action="store_true",
        help="Print SQLite morning recap and exit",
    )
    args = parser.parse_args(argv)

    settings = load_settings()
    if not settings.paper_mode_only:
        print("FATAL: Live trading is not supported.", file=sys.stderr)
        return 1

    db = DeskDatabase(settings.sqlite_path)
    ui = TerminalUI(settings.starting_balance, paper_only=True)
    logger = LoggerAgent(db, ui)

    if args.recap_only:
        print(logger.morning_recap())
        return 0

    if args.replay:
        replay_desk(settings, logger)
        return 0

    desk = TradingDesk(settings)
    print(
        "Starting PAPER-ONLY desk. No wallet keys. "
        f"Grok: {'ON' if settings.grok_available else 'OFF (rule-based analyst)'}"
    )
    try:
        desk.run_loop(
            logger,
            max_cycles=args.cycles,
            use_live_display=not args.no_live_ui,
        )
    finally:
        print(logger.morning_recap())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())