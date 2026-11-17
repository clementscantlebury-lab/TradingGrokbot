"""Replay mode — run pipeline over recorded JSON snapshots."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterator

from desk.agents.logger import LoggerAgent
from desk.config import DeskSettings
from desk.models import ScannedPair
from desk.orchestrator import TradingDesk


def load_snapshots(directory: str) -> list[list[ScannedPair]]:
    root = Path(directory)
    if not root.exists():
        return []

    batches: list[list[ScannedPair]] = []
    for path in sorted(root.glob("*.json")):
        data = json.loads(path.read_text())
        batch: list[ScannedPair] = []
        for item in data:
            pair = ScannedPair(
                mint=item["mint"],
                symbol=item.get("symbol", "UNK"),
                pair_address=item.get("pair_address", ""),
                source=item.get("source", "replay"),
                price_usd=float(item.get("price_usd", 0)),
                liquidity_usd=float(item.get("liquidity_usd", 0)),
                volume_h1=float(item.get("volume_h1", 0)),
                volume_h24=float(item.get("volume_h24", 0)),
                buys_h1=int(item.get("buys_h1", 0)),
                sells_h1=int(item.get("sells_h1", 0)),
                unique_buyers_h1=item.get("unique_buyers_h1"),
                price_low_1h=item.get("price_low_1h"),
            )
            batch.append(pair)
        batches.append(batch)
    return batches


def replay_desk(
    settings: DeskSettings,
    logger: LoggerAgent,
    snapshots_dir: str | None = None,
) -> None:
    directory = snapshots_dir or settings.replay_snapshots_dir
    batches = load_snapshots(directory)
    desk = TradingDesk(settings)

    if not batches:
        logger.ui.activity.add("REPLAY", f"No snapshots in {directory}")
        return

    for i, batch in enumerate(batches):
        logger.ui.cycle = i + 1

        def source() -> list[ScannedPair]:
            return batch

        desk.run_cycle(logger, pair_source=source)
    logger.print_recap()