import aiohttp
import logging
import time
from typing import Optional, Dict, Any
from aiolimiter import AsyncLimiter
from src.core.stats import BotStats
from src.core.awbw_categories import parse_map_categories
from src.config import config

logger = logging.getLogger(__name__)


class AWBWClient:
    """
    Client for interacting with the AWBW API.
    Handles rate limiting and session management.
    """

    MAPS_API = config.api["map_url"]

    def __init__(self):
        self._session: Optional[aiohttp.ClientSession] = None
        rate_limit = config.api["rate_limit"]
        self._limiter = AsyncLimiter(rate_limit["calls"], rate_limit["period"])

    async def get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=15, connect=5, sock_read=10)
            self._session = aiohttp.ClientSession(timeout=timeout)
        return self._session

    async def close(self):
        if self._session:
            await self._session.close()

    async def get_map(self, map_id: int) -> Dict[str, Any]:
        """
        Fetches map data from AWBW with rate limiting.
        """
        session = await self.get_session()

        async with self._limiter:
            start_time = time.time()
            try:
                logger.info(f"Fetching map {map_id} from AWBW...")
                async with session.get(
                    self.MAPS_API, params={"maps_id": map_id}
                ) as response:
                    if response.status != 200:
                        raise ConnectionError(
                            f"AWBW API returned status {response.status}"
                        )

                    try:
                        data = await response.json()
                    except aiohttp.ContentTypeError:
                        text = await response.text()
                        raise ConnectionError(
                            f"AWBW API returned invalid JSON: {text[:100]}..."
                        )

                    if data.get("err"):
                        raise ValueError(data.get("message", "Unknown API Error"))

                    # Basic validation that it looks like a map
                    if "Terrain Map" not in data:
                        raise ValueError("Response does not contain Terrain Map data")

                    return data
            except aiohttp.ClientError as e:
                logger.error(f"Network error fetching map {map_id}: {e}")
                raise
            finally:
                BotStats().record_api_request(time.time() - start_time)

    async def get_game_page(self, game_id: int, ndx: int | None = None) -> str:
        """Fetches the public AWBW game page HTML with rate limiting."""
        session = await self.get_session()

        async with self._limiter:
            start_time = time.time()
            try:
                params = {"games_id": game_id}
                if ndx is not None:
                    params["ndx"] = ndx
                logger.info("Fetching game %s page from AWBW...", game_id)
                async with session.get(
                    "https://awbw.amarriner.com/game.php",
                    params=params,
                    headers={"User-Agent": "BattleMapsBot/1.0"},
                ) as response:
                    if response.status != 200:
                        raise ConnectionError(
                            f"AWBW game page returned status {response.status}"
                        )
                    return await response.text()
            except aiohttp.ClientError as e:
                logger.error(f"Network error fetching game {game_id}: {e}")
                raise
            finally:
                BotStats().record_api_request(time.time() - start_time)

    async def get_replay_turn(
        self, game_id: int, turn: int, turn_player_id: int, current_day: int
    ) -> dict[str, Any]:
        """Fetch the board state for an AWBW replay turn."""
        session = await self.get_session()
        async with self._limiter:
            started = time.time()
            try:
                async with session.post(
                    "https://awbw.amarriner.com/api/game/load_replay.php",
                    json={
                        "gameId": game_id,
                        "turn": turn,
                        "turnPId": turn_player_id,
                        "turnDay": current_day,
                        "initial": True,
                    },
                    headers={
                        "Referer": f"https://awbw.amarriner.com/game.php?games_id={game_id}&ndx={turn}",
                        "X-Requested-With": "XMLHttpRequest",
                    },
                ) as response:
                    if response.status != 200:
                        raise ConnectionError(
                            f"AWBW replay returned status {response.status}"
                        )
                    return await response.json(content_type=None)
            finally:
                BotStats().record_api_request(time.time() - started)

    async def get_map_analysis_page(self, map_id: int) -> str:
        """Fetch the public map-analysis page from AWBW."""
        session = await self.get_session()
        async with self._limiter:
            started = time.time()
            try:
                async with session.get(
                    "https://awbw.amarriner.com/analysis.php",
                    params={"maps_id": map_id},
                    headers={"User-Agent": "BattleMapsBot/1.0"},
                ) as response:
                    if response.status != 200:
                        raise ConnectionError(
                            f"AWBW map analysis returned status {response.status}"
                        )
                    return await response.text()
            finally:
                BotStats().record_api_request(time.time() - started)

    async def get_profile_page(self, username: str) -> str:
        """Fetch a public AWBW profile page through the shared rate limiter."""
        session = await self.get_session()
        async with self._limiter:
            started = time.time()
            try:
                async with session.get(
                    "https://awbw.amarriner.com/profile.php",
                    params={"username": username},
                    headers={"User-Agent": "BattleMapsBot/1.0"},
                ) as response:
                    if response.status != 200:
                        raise ConnectionError(
                            f"AWBW profile returned status {response.status}"
                        )
                    return await response.text()
            finally:
                BotStats().record_api_request(time.time() - started)

    async def get_global_league_standings_page(self, time_period: str) -> str:
        """Fetch the public Global League table through the shared limiter."""
        session = await self.get_session()
        async with self._limiter:
            started = time.time()
            try:
                async with session.get(
                    "https://awbw.amarriner.com/newleague_standings.php",
                    params={"type": "tot", "time": time_period},
                    headers={"User-Agent": "BattleMapsBot/1.0"},
                ) as response:
                    if response.status != 200:
                        raise ConnectionError(
                            f"AWBW Global League standings returned status {response.status}"
                        )
                    # The all-time table occasionally includes legacy bytes that
                    # are invalid UTF-8 despite the page's declared charset.
                    return await response.text(encoding="latin-1")
            finally:
                BotStats().record_api_request(time.time() - started)

    async def get_live_league_standings(self) -> dict[str, Any]:
        """Fetch the public Live League leaderboard through the shared limiter."""
        session = await self.get_session()
        async with self._limiter:
            started = time.time()
            try:
                async with session.post(
                    "https://awbw.amarriner.com/api/live/standings.php?method=leaderboard",
                    json={"method": "leaderboard", "filter": "all"},
                    headers={"User-Agent": "BattleMapsBot/1.0"},
                ) as response:
                    if response.status != 200:
                        raise ConnectionError(
                            f"AWBW Live League standings returned status {response.status}"
                        )
                    return await response.json(content_type=None)
            finally:
                BotStats().record_api_request(time.time() - started)

    async def get_map_categories(self, map_id: int) -> list[str]:
        session = await self.get_session()
        async with self._limiter:
            start_time = time.time()
            try:
                async with session.get(
                    "https://awbw.amarriner.com/prevmaps.php",
                    params={"maps_id": map_id},
                    headers={"User-Agent": "BattleMapsBot/1.0"},
                ) as response:
                    if response.status != 200:
                        raise ConnectionError(
                            f"AWBW map page returned status {response.status}"
                        )
                    return parse_map_categories(await response.text())
            finally:
                BotStats().record_api_request(time.time() - start_time)

    async def get_league_setups(self) -> dict:
        """Read the same public league snapshot used by newleaguesetups.php."""
        session = await self.get_session()
        async with self._limiter:
            started = time.time()
            try:
                async with session.post(
                    "https://awbw.amarriner.com/api/league/maps.php",
                    json={"method": "listMaps"},
                    headers={"User-Agent": "BattleMapsBot/1.0"},
                ) as response:
                    if response.status != 200:
                        raise ConnectionError(
                            f"AWBW league API returned status {response.status}"
                        )
                    return await response.json()
            finally:
                BotStats().record_api_request(time.time() - started)
