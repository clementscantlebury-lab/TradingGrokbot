"""Cluster / RugCheck parsing from mocked JSON."""

from desk.clients.rugcheck import RugCheckClient
from desk.models import FilterContext


MOCK_REPORT = {
    "mintAuthority": None,
    "freezeAuthority": None,
    "lpLockedPct": 100,
    "topHolders": [{"pct": 1.2} for _ in range(10)],
    "risks": [{"name": "Low liquidity", "level": "warn"}],
    "insiderNetworks": [],
    "graphInsiders": [],
    "freshWalletPct": 8,
}


def test_rugcheck_applies_context(monkeypatch):
    client = RugCheckClient("https://api.rugcheck.xyz/v1")

    def fake_get(url, timeout=10):
        class R:
            status_code = 200

            def raise_for_status(self):
                pass

            def json(self):
                return MOCK_REPORT

        return R()

    import requests

    monkeypatch.setattr(requests, "get", fake_get)
    ctx = FilterContext()
    ctx = client.apply_to_context("SomeMint", ctx)
    assert ctx.rugcheck_available
    assert ctx.mint_revoked is True
    assert ctx.freeze_revoked is True
    assert ctx.lp_locked_pct == 100