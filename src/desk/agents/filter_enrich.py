"""Build FilterContext from RugCheck + RPC."""

from __future__ import annotations

from desk.clients.rugcheck import RugCheckClient
from desk.clients.solana_rpc import SolanaRpcClient
from desk.config import DeskSettings
from desk.models import FilterContext


class FilterEnricher:
    def __init__(self, settings: DeskSettings) -> None:
        self.rug = RugCheckClient(settings.rugcheck_base_url)
        self.rpc = SolanaRpcClient(settings.solana_rpc_url)

    def build_context(self, mint: str) -> FilterContext:
        ctx = FilterContext()
        ctx = self.rug.apply_to_context(mint, ctx)
        ctx = self.rpc.enrich_mint_authorities(mint, ctx)
        ctx = self.rpc.estimate_top_holders_pct(mint, ctx)
        return ctx