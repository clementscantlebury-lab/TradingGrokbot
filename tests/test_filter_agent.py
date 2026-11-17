from unittest.mock import MagicMock

import pytest

from desk.agents.filter import FilterAgent
from desk.models import FilterContext


@pytest.fixture
def filter_agent(settings):
    enricher = MagicMock()
    enricher.build_context.return_value = FilterContext(
        mint_revoked=True,
        freeze_revoked=True,
        lp_locked_pct=98.0,
        top10_holders_pct=15.0,
        honeypot_sell_ok=True,
        rugcheck_available=True,
        insider_bundle_detected=False,
        shared_funding_groups=0,
        fresh_wallet_supply_pct=0.1,
    )
    return FilterAgent(settings, enricher)


def test_filter_rejects_unverified_mint(filter_agent, healthy_pair, settings):
    filter_agent.enricher.build_context.return_value = FilterContext(
        mint_revoked=None,
        freeze_revoked=True,
        lp_locked_pct=99,
        top10_holders_pct=10,
        honeypot_sell_ok=True,
        rugcheck_available=True,
    )
    r = filter_agent.filter_pair(healthy_pair)
    assert not r.passed
    assert "mint" in r.reason.lower()


def test_filter_passes_complete_context(filter_agent, healthy_pair):
    settings = filter_agent.settings
    settings.cluster_check_required = True
    r = filter_agent.filter_pair(healthy_pair)
    assert r.passed