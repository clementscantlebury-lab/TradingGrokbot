"""AGENT 1: SCOUT — discover candidate pairs."""

from __future__ import annotations

from desk.clients.dexscreener import DexScreenerClient
from desk.clients.geckoterminal import GeckoTerminalClient
from desk.config import DeskSettings
from desk.models import ScannedPair


class ScoutAgent:
    def __init__(self, settings: DeskSettings) -> None:
        self.settings = settings
        self.dex = DexScreenerClient(timeout=settings.dexscreener_timeout)
        self.gecko = GeckoTerminalClient(
            settings.gecko_base_url, timeout=settings.dexscreener_timeout
        )

    def scan(self, enrich: bool = True) -> list[ScannedPair]:
        seen: set[str] = set()
        candidates: list[ScannedPair] = []

        for pair in self.dex.fetch_latest_solana_profiles(limit=30):
            key = pair.mint or pair.symbol
            if key in seen:
                continue
            seen.add(key)
            candidates.append(pair)

        for pair in self.gecko.fetch_new_pools(limit=15):
            key = pair.mint or pair.pair_address
            if key in seen:
                continue
            seen.add(key)
            candidates.append(pair)

        if enrich:
            enriched: list[ScannedPair] = []
            for p in candidates:
                if p.mint and len(p.mint) > 20:
                    enriched.append(self.dex.enrich_pair_metrics(p))
                else:
                    enriched.append(p)
            return enriched
        return candidates