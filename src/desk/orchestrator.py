"""Pipeline orchestration — RISK first, then SCOUT → FILTER → ANALYST → EXECUTOR."""

from __future__ import annotations

import signal
import time
from typing import Callable, Optional

from desk.agents.analyst import AnalystAgent
from desk.agents.executor import ExecutorAgent
from desk.agents.filter import FilterAgent
from desk.agents.filter_enrich import FilterEnricher
from desk.agents.logger import LoggerAgent
from desk.agents.risk import RiskAgent
from desk.agents.scout import ScoutAgent
from desk.clients.dexscreener import DexScreenerClient
from desk.config import DeskSettings
from desk.models import Position, ScannedPair


class TradingDesk:
    def __init__(self, settings: DeskSettings) -> None:
        self.settings = settings
        self.balance = settings.starting_balance
        self.positions: dict[str, Position] = {}
        self.scout = ScoutAgent(settings)
        self.enricher = FilterEnricher(settings)
        self.filter = FilterAgent(settings, self.enricher)
        self.analyst = AnalystAgent(settings)
        self.executor = ExecutorAgent(settings)
        self.risk = RiskAgent(settings)
        self.dex = DexScreenerClient(timeout=settings.dexscreener_timeout)
        self._stop = False

    def request_stop(self) -> None:
        self._stop = True

    def _price_for(self, mint: str) -> float:
        pair_stub = ScannedPair(mint=mint, symbol="", pair_address="", source="")
        enriched = self.dex.enrich_pair_metrics(pair_stub)
        return enriched.price_usd

    def run_cycle(self, logger: LoggerAgent, pair_source: Optional[Callable[[], list[ScannedPair]]] = None) -> None:
        self.balance, risk_fills, risk_events = self.risk.manage(
            self.positions, self._price_for, self.balance
        )
        for ev in risk_events:
            logger.ui.activity.add("RISK", ev)
        for fill in risk_fills:
            logger.log_fill(fill)

        logger.log_equity(self.balance, len(self.positions))

        candidates = pair_source() if pair_source else self.scout.scan(enrich=True)
        logger.ui.activity.add("SCOUT", f"{len(candidates)} candidates")

        for pair in candidates:
            if not pair.mint:
                continue
            logger.log_scan(pair)
            fresult = self.filter.filter_pair(pair)
            if not fresult.passed:
                logger.log_rejection(pair.mint, pair.symbol, fresult)
                continue

            aresult = self.analyst.score(pair, fresult.activity_gate_details)
            logger.log_analyst(pair.mint, pair.symbol, aresult)
            if aresult.score < self.settings.analyst_min_score:
                logger.ui.activity.add(
                    "ANALYST",
                    f"NO TRADE {pair.symbol} (< {self.settings.analyst_min_score})",
                )
                continue

            if not self.executor.can_enter(pair.mint, self.positions, aresult.score):
                continue

            fill, pos, self.balance = self.executor.paper_buy(
                pair.mint,
                pair.symbol,
                pair.price_usd,
                aresult.score,
                self.balance,
            )
            if fill and pos:
                self.positions[pair.mint] = pos
                logger.log_fill(fill, pair.symbol)
                logger.log_equity(self.balance, len(self.positions))

    def run_loop(
        self,
        logger: LoggerAgent,
        max_cycles: Optional[int] = None,
        use_live_display: bool = True,
    ) -> None:
        cycles = 0
        live_ctx = logger.ui.start_live() if use_live_display else None

        def handle_sig(*_args) -> None:
            self.request_stop()

        signal.signal(signal.SIGINT, handle_sig)
        signal.signal(signal.SIGTERM, handle_sig)

        try:
            if live_ctx:
                live_ctx.start()
            while not self._stop:
                logger.ui.cycle = cycles + 1
                self.run_cycle(logger)
                cycles += 1
                if max_cycles and cycles >= max_cycles:
                    break
                time.sleep(self.settings.cycle_interval_sec)
        finally:
            if live_ctx:
                live_ctx.stop()