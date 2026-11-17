from desk.config import DeskSettings
from desk.filter.cluster_check import evaluate_holder_cluster
from desk.models import FilterContext


def test_rejects_when_cluster_required_but_not_performed():
    ctx = FilterContext(rugcheck_available=False)
    settings = DeskSettings(CLUSTER_CHECK_REQUIRED=True)
    v = evaluate_holder_cluster(ctx, settings)
    assert not v.ok
    assert not v.performed


def test_rejects_insider_bundle():
    ctx = FilterContext(rugcheck_available=True, insider_bundle_detected=True)
    settings = DeskSettings(CLUSTER_CHECK_REQUIRED=True)
    v = evaluate_holder_cluster(ctx, settings)
    assert not v.ok
    assert "insider" in v.reason.lower()


def test_rejects_too_many_funding_groups():
    ctx = FilterContext(
        rugcheck_available=True,
        shared_funding_groups=10,
        insider_bundle_detected=False,
        fresh_wallet_supply_pct=0.05,
    )
    settings = DeskSettings(
        CLUSTER_CHECK_REQUIRED=True,
        CLUSTER_MAX_SHARED_FUNDING_GROUPS=3,
    )
    v = evaluate_holder_cluster(ctx, settings)
    assert not v.ok


def test_passes_clean_cluster():
    ctx = FilterContext(
        rugcheck_available=True,
        insider_bundle_detected=False,
        shared_funding_groups=1,
        fresh_wallet_supply_pct=0.05,
    )
    settings = DeskSettings(CLUSTER_CHECK_REQUIRED=True)
    v = evaluate_holder_cluster(ctx, settings)
    assert v.ok and v.performed