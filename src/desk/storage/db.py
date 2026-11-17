"""SQLite persistence for LOGGER agent."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from desk.models import AnalystResult, FilterResult, PaperFill, ScannedPair


class DeskDatabase:
    def __init__(self, path: str) -> None:
        self.path = path
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS scans (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts TEXT NOT NULL,
                    mint TEXT,
                    symbol TEXT,
                    source TEXT,
                    payload TEXT
                );
                CREATE TABLE IF NOT EXISTS rejections (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts TEXT NOT NULL,
                    mint TEXT,
                    reason TEXT,
                    details TEXT
                );
                CREATE TABLE IF NOT EXISTS analyst (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts TEXT NOT NULL,
                    mint TEXT,
                    score REAL,
                    source TEXT,
                    rationale TEXT,
                    breakdown TEXT
                );
                CREATE TABLE IF NOT EXISTS fills (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts TEXT NOT NULL,
                    mint TEXT,
                    side TEXT,
                    size_usd REAL,
                    price REAL,
                    slippage_bps REAL,
                    fees_usd REAL,
                    score REAL
                );
                CREATE TABLE IF NOT EXISTS equity (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts TEXT NOT NULL,
                    balance REAL,
                    open_positions INTEGER
                );
                """
            )

    def log_scan(self, pair: ScannedPair) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO scans (ts, mint, symbol, source, payload) VALUES (?,?,?,?,?)",
                (
                    datetime.utcnow().isoformat(),
                    pair.mint,
                    pair.symbol,
                    pair.source,
                    json.dumps({"price": pair.price_usd, "vol_h1": pair.volume_h1}),
                ),
            )

    def log_rejection(self, mint: str, result: FilterResult) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO rejections (ts, mint, reason, details) VALUES (?,?,?,?)",
                (
                    datetime.utcnow().isoformat(),
                    mint,
                    result.reason,
                    json.dumps(result.activity_gate_details),
                ),
            )

    def log_analyst(self, mint: str, result: AnalystResult) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO analyst (ts, mint, score, source, rationale, breakdown) VALUES (?,?,?,?,?,?)",
                (
                    datetime.utcnow().isoformat(),
                    mint,
                    result.score,
                    result.source,
                    result.rationale,
                    json.dumps(result.breakdown),
                ),
            )

    def log_fill(self, fill: PaperFill) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO fills (ts, mint, side, size_usd, price, slippage_bps, fees_usd, score) VALUES (?,?,?,?,?,?,?,?)",
                (
                    fill.timestamp.isoformat(),
                    fill.mint,
                    fill.side,
                    fill.size_usd,
                    fill.price,
                    fill.slippage_bps,
                    fill.fees_usd,
                    fill.score,
                ),
            )

    def log_equity(self, balance: float, open_positions: int) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO equity (ts, balance, open_positions) VALUES (?,?,?)",
                (datetime.utcnow().isoformat(), balance, open_positions),
            )

    def equity_series(self, limit: int = 100) -> list[tuple[str, float]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT ts, balance FROM equity ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
        return [(r["ts"], r["balance"]) for r in reversed(rows)]

    def recap(self) -> dict[str, Any]:
        with self._connect() as conn:
            scans = conn.execute("SELECT COUNT(*) c FROM scans").fetchone()["c"]
            rejects = conn.execute("SELECT COUNT(*) c FROM rejections").fetchone()["c"]
            trades = conn.execute("SELECT COUNT(*) c FROM fills").fetchone()["c"]
            last_eq = conn.execute(
                "SELECT balance FROM equity ORDER BY id DESC LIMIT 1"
            ).fetchone()
            top_rejects = conn.execute(
                "SELECT reason, COUNT(*) c FROM rejections GROUP BY reason ORDER BY c DESC LIMIT 5"
            ).fetchall()
        return {
            "scans": scans,
            "rejections": rejects,
            "fills": trades,
            "last_balance": last_eq["balance"] if last_eq else None,
            "top_rejection_reasons": [(r["reason"], r["c"]) for r in top_rejects],
        }