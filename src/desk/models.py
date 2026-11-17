"""Shared data models for the trading desk pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional


@dataclass
class ScannedPair:
    mint: str
    symbol: str
    pair_address: str
    source: str
    price_usd: float = 0.0
    liquidity_usd: float = 0.0
    volume_h1: float = 0.0
    volume_h24: float = 0.0
    buys_h1: int = 0
    sells_h1: int = 0
    unique_buyers_h1: Optional[int] = None
    price_low_1h: Optional[float] = None
    pair_created_at: Optional[datetime] = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class FilterContext:
    """Enriched on-chain / API fields for deterministic filter."""

    mint_revoked: Optional[bool] = None
    freeze_revoked: Optional[bool] = None
    lp_locked_pct: Optional[float] = None
    top10_holders_pct: Optional[float] = None
    honeypot_sell_ok: Optional[bool] = None
    rugcheck_available: bool = False
    cluster_ok: Optional[bool] = None
    cluster_reason: str = ""
    insider_bundle_detected: bool = False
    shared_funding_groups: int = 0
    fresh_wallet_supply_pct: float = 0.0
    verification_notes: list[str] = field(default_factory=list)


@dataclass
class FilterResult:
    passed: bool
    reason: str
    activity_gate_details: dict[str, Any] = field(default_factory=dict)


@dataclass
class AnalystResult:
    score: float
    rationale: str
    source: str  # "grok" | "rule_based"
    breakdown: dict[str, Any] = field(default_factory=dict)


@dataclass
class PaperFill:
    mint: str
    side: str
    size_usd: float
    price: float
    slippage_bps: float
    fees_usd: float
    score: float
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class Position:
    mint: str
    symbol: str
    entry_price: float
    effective_entry_price: float
    size_usd: float
    peak_price: float
    trailing_active: bool = False
    opened_at: datetime = field(default_factory=datetime.utcnow)
    price_samples: list[tuple[datetime, float]] = field(default_factory=list)

    def add_price_sample(self, price: float, at: Optional[datetime] = None) -> None:
        ts = at or datetime.utcnow()
        self.price_samples.append((ts, price))
        if len(self.price_samples) > 500:
            self.price_samples = self.price_samples[-500:]
        if price > self.peak_price:
            self.peak_price = price