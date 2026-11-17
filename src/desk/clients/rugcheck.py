"""RugCheck API client for safety and cluster hints."""

from __future__ import annotations

from typing import Any, Optional

import requests

from desk.models import FilterContext


class RugCheckClient:
    def __init__(self, base_url: str, timeout: float = 12.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def fetch_report(self, mint: str) -> Optional[dict[str, Any]]:
        url = f"{self.base_url}/tokens/{mint}/report"
        try:
            resp = requests.get(url, timeout=self.timeout)
            if resp.status_code == 404:
                return None
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException:
            return None

    def apply_to_context(self, mint: str, ctx: FilterContext) -> FilterContext:
        report = self.fetch_report(mint)
        if not report:
            ctx.verification_notes.append("rugcheck_unavailable")
            return ctx
        ctx.rugcheck_available = True

        token = report.get("token") or report
        mint_auth = token.get("mintAuthority") or report.get("mintAuthority")
        freeze_auth = token.get("freezeAuthority") or report.get("freezeAuthority")
        ctx.mint_revoked = mint_auth is None
        ctx.freeze_revoked = freeze_auth is None

        markets = report.get("markets") or []
        lp_locked = 0.0
        for m in markets:
            lp = m.get("lp") or {}
            if lp.get("lpLockedPct") is not None:
                lp_locked = max(lp_locked, float(lp.get("lpLockedPct", 0)))
        if lp_locked == 0 and report.get("lpLockedPct") is not None:
            lp_locked = float(report["lpLockedPct"])
        if lp_locked:
            ctx.lp_locked_pct = lp_locked

        top_holders = report.get("topHolders") or report.get("top_holders") or []
        if top_holders:
            total_pct = 0.0
            for h in top_holders[:10]:
                pct = h.get("pct") or h.get("percentage") or h.get("uiAmount", 0)
                try:
                    total_pct += float(pct)
                except (TypeError, ValueError):
                    pass
            if total_pct > 0:
                ctx.top10_holders_pct = total_pct

        risks = report.get("risks") or []
        for r in risks:
            name = (r.get("name") or r.get("description") or "").lower()
            if "honeypot" in name or "sell" in name:
                level = (r.get("level") or "").lower()
                ctx.honeypot_sell_ok = level not in ("danger", "critical", "high")

        insider = report.get("insiderNetworks") or report.get("insider") or []
        if insider:
            ctx.insider_bundle_detected = len(insider) > 0

        graph = report.get("graphInsiders") or report.get("bundled") or []
        if graph:
            ctx.shared_funding_groups = max(ctx.shared_funding_groups, len(graph))

        fresh_pct = report.get("freshWalletPct") or report.get("newWalletHoldingPct")
        if fresh_pct is not None:
            try:
                ctx.fresh_wallet_supply_pct = float(fresh_pct) / (
                    100.0 if float(fresh_pct) > 1 else 1.0
                )
            except (TypeError, ValueError):
                pass

        return ctx