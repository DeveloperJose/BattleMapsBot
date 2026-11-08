import aiohttp
import sqlite3
import json
import os
import asyncio
import logging
import time
import re
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from src.core.awbw import AWBWClient
from src.core.awbw_game import apply_replay_turn, parse_game_page
from src.config import config

logger = logging.getLogger(__name__)

CACHE_TTL_SECONDS = config.cache.get("ttl_seconds", 24 * 60 * 60)
MAX_CACHE_SIZE_MB = config.cache.get("max_size_mb", 250)
REPLAY_TURN_FETCH_DELAY_SECONDS = 3


class MapRepository:
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or config.cache["db_path"]
        self._ensure_dirs()
        self._init_db()
        self.client = AWBWClient()
        self._analysis_cache: dict[int, tuple[float, dict[str, str]]] = {}

    def _ensure_dirs(self):
        db_dir = os.path.dirname(self.db_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)

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
            expiry = updated + timedelta(seconds=CACHE_TTL_SECONDS)
            return datetime.now() > expiry
        except ValueError, TypeError:
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
                            f"Map {map_id} cache expired (older than {CACHE_TTL_SECONDS}s)"
                        )
                        return None
                    data = json.loads(json_data)
                    data.setdefault(
                        "fetched_at", datetime.fromisoformat(updated_at).timestamp()
                    )
                    return data
        except Exception as e:
            logger.error(f"DB Error reading map {map_id}: {e}")
        return None

    def _save_to_db(self, map_id: int, data: Dict[str, Any]):
        try:
            self._enforce_size_limit()

            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "INSERT OR REPLACE INTO maps (id, json_data, updated_at) VALUES (?, ?, ?)",
                    (
                        map_id,
                        json.dumps(data),
                        datetime.fromtimestamp(data["fetched_at"]).isoformat(),
                    ),
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
                "hp": int(unit.get("Unit HP", 10)),
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
                    fetched_at = data["fetched_at"]
                    data = self._parse_map_data(data, map_id)
                    data["fetched_at"] = fetched_at
                    await loop.run_in_executor(None, self._save_to_db, map_id, data)

                logger.info(f"Loaded map {map_id} from DB cache.")
                return data

        raw_data = await self.client.get_map(map_id)
        data = self._parse_map_data(raw_data, map_id)
        data["fetched_at"] = time.time()
        try:
            data["categories"] = await self.client.get_map_categories(map_id)
        except aiohttp.ClientError, asyncio.TimeoutError, ConnectionError, ValueError:
            logger.warning(
                "Could not fetch categories for map %s", map_id, exc_info=True
            )
            data["categories"] = None
        await loop.run_in_executor(None, self._save_to_db, map_id, data)

        return data

    async def get_game_data(
        self, game_id: int, ndx: int | None = None
    ) -> Dict[str, Any]:
        game_html = await self.client.get_game_page(game_id)
        map_id = self._parse_game_map_id(game_html)
        base_map_data = await self.get_map_data(map_id)
        game_data = parse_game_page(game_html, game_id, base_map_data)
        game_data["game_ndx"] = ndx
        if ndx is not None:
            await asyncio.sleep(REPLAY_TURN_FETCH_DELAY_SECONDS)
            turn_player_id, current_day = self._parse_game_replay_context(game_html)
            replay = await self.client.get_replay_turn(
                game_id, ndx, turn_player_id, current_day
            )
            apply_replay_turn(game_data, replay)
            game_data["current_game_day"] = current_day
        return game_data

    async def get_map_analysis(self, map_id: int) -> dict[str, str]:
        cached = self._analysis_cache.get(map_id)
        if cached and time.time() - cached[0] < 6 * 60 * 60:
            return cached[1]
        page = await self.client.get_map_analysis_page(map_id)
        analysis = _parse_map_analysis(page)
        self._analysis_cache[map_id] = (time.time(), analysis)
        return analysis

    def _parse_game_map_id(self, game_html: str) -> int:
        import re

        match = re.search(r"const\s+mapId\s*=\s*(\d+)\s*;", game_html)
        if not match:
            raise ValueError("Could not find mapId in AWBW game page")
        return int(match.group(1))

    def _parse_game_replay_context(self, game_html: str) -> tuple[int, int]:
        turn_match = re.search(r"let\s+currentTurn\s*=\s*(\d+)\s*;", game_html)
        day_match = re.search(r"let\s+gameDay\s*=\s*(\d+)\s*;", game_html)
        if not turn_match or not day_match:
            raise ValueError("Could not find replay context in AWBW game page")
        return int(turn_match.group(1)), int(day_match.group(1))

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
            "ttl_seconds": CACHE_TTL_SECONDS,
        }

    async def close(self):
        await self.client.close()


def _parse_map_analysis(page: str) -> dict[str, Any]:
    """Extract game, country, and CO summaries from the AWBW analysis page."""
    labels = {
        "Games": "games",
        "Game Days": "game_days",
        "Avg Game Days": "avg_game_days",
        "Real Time Days": "real_time_days",
        "Avg RT Days": "avg_rt_days",
        "Official Games": "official_games",
        "Team Games": "team_games",
        "No COP Games": "no_cop_games",
        "First Published": "first_published",
        "Last Published": "last_published",
        "Rating": "rating",
        "Comments": "comments",
        "Favorites": "favorites",
    }
    analysis = {}
    for label, key in labels.items():
        match = re.search(
            rf"{re.escape(label)}:(?:\s*<[^>]+>)*\s*(?P<value>[0-9][0-9,./ ]*(?:\([0-9]+%\))?)",
            page,
        )
        if match:
            analysis[key] = match.group("value").strip()

    country_names = {
        "os": "Orange Star",
        "bm": "Blue Moon",
        "ge": "Green Earth",
        "yc": "Yellow Comet",
        "bh": "Black Hole",
        "rf": "Red Fire",
        "gs": "Grey Sky",
        "bd": "Brown Desert",
        "ab": "Amber Blaze",
        "jc": "Jade Sun",
        "ci": "Cobalt Ice",
        "pc": "Pink Cosmos",
        "tg": "Teal Galaxy",
        "pl": "Purple Lightning",
        "ar": "Acid Rain",
        "ww": "White Wave",
        "aa": "Azure Asteroid",
    }
    country_section = re.search(
        r"<b>Country Data</b>.*?(?=<b>CO Data</b>)", page, re.DOTALL
    )
    countries = []
    if country_section:
        for row in re.findall(r"<tr>(.*?)</tr>", country_section.group(0), re.DOTALL):
            logo = re.search(r"terrain/aw1/([a-z]+)logo\.gif", row)
            values = re.findall(r"<b>\s*([0-9,]+|[0-9]+%)\s*</b>", row)
            if logo and len(values) >= 2:
                code = logo.group(1)
                countries.append(
                    {
                        "country": country_names.get(code, code.upper()),
                        "wins": values[0],
                        "win_pct": values[1],
                    }
                )
    if countries:
        analysis["countries"] = countries

    co_section = re.search(r"<b>CO Data</b>(.*)", page, re.DOTALL)
    cos = []
    if co_section:
        for row in re.findall(r"<tr>(.*?)</tr>", co_section.group(1), re.DOTALL):
            name = re.search(r'<td title="([^"]+)"', row)
            cells = re.findall(r"<td[^>]*>(.*?)</td>", row, re.DOTALL)
            values = [re.sub(r"<[^>]+>", "", cell).strip() for cell in cells[1:]]
            if name and len(values) >= 4:
                cos.append(
                    {
                        "name": name.group(1),
                        "chosen": values[0],
                        "chosen_pct": values[1],
                        "record": values[2],
                        "win_pct": values[3],
                    }
                )
    if cos:
        analysis["cos"] = sorted(
            cos, key=lambda row: int(row["chosen"].replace(",", "")), reverse=True
        )
    return analysis
