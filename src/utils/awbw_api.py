from aiohttp.client import ClientSession
from datetime import datetime
from typing import Any, Dict, Optional


MAPS_API = "https://awbw.amarriner.com/api/map/map_info.php"
UNSECURED_MAPS_API = "http://awbw.amarriner.com/api/map/map_info.php"


async def get_map(maps_id: Optional[int] = None, verify: bool = False) -> Dict[str, Any]:
    if not maps_id:
        raise ValueError("No valid map ID given.")

    try:
        int(maps_id)
    except (ValueError, TypeError):
        raise ValueError("Argument supplied not a valid map ID")

    payload = {"maps_id": maps_id}

    api = MAPS_API if verify else UNSECURED_MAPS_API

    async with ClientSession() as session:
        async with session.get(api, params=payload, ssl=verify) as response:
            if response.status != 200:
                 raise ConnectionError(f"Unable to establish connection to AWBW. Error: {response.status}")
            
            try:
                j_map = await response.json()
            except Exception:
                raise ConnectionError("Received invalid JSON from AWBW.")


    if j_map.get("err", False):
        raise ValueError(j_map.get("message", "No map matches given ID."))

    map_data = dict()

    map_data["name"] = j_map["Name"]
    map_data["id"] = maps_id
    map_data["author"] = j_map["Author"]
    map_data["player_count"] = int(j_map["Player Count"])
    map_data["published"] = datetime.fromisoformat(j_map["Published Date"])
    map_data["size_w"] = int(j_map["Size X"])
    map_data["size_h"] = int(j_map["Size Y"])
    map_data["terr"] = [list(r) for r in zip(*j_map["Terrain Map"])]

    units = list()
    for unit in j_map["Predeployed Units"]:
        unit_dict = {
            "id":   int(unit["Unit ID"]),
            "x":    int(unit["Unit X"]),
            "y":    int(unit["Unit Y"]),
            "ctry": unit["Country Code"]
        }
        units.append(unit_dict)

    map_data["unit"] = units

    return map_data

# def get_user(user_id: int = None) -> Dict[str, str]:
#     pass


