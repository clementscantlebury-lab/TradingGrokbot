"""Minimal Solana JSON-RPC for mint account verification."""

from __future__ import annotations

from typing import Any, Optional

import requests

from desk.models import FilterContext


class SolanaRpcClient:
    def __init__(self, rpc_url: Optional[str], timeout: float = 10.0) -> None:
        self.rpc_url = rpc_url
        self.timeout = timeout

    @property
    def available(self) -> bool:
        return bool(self.rpc_url)

    def _rpc(self, method: str, params: list[Any]) -> Optional[Any]:
        if not self.rpc_url:
            return None
        body = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params}
        try:
            resp = requests.post(self.rpc_url, json=body, timeout=self.timeout)
            resp.raise_for_status()
            data = resp.json()
            if "error" in data:
                return None
            return data.get("result")
        except requests.RequestException:
            return None

    def enrich_mint_authorities(self, mint: str, ctx: FilterContext) -> FilterContext:
        if not self.available:
            ctx.verification_notes.append("rpc_unavailable")
            return ctx
        result = self._rpc(
            "getAccountInfo",
            [mint, {"encoding": "jsonParsed"}],
        )
        if not result or not result.get("value"):
            ctx.verification_notes.append("rpc_mint_account_missing")
            return ctx
        parsed = (result["value"].get("data") or {}).get("parsed") or {}
        info = parsed.get("info") or {}
        mint_auth = info.get("mintAuthority")
        freeze_auth = info.get("freezeAuthority")
        if ctx.mint_revoked is None:
            ctx.mint_revoked = mint_auth is None
        if ctx.freeze_revoked is None:
            ctx.freeze_revoked = freeze_auth is None
        ctx.verification_notes.append("rpc_mint_checked")
        return ctx

    def estimate_top_holders_pct(self, mint: str, ctx: FilterContext) -> FilterContext:
        """Best-effort via largest token accounts — may be incomplete without indexer."""
        if not self.available or ctx.top10_holders_pct is not None:
            return ctx
        result = self._rpc(
            "getTokenLargestAccounts",
            [mint],
        )
        if not result or not result.get("value"):
            return ctx
        accounts = result["value"][:10]
        supply_result = self._rpc(
            "getAccountInfo",
            [mint, {"encoding": "jsonParsed"}],
        )
        supply = 0.0
        if supply_result and supply_result.get("value"):
            info = (
                (supply_result["value"].get("data") or {})
                .get("parsed", {})
                .get("info", {})
            )
            supply = float(info.get("supply") or info.get("decimals") and 0 or 0)
            try:
                supply = float(info.get("supply", 0))
                decimals = int(info.get("decimals", 0))
                supply = supply / (10**decimals) if supply > 10**decimals else supply
            except (TypeError, ValueError):
                supply = 0.0
        held = 0.0
        for acc in accounts:
            try:
                amt = float((acc.get("uiAmount") or acc.get("amount") or 0))
                held += amt
            except (TypeError, ValueError):
                pass
        if supply > 0 and held > 0:
            ctx.top10_holders_pct = min(100.0, (held / supply) * 100.0)
            ctx.verification_notes.append("rpc_top_holders_estimate")
        return ctx