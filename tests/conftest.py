import pytest

from desk.config import DeskSettings
from desk.models import FilterContext, ScannedPair


@pytest.fixture
def settings() -> DeskSettings:
    return DeskSettings(
        XAI_API_KEY=None,
        SOLANA_RPC_URL=None,
        FILTER_USE_LEGACY_50K_VOLUME=False,
        CLUSTER_CHECK_REQUIRED=False,
    )


@pytest.fixture
def healthy_pair() -> ScannedPair:
    return ScannedPair(
        mint="Mint111",
        symbol="HEALTH",
        pair_address="p1",
        source="test",
        price_usd=1.0,
        liquidity_usd=100_000,
        volume_h1=25_000,
        buys_h1=60,
        sells_h1=40,
        price_low_1h=0.85,
    )


@pytest.fixture
def safe_ctx() -> FilterContext:
    return FilterContext(
        mint_revoked=True,
        freeze_revoked=True,
        lp_locked_pct=99.0,
        top10_holders_pct=12.0,
        honeypot_sell_ok=True,
        rugcheck_available=True,
        cluster_ok=True,
        insider_bundle_detected=False,
        shared_funding_groups=0,
        fresh_wallet_supply_pct=0.05,
    )