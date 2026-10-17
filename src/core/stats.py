import sqlite3
import time
from contextlib import closing
from pathlib import Path
from typing import Any, Dict

from src.config import STATS_DB_PATH


class BotStats:
    """Durable totals and rolling API counts, committed after every event."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            instance = super().__new__(cls)
            instance._init_stats()
            cls._instance = instance
        return cls._instance

    def _init_stats(self) -> None:
        self.start_time = time.time()
        self.db_path = Path(STATS_DB_PATH)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with closing(self._connect()) as conn, conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS counters (
                    kind TEXT PRIMARY KEY,
                    count INTEGER NOT NULL DEFAULT 0,
                    total_time REAL NOT NULL DEFAULT 0,
                    longest REAL NOT NULL DEFAULT 0,
                    longest_id INTEGER NOT NULL DEFAULT 0
                );
                CREATE TABLE IF NOT EXISTS api_requests (
                    timestamp REAL NOT NULL
                );
                CREATE INDEX IF NOT EXISTS api_requests_timestamp
                    ON api_requests(timestamp);
            """)
            conn.execute(
                "DELETE FROM api_requests WHERE timestamp < ?", (time.time() - 86400,)
            )

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path, timeout=10)

    def _record(self, kind: str, duration: float, item_id: int = 0) -> None:
        with closing(self._connect()) as conn, conn:
            conn.execute(
                """
                INSERT INTO counters (kind, count, total_time, longest, longest_id)
                VALUES (?, 1, ?, ?, ?)
                ON CONFLICT(kind) DO UPDATE SET
                    count = count + 1,
                    total_time = total_time + excluded.total_time,
                    longest_id = CASE WHEN excluded.longest > longest
                        THEN excluded.longest_id ELSE longest_id END,
                    longest = MAX(longest, excluded.longest)
                """,
                (kind, duration, duration, item_id),
            )
            if kind == "api":
                now = time.time()
                conn.execute("INSERT INTO api_requests VALUES (?)", (now,))
                conn.execute(
                    "DELETE FROM api_requests WHERE timestamp < ?", (now - 86400,)
                )

    def record_api_request(self, duration: float) -> None:
        self._record("api", duration)

    def record_render(self, duration: float, map_id: int) -> None:
        self._record("render", duration, map_id)

    def record_game_render(self, duration: float, game_id: int) -> None:
        self._record("game_render", duration, game_id)

    def record_game_generation(self, duration: float, game_id: int) -> None:
        self._record("game_generation", duration, game_id)

    def _get_stats(self, kind: str) -> Dict[str, Any]:
        with closing(self._connect()) as conn:
            row = conn.execute(
                "SELECT count, total_time, longest, longest_id FROM counters WHERE kind = ?",
                (kind,),
            ).fetchone()
        count, total_time, longest, longest_id = row or (0, 0.0, 0.0, 0)
        return {
            "count": count,
            "total_time": total_time,
            "longest": longest,
            "average": total_time / count if count else 0,
            "longest_id": longest_id,
        }

    def get_api_stats(self) -> Dict[str, Any]:
        stats = self._get_stats("api")
        now = time.time()
        with closing(self._connect()) as conn:
            windows = conn.execute(
                """
                SELECT COUNT(*), COALESCE(SUM(timestamp > ?), 0),
                    COALESCE(SUM(timestamp > ?), 0)
                FROM api_requests WHERE timestamp >= ?
                """,
                (now - 3600, now - 60, now - 86400),
            ).fetchone()
        return {
            "longest": stats["longest"],
            "average": stats["average"],
            # Retain the old key for compatibility with existing callers.
            "total_uptime": stats["count"],
            "total_all_time": stats["count"],
            "total_24h": windows[0],
            "total_1h": windows[1],
            "total_1m": windows[2],
        }

    def get_render_stats(self) -> Dict[str, Any]:
        stats = self._get_stats("render")
        stats["longest_map_id"] = stats.pop("longest_id")
        return stats

    def get_game_render_stats(self) -> Dict[str, Any]:
        stats = self._get_stats("game_render")
        stats["longest_game_id"] = stats.pop("longest_id")
        return stats

    def get_game_generation_stats(self) -> Dict[str, Any]:
        stats = self._get_stats("game_generation")
        stats["longest_game_id"] = stats.pop("longest_id")
        return stats
