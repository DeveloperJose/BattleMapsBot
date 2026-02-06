import sqlite3
import json
import os
import asyncio
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from src.core.awbw import AWBWClient

logger = logging.getLogger(__name__)

CACHE_TTL_HOURS = 24
MAX_CACHE_SIZE_MB = 250


class MapRepository:
    def __init__(self, db_path: str = "data/maps.db"):
        self.db_path = db_path
        self._ensure_dirs()
        self._init_db()
        self.client = AWBWClient()

    def _ensure_dirs(self):
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS maps (
                    id INTEGER PRIMARY KEY,
                    json_data TEXT,
                    updated_at TIMESTAMP
                )
            """)
            conn.commit()

    def _get_db_size_mb(self) -> float:
        """Get database size in MB."""
        if os.path.exists(self.db_path):
            return os.path.getsize(self.db_path) / (1024 * 1024)
        return 0.0

    def _enforce_size_limit(self):
        """Clear old cache entries if size exceeds limit."""
        current_size = self._get_db_size_mb()
        if current_size <= MAX_CACHE_SIZE_MB:
            return

        logger.warning(
            f"Cache size {current_size:.1f}MB exceeds limit {MAX_CACHE_SIZE_MB}MB. Cleaning up..."
        )

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT id FROM maps ORDER BY updated_at ASC LIMIT 100"
            )
            old_ids = [row[0] for row in cursor.fetchall()]

            for map_id in old_ids:
                conn.execute("DELETE FROM maps WHERE id = ?", (map_id,))

            conn.commit()

        new_size = self._get_db_size_mb()
        logger.info(f"Cache cleanup complete. New size: {new_size:.1f}MB")

    def _is_expired(self, updated_at: str) -> bool:
        """Check if cache entry is older than TTL."""
        try:
            updated = datetime.fromisoformat(updated_at)
            expiry = updated + timedelta(hours=CACHE_TTL_HOURS)
            return datetime.now() > expiry
        except (ValueError, TypeError):
            return True

    def _get_from_db(self, map_id: int) -> Optional[Dict[str, Any]]:
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    "SELECT json_data, updated_at FROM maps WHERE id = ?", (map_id,)
                )
                row = cursor.fetchone()
                if row:
                    json_data, updated_at = row
                    if self._is_expired(updated_at):
                        logger.info(
                            f"Map {map_id} cache expired (older than {CACHE_TTL_HOURS}h)"
                        )
                        return None
                    return json.loads(json_data)
        except Exception as e:
            logger.error(f"DB Error reading map {map_id}: {e}")
        return None

    def _save_to_db(self, map_id: int, data: Dict[str, Any]):
        try:
            self._enforce_size_limit()

            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "INSERT OR REPLACE INTO maps (id, json_data, updated_at) VALUES (?, ?, ?)",
                    (map_id, json.dumps(data), datetime.now().isoformat()),
                )
                conn.commit()
        except Exception as e:
            logger.error(f"DB Error saving map {map_id}: {e}")

    def _parse_map_data(self, j_map: Dict[str, Any], map_id: int) -> Dict[str, Any]:
        map_data = dict()

        map_data["name"] = j_map.get("Name", "Unknown")
        map_data["id"] = map_id
        map_data["author"] = j_map.get("Author", "Unknown")
        map_data["player_count"] = int(j_map.get("Player Count", 0))

        if "Published Date" in j_map:
            map_data["published"] = j_map["Published Date"]

        map_data["size_w"] = int(j_map.get("Size X", 0))
        map_data["size_h"] = int(j_map.get("Size Y", 0))

        if "Terrain Map" in j_map:
            map_data["terr"] = j_map["Terrain Map"]
        else:
            map_data["terr"] = []

        units = list()
        for unit in j_map.get("Predeployed Units", []):
            unit_dict = {
                "id": int(unit.get("Unit ID", 0)),
                "x": int(unit.get("Unit X", 0)),
                "y": int(unit.get("Unit Y", 0)),
                "ctry": unit.get("Country Code", ""),
            }
            units.append(unit_dict)

        map_data["unit"] = units

        return map_data

    async def get_map_data(self, map_id: int, refresh: bool = False) -> Dict[str, Any]:
        loop = asyncio.get_running_loop()

        if not refresh:
            data = await loop.run_in_executor(None, self._get_from_db, map_id)
            if data:
                if "size_w" not in data and "Size X" in data:
                    logger.info(f"Migrating legacy cache for map {map_id}...")
                    data = self._parse_map_data(data, map_id)
                    await loop.run_in_executor(None, self._save_to_db, map_id, data)

                logger.info(f"Loaded map {map_id} from DB cache.")
                return data

        raw_data = await self.client.get_map(map_id)
        data = self._parse_map_data(raw_data, map_id)
        await loop.run_in_executor(None, self._save_to_db, map_id, data)

        return data

    def clear_cache(self, map_id: Optional[int] = None):
        if map_id:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("DELETE FROM maps WHERE id = ?", (map_id,))
                conn.commit()
            logger.info(f"Cleared cache for map {map_id}")
        else:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("DELETE FROM maps")
                conn.commit()
            logger.info("Cleared all map caches")

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        db_size = self._get_db_size_mb()
        entry_count = 0

        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("SELECT COUNT(*) FROM maps")
                entry_count = cursor.fetchone()[0]
        except Exception:
            pass

        return {
            "db_size_mb": round(db_size, 2),
            "entry_count": entry_count,
            "size_limit_mb": MAX_CACHE_SIZE_MB,
            "ttl_hours": CACHE_TTL_HOURS,
        }

    async def close(self):
        await self.client.close()
