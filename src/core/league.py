import asyncio
from contextlib import closing
import json
import logging
from pathlib import Path
import sqlite3
import time
from typing import Any

import aiohttp

from src.config import LEAGUE_DB_PATH
from src.core.awbw import AWBWClient

logger = logging.getLogger(__name__)
LEAGUE_TTL_SECONDS = 6 * 60 * 60
RETRY_SECONDS = 5 * 60


def normalize_league_data(payload: Any) -> list[dict]:
    """Validate the public snapshot before replacing the last known good data."""
    if not isinstance(payload, dict):
        raise ValueError("Invalid league response")
    maps, cos = payload.get("maps"), payload.get("cos")
    if not isinstance(maps, list) or not isinstance(cos, dict):
        raise ValueError("League response is missing maps or COs")
    setups = []
    for item in maps:
        if item["type"] not in {"std", "fog", "hf"}:
            raise ValueError("Unknown league mode")
        tiers = []
        for tier in item["tiers"]:
            if not tier["enabled"]:
                continue
            names = [cos[str(co["id"])]["name"] for co in tier["cos"]]
            if not all(isinstance(name, str) for name in names):
                raise ValueError("Invalid CO name")
            tiers.append({"name": str(tier["name"]), "cos": names})
        bans = item.get("unitBans", [])
        if not isinstance(bans, list) or not all(isinstance(ban, str) for ban in bans):
            raise ValueError("Invalid unit bans")
        setups.append(
            {
                "id": int(item["id"]),
                "mode": item["type"],
                "tiers": tiers,
                "unit_bans": bans,
                "unit_limit": int(item["unitLimit"]),
                "cap_limit": int(item["capLimit"]),
            }
        )
    return setups


class LeagueRepository:
    """One durable league snapshot shared by all maps, with stale fallback."""

    def __init__(self, client: AWBWClient, db_path: Path | str = LEAGUE_DB_PATH):
        self.client = client
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = asyncio.Lock()
        self._retry_after = 0.0
        with closing(sqlite3.connect(self.db_path)) as conn, conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS league_snapshot (
                    id INTEGER PRIMARY KEY CHECK(id = 1),
                    fetched_at REAL NOT NULL,
                    setups TEXT NOT NULL
                )
            """)

    def _read(self) -> dict | None:
        with closing(sqlite3.connect(self.db_path)) as conn:
            row = conn.execute(
                "SELECT fetched_at, setups FROM league_snapshot WHERE id = 1"
            ).fetchone()
        if row is None:
            return None
        return {"fetched_at": row[0], "setups": json.loads(row[1])}

    def _write(self, snapshot: dict) -> None:
        with closing(sqlite3.connect(self.db_path)) as conn, conn:
            conn.execute(
                "INSERT OR REPLACE INTO league_snapshot VALUES (1, ?, ?)",
                (snapshot["fetched_at"], json.dumps(snapshot["setups"])),
            )

    async def refresh(self) -> dict | None:
        async with self._lock:
            snapshot = await asyncio.to_thread(self._read)
            now = time.time()
            if snapshot and now - snapshot["fetched_at"] < LEAGUE_TTL_SECONDS:
                return snapshot
            if now < self._retry_after:
                return snapshot
            try:
                payload = await self.client.get_league_setups()
                setups = normalize_league_data(payload)
            except (
                aiohttp.ClientError,
                asyncio.TimeoutError,
                ConnectionError,
                ValueError,
                KeyError,
                TypeError,
            ):
                self._retry_after = time.time() + RETRY_SECONDS
                logger.warning(
                    "League refresh failed; retaining cached tiers", exc_info=True
                )
                return snapshot
            snapshot = {"fetched_at": time.time(), "setups": setups}
            await asyncio.to_thread(self._write, snapshot)
            self._retry_after = 0.0
            return snapshot

    async def get_map_setups(self, map_id: int) -> dict | None:
        snapshot = await self.refresh()
        if snapshot is None:
            return None
        setups = [item for item in snapshot["setups"] if item["id"] == map_id]
        if not setups:
            return None
        return {"fetched_at": snapshot["fetched_at"], "setups": setups}
