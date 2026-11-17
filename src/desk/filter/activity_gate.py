"""
Smarter liquidity/activity gate (PDF §4 fix #1).

The blueprint's fixed $50k 1h volume requirement buys *after* the spike. We use a
composite gate: a lower absolute floor, volume relative to pool liquidity (activity
vs. depth), buy/sell balance, unique buyer proxy, and a guard that price is not
already far above its recent 1h low (parabolic chase filter).
"""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from desk.config import DeskSettings
from desk.models import ScannedPair


def evaluate_activity_gate(
    pair: ScannedPair, settings: DeskSettings
) -> tuple[bool, str, dict[str, Any]]:
    details: dict[str, Any] = {
        "volume_h1": pair.volume_h1,
        "liquidity_usd": pair.liquidity_usd,
        "buys_h1": pair.buys_h1,
        "sells_h1": pair.sells_h1,
    }

    if settings.filter_use_legacy_50k_volume:
        if pair.volume_h1 < 50_000:
            return False, "REJECT: legacy 1h volume under $50k", details
        return True, "PASS: legacy volume gate", details

    if pair.volume_h1 < settings.activity_min_volume_usd_h1:
        return (
            False,
            f"REJECT: 1h volume ${pair.volume_h1:.0f} below floor "
            f"${settings.activity_min_volume_usd_h1:.0f}",
            details,
        )

    liq = max(pair.liquidity_usd, 1.0)
    vol_liq = pair.volume_h1 / liq
    details["vol_to_liq"] = vol_liq
    if vol_liq < settings.activity_min_vol_to_liq_ratio:
        return (
            False,
            f"REJECT: volume/liquidity {vol_liq:.3f} below "
            f"{settings.activity_min_vol_to_liq_ratio}",
            details,
        )

    sells = max(pair.sells_h1, 1)
    buy_sell = pair.buys_h1 / sells
    details["buy_sell_ratio"] = buy_sell
    if buy_sell > settings.activity_max_buy_sell_ratio:
        return (
            False,
            f"REJECT: buy/sell ratio {buy_sell:.2f} suggests one-sided pump",
            details,
        )
    if pair.buys_h1 < settings.activity_min_unique_buyers:
        return (
            False,
            f"REJECT: buys h1 {pair.buys_h1} below min unique buyers "
            f"{settings.activity_min_unique_buyers}",
            details,
        )

    if pair.price_usd > 0 and pair.price_low_1h and pair.price_low_1h > 0:
        extension = (pair.price_usd - pair.price_low_1h) / pair.price_low_1h
        details["price_above_low_pct"] = extension
        if extension > settings.activity_max_price_above_recent_low_pct:
            return (
                False,
                f"REJECT: price {extension*100:.1f}% above 1h low — post-spike entry",
                details,
            )

    details["gate"] = "smart_activity"
    return True, "PASS: smart activity gate", details