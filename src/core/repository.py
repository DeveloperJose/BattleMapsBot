import sqlite3
import json
import os
import asyncio
import logging
from typing import Optional, Dict, Any
from datetime import datetime
from src.core.awbw import AWBWClient

logger = logging.getLogger(__name__)


class MapRepository:
    def __init__(self, db_path: str = "data/maps.db"):
        self.db_path = db_path
        self.cache_dir = "data/cache"
        self._ensure_dirs()
        self._init_db()
        self.client = AWBWClient()

    def _ensure_dirs(self):
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        os.makedirs(self.cache_dir, exist_ok=True)

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

    def _get_from_db(self, map_id: int) -> Optional[Dict[str, Any]]:
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    "SELECT json_data FROM maps WHERE id = ?", (map_id,)
                )
                row = cursor.fetchone()
                if row:
                    return json.loads(row[0])
        except Exception as e:
            logger.error(f"DB Error reading map {map_id}: {e}")
        return None

    def _save_to_db(self, map_id: int, data: Dict[str, Any]):
        try:
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

    def get_cache_path(self, map_id: int) -> str:
        return os.path.join(self.cache_dir, f"{map_id}.png")

    def clear_cache(self, map_id: Optional[int] = None):
        if map_id:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("DELETE FROM maps WHERE id = ?", (map_id,))
                conn.commit()

            path = self.get_cache_path(map_id)
            if os.path.exists(path):
                os.remove(path)
            logger.info(f"Cleared cache for map {map_id}")
        else:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("DELETE FROM maps")
                conn.commit()

            if os.path.exists(self.cache_dir):
                for f in os.listdir(self.cache_dir):
                    if f.endswith(".png"):
                        os.remove(os.path.join(self.cache_dir, f))
            logger.info("Cleared all map caches")

    async def close(self):
        await self.client.close()
