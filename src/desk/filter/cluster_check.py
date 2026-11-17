"""
Holder cluster / bundled insider detection (PDF §4 fix #3).

Sophisticated rugs split supply across many fresh wallets (<1.5% each) so top-10
checks pass. We require a verifiable cluster assessment from RugCheck insider/bundle
fields and optional RPC age heuristics. If the check cannot be performed and
CLUSTER_CHECK_REQUIRED is true, reject.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from desk.config import DeskSettings
from desk.models import FilterContext


@dataclass
class ClusterVerdict:
    ok: bool
    performed: bool
    reason: str
    metrics: dict[str, Any]


def evaluate_holder_cluster(
    ctx: FilterContext,
    settings: DeskSettings,
    pair_age_hours: Optional[float] = None,
) -> ClusterVerdict:
    metrics: dict[str, Any] = {
        "fresh_wallet_supply_pct": ctx.fresh_wallet_supply_pct,
        "shared_funding_groups": ctx.shared_funding_groups,
        "insider_bundle_detected": ctx.insider_bundle_detected,
        "rugcheck_available": ctx.rugcheck_available,
    }

    performed = ctx.rugcheck_available or ctx.shared_funding_groups > 0

    if not performed:
        if settings.cluster_check_required:
            return ClusterVerdict(
                ok=False,
                performed=False,
                reason="REJECT: cluster check not performed (no RugCheck/insider data)",
                metrics=metrics,
            )
        return ClusterVerdict(
            ok=True,
            performed=False,
            reason="SKIP: cluster optional and data missing",
            metrics=metrics,
        )

    if ctx.insider_bundle_detected:
        return ClusterVerdict(
            ok=False,
            performed=True,
            reason="REJECT: RugCheck insider/bundle network detected",
            metrics=metrics,
        )

    if ctx.shared_funding_groups > settings.cluster_max_shared_funding_groups:
        return ClusterVerdict(
            ok=False,
            performed=True,
            reason=(
                f"REJECT: {ctx.shared_funding_groups} shared funding groups "
                f"> max {settings.cluster_max_shared_funding_groups}"
            ),
            metrics=metrics,
        )

    if ctx.fresh_wallet_supply_pct > settings.cluster_max_fresh_wallets_pct:
        return ClusterVerdict(
            ok=False,
            performed=True,
            reason=(
                f"REJECT: fresh wallets hold {ctx.fresh_wallet_supply_pct*100:.1f}% "
                f"> max {settings.cluster_max_fresh_wallets_pct*100:.1f}%"
            ),
            metrics=metrics,
        )

    return ClusterVerdict(
        ok=True,
        performed=True,
        reason="PASS: cluster check",
        metrics=metrics,
    )