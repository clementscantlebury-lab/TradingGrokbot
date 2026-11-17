"""AGENT 2: FILTER — deterministic safety gate, never LLM."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from desk.agents.filter_enrich import FilterEnricher
from desk.config import DeskSettings
from desk.filter.activity_gate import evaluate_activity_gate
from desk.filter.cluster_check import evaluate_holder_cluster
from desk.models import FilterContext, FilterResult, ScannedPair


class FilterAgent:
    LP_MIN_PCT = 95.0
    TOP10_MAX_PCT = 20.0

    def __init__(self, settings: DeskSettings, enricher: FilterEnricher) -> None:
        self.settings = settings
        self.enricher = enricher

    def filter_pair(self, pair: ScannedPair) -> FilterResult:
        activity_ok, activity_reason, activity_details = evaluate_activity_gate(
            pair, self.settings
        )
        if not activity_ok:
            return FilterResult(
                passed=False,
                reason=activity_reason,
                activity_gate_details=activity_details,
            )

        ctx = self.enricher.build_context(pair.mint)

        if ctx.mint_revoked is None:
            return FilterResult(False, "REJECT: mint authority unverified", activity_details)
        if not ctx.mint_revoked:
            return FilterResult(False, "REJECT: mint authority still active", activity_details)

        if ctx.freeze_revoked is None:
            return FilterResult(False, "REJECT: freeze authority unverified", activity_details)
        if not ctx.freeze_revoked:
            return FilterResult(False, "REJECT: freeze authority still active", activity_details)

        if ctx.lp_locked_pct is None:
            return FilterResult(
                False, "REJECT: LP lock/burn percentage unverified", activity_details
            )
        if ctx.lp_locked_pct < self.LP_MIN_PCT:
            return FilterResult(
                False,
                f"REJECT: LP locked/burned {ctx.lp_locked_pct:.1f}% < 95%",
                activity_details,
            )

        if ctx.top10_holders_pct is None:
            return FilterResult(
                False, "REJECT: top-10 holder concentration unverified", activity_details
            )
        if ctx.top10_holders_pct > self.TOP10_MAX_PCT:
            return FilterResult(
                False,
                f"REJECT: top 10 holders {ctx.top10_holders_pct:.1f}% > 20%",
                activity_details,
            )

        if ctx.honeypot_sell_ok is False:
            return FilterResult(False, "REJECT: honeypot/sell check failed", activity_details)
        if ctx.honeypot_sell_ok is None and ctx.rugcheck_available:
            return FilterResult(
                False, "REJECT: honeypot/sell simulation unverified", activity_details
            )

        age_h: Optional[float] = None
        if pair.pair_created_at:
            age_h = (
                datetime.now(timezone.utc) - pair.pair_created_at
            ).total_seconds() / 3600.0

        cluster = evaluate_holder_cluster(ctx, self.settings, age_h)
        if not cluster.ok:
            return FilterResult(
                passed=False,
                reason=cluster.reason,
                activity_gate_details={**activity_details, **cluster.metrics},
            )

        return FilterResult(
            passed=True,
            reason="PASS: all deterministic checks",
            activity_gate_details={**activity_details, "cluster": cluster.reason},
        )