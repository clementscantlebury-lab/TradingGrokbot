"""Environment-backed configuration for all agents and vulnerability fixes."""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class StopEvalMode(str, Enum):
    TWAP = "twap"
    CANDLE_1M = "candle_1m"
    TICK = "tick"


class DeskSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    xai_api_key: Optional[str] = Field(default=None, alias="XAI_API_KEY")
    solana_rpc_url: Optional[str] = Field(default=None, alias="SOLANA_RPC_URL")

    starting_balance: float = Field(default=280.0, alias="STARTING_BALANCE")
    cycle_interval_sec: int = Field(default=60, alias="CYCLE_INTERVAL_SEC")
    analyst_min_score: float = Field(default=0.6, alias="ANALYST_MIN_SCORE")

    activity_min_volume_usd_h1: float = Field(
        default=8000.0, alias="ACTIVITY_MIN_VOLUME_USD_H1"
    )
    activity_min_vol_to_liq_ratio: float = Field(
        default=0.15, alias="ACTIVITY_MIN_VOL_TO_LIQ_RATIO"
    )
    activity_max_buy_sell_ratio: float = Field(
        default=4.0, alias="ACTIVITY_MAX_BUY_SELL_RATIO"
    )
    activity_min_unique_buyers: int = Field(
        default=25, alias="ACTIVITY_MIN_UNIQUE_BUYERS"
    )
    activity_max_price_above_recent_low_pct: float = Field(
        default=0.45, alias="ACTIVITY_MAX_PRICE_ABOVE_RECENT_LOW_PCT"
    )
    filter_use_legacy_50k_volume: bool = Field(
        default=False, alias="FILTER_USE_LEGACY_50K_VOLUME"
    )

    risk_stop_eval_mode: StopEvalMode = Field(
        default=StopEvalMode.TWAP, alias="RISK_STOP_EVAL_MODE"
    )
    risk_twap_window_sec: int = Field(default=60, alias="RISK_TWAP_WINDOW_SEC")
    risk_exit_slippage_bps: float = Field(default=250.0, alias="RISK_EXIT_SLIPPAGE_BPS")
    risk_hard_stop_pct: float = Field(default=0.06, alias="RISK_HARD_STOP_PCT")
    risk_trail_trigger_pct: float = Field(default=0.12, alias="RISK_TRAIL_TRIGGER_PCT")
    risk_trail_drawdown_pct: float = Field(default=0.06, alias="RISK_TRAIL_DRAWDOWN_PCT")

    cluster_check_required: bool = Field(default=True, alias="CLUSTER_CHECK_REQUIRED")
    cluster_max_fresh_wallets_pct: float = Field(
        default=0.25, alias="CLUSTER_MAX_FRESH_WALLETS_PCT"
    )
    cluster_max_shared_funding_groups: int = Field(
        default=3, alias="CLUSTER_MAX_SHARED_FUNDING_GROUPS"
    )
    cluster_wallet_age_max_hours: int = Field(
        default=48, alias="CLUSTER_WALLET_AGE_MAX_HOURS"
    )

    position_size_pct: float = Field(default=0.08, alias="POSITION_SIZE_PCT")
    entry_slippage_bps: float = Field(default=150.0, alias="ENTRY_SLIPPAGE_BPS")

    sqlite_path: str = Field(default="./data/desk.sqlite", alias="SQLITE_PATH")
    replay_snapshots_dir: str = Field(
        default="./fixtures/replay", alias="REPLAY_SNAPSHOTS_DIR"
    )

    dexscreener_timeout: float = 10.0
    rugcheck_base_url: str = "https://api.rugcheck.xyz/v1"
    gecko_base_url: str = "https://api.geckoterminal.com/api/v2"
    xai_base_url: str = "https://api.x.ai/v1"

    @property
    def paper_mode_only(self) -> bool:
        """Desk never supports live trading."""
        return True

    @property
    def grok_available(self) -> bool:
        return bool(self.xai_api_key and self.xai_api_key.strip())

    @property
    def rpc_available(self) -> bool:
        return bool(self.solana_rpc_url and self.solana_rpc_url.strip())


def load_settings() -> DeskSettings:
    return DeskSettings()