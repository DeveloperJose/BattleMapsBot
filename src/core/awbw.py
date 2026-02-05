import aiohttp
import logging
from typing import Optional, Dict, Any
from aiolimiter import AsyncLimiter

logger = logging.getLogger(__name__)


class AWBWClient:
    """
    Client for interacting with the AWBW API.
    Handles rate limiting and session management.
    """

    MAPS_API = "https://awbw.amarriner.com/api/map/map_info.php"

    def __init__(self):
        self._session: Optional[aiohttp.ClientSession] = None
        self._limiter = AsyncLimiter(2, 1.0)

    async def get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
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
