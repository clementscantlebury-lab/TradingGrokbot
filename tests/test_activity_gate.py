from desk.config import DeskSettings
from desk.filter.activity_gate import evaluate_activity_gate
from desk.models import ScannedPair


def test_rejects_low_volume(healthy_pair):
    healthy_pair.volume_h1 = 1000
    settings = DeskSettings()
    ok, reason, _ = evaluate_activity_gate(healthy_pair, settings)
    assert not ok
    assert "volume" in reason.lower()


def test_rejects_parabolic_extension(healthy_pair):
    healthy_pair.price_usd = 2.0
    healthy_pair.price_low_1h = 1.0
    settings = DeskSettings(ACTIVITY_MAX_PRICE_ABOVE_RECENT_LOW_PCT=0.45)
    ok, reason, details = evaluate_activity_gate(healthy_pair, settings)
    assert not ok
    assert "post-spike" in reason.lower()
    assert details["price_above_low_pct"] == 1.0


def test_passes_smart_gate(healthy_pair):
    settings = DeskSettings()
    ok, reason, details = evaluate_activity_gate(healthy_pair, settings)
    assert ok
    assert details.get("gate") == "smart_activity"


def test_legacy_50k_mode():
    pair = ScannedPair(
        mint="x", symbol="Y", pair_address="", source="t",
        volume_h1=49_000, liquidity_usd=100_000, buys_h1=100, sells_h1=10,
        price_usd=1, price_low_1h=0.95,
    )
    settings = DeskSettings(FILTER_USE_LEGACY_50K_VOLUME=True)
    ok, reason, _ = evaluate_activity_gate(pair, settings)
    assert not ok
    assert "50k" in reason.lower()