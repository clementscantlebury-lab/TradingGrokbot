"""GeckoTerminal public API — trending Solana pools."""

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


class GeckoTerminalClient:
    def __init__(self, base_url: str, timeout: float = 10.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def fetch_new_pools(self, limit: int = 20) -> list[ScannedPair]:
        url = f"{self.base_url}/networks/solana/new_pools"
        try:
            resp = requests.get(url, timeout=self.timeout)
            resp.raise_for_status()
            payload = resp.json()
        except requests.RequestException:
            return []
        data = payload.get("data") or []
        out: list[ScannedPair] = []
        for item in data[:limit]:
            attrs = item.get("attributes") or {}
            relationships = item.get("relationships") or {}
            base = relationships.get("base_token") or {}
            base_data = base.get("data") or {}
            mint = (attrs.get("address") or base_data.get("id") or "").split("_")[-1]
            if not mint or len(mint) < 32:
                mint = attrs.get("name", "")[:44]
            symbol = (attrs.get("name") or "UNK").split("/")[0].strip().upper()
            pair = ScannedPair(
                mint=mint if mint.startswith("http") is False else "",
                symbol=symbol,
                pair_address=attrs.get("address") or "",
                source="geckoterminal:new_pools",
                price_usd=_safe_float(attrs.get("base_token_price_usd")),
                liquidity_usd=_safe_float(attrs.get("reserve_in_usd")),
                volume_h1=_safe_float(attrs.get("volume_usd", {}).get("h1")
                if isinstance(attrs.get("volume_usd"), dict)
                else attrs.get("volume_usd")),
                raw=item,
            )
            if pair.mint:
                out.append(pair)
        return out

    def fetch_trending_pools(self, limit: int = 15) -> list[ScannedPair]:
        url = f"{self.base_url}/networks/solana/trending_pools"
        try:
            resp = requests.get(url, timeout=self.timeout)
            resp.raise_for_status()
            payload = resp.json()
        except requests.RequestException:
            return []
        data = payload.get("data") or []
        out: list[ScannedPair] = []
        for item in data[:limit]:
            attrs = item.get("attributes") or {}
            name = attrs.get("name") or ""
            symbol = name.split("/")[0].strip().upper() if name else "UNK"
            pair_addr = attrs.get("address") or ""
            vol = attrs.get("volume_usd") or {}
            pair = ScannedPair(
                mint=pair_addr,
                symbol=symbol,
                pair_address=pair_addr,
                source="geckoterminal:trending",
                price_usd=_safe_float(attrs.get("base_token_price_usd")),
                liquidity_usd=_safe_float(attrs.get("reserve_in_usd")),
                volume_h1=_safe_float(vol.get("h1") if isinstance(vol, dict) else vol),
                pair_created_at=datetime.now(timezone.utc),
                raw=item,
            )
            if pair.pair_address:
                out.append(pair)
        return out