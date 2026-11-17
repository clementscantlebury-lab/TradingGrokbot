from desk.agents.executor import ExecutorAgent
from desk.config import DeskSettings


def test_position_size_eight_percent():
    settings = DeskSettings(POSITION_SIZE_PCT=0.08, ANALYST_MIN_SCORE=0.6)
    ex = ExecutorAgent(settings)
    fill, pos, bal = ex.paper_buy("mint", "SYM", 1.0, 0.75, 280.0)
    assert fill is not None
    assert pos is not None
    assert fill.size_usd == round(280 * 0.08, 2)
    assert bal == 280.0 - fill.size_usd


def test_no_reentry():
    from desk.models import Position

    settings = DeskSettings()
    ex = ExecutorAgent(settings)
    positions = {
        "mint": Position(
            mint="mint",
            symbol="S",
            entry_price=1,
            effective_entry_price=1,
            size_usd=10,
            peak_price=1,
        )
    }
    assert not ex.can_enter("mint", positions, 0.9)


def test_no_live_trading_path():
    settings = DeskSettings()
    assert settings.paper_mode_only is True