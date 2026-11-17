"""DexScreener public API client."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import requests

from desk.models import ScannedPair


def _safe_float(val: Any, default: float = 0.0) -> float:
    try:
        if val is None:
            return default
        return float(val)
    except (TypeError, ValueError):
        return default


class DexScreenerClient:
    LATEST_PROFILES = "https://api.dexscreener.com/token-profiles/latest/v1"
    TOKEN_PAIRS = "https://api.dexscreener.com/token-pairs/v1/solana/{mint}"

    def __init__(self, timeout: float = 10.0) -> None:
        self.timeout = timeout

    def fetch_latest_solana_profiles(self, limit: int = 30) -> list[ScannedPair]:
        resp = requests.get(self.LATEST_PROFILES, timeout=self.timeout)
        resp.raise_for_status()
        data = resp.json()
        if not isinstance(data, list):
            return []
        out: list[ScannedPair] = []
        for item in data:
            if item.get("chainId") != "solana":
                continue
            mint = item.get("tokenAddress") or item.get("address") or ""
            if not mint:
                continue
            symbol = (item.get("symbol") or item.get("name") or mint[:8]).upper()
            pair = ScannedPair(
                mint=mint,
                symbol=symbol,
                pair_address="",
                source="dexscreener:profiles",
                raw=item,
            )
            out.append(pair)
            if len(out) >= limit:
                break
        return out

    def enrich_pair_metrics(self, pair: ScannedPair) -> ScannedPair:
        url = self.TOKEN_PAIRS.format(mint=pair.mint)
        try:
            resp = requests.get(url, timeout=self.timeout)
            resp.raise_for_status()
            pairs = resp.json()
        except requests.RequestException:
            return pair
        if not isinstance(pairs, list) or not pairs:
            return pair
        best = max(
            pairs,
            key=lambda p: _safe_float((p.get("liquidity") or {}).get("usd")),
        )
        pair.pair_address = best.get("pairAddress") or pair.pair_address
        pair.price_usd = _safe_float(best.get("priceUsd"))
        liq = best.get("liquidity") or {}
        pair.liquidity_usd = _safe_float(liq.get("usd"))
        vol = best.get("volume") or {}
        pair.volume_h1 = _safe_float(vol.get("h1"))
        pair.volume_h24 = _safe_float(vol.get("h24"))
        txns = best.get("txns") or {}
        h1 = txns.get("h1") or {}
        pair.buys_h1 = int(h1.get("buys") or 0)
        pair.sells_h1 = int(h1.get("sells") or 0)
        chg = best.get("priceChange") or {}
        if chg.get("h1") is not None:
            pct = _safe_float(chg.get("h1")) / 100.0
            if pair.price_usd and pct:
                pair.price_low_1h = pair.price_usd / (1 + max(pct, 0.0001))
        created = best.get("pairCreatedAt")
        if created:
            try:
                ms = int(created)
                pair.pair_created_at = datetime.fromtimestamp(ms / 1000, tz=timezone.utc)
            except (TypeError, ValueError):
                pass
        pair.unique_buyers_h1 = pair.buys_h1
        pair.raw["dex_pair"] = best
        return pair