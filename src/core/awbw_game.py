import html
import json
import re
from typing import Any


class AWBWGameParseError(ValueError):
    pass


def parse_game_page(
    page_html: str, game_id: int, base_map_data: dict[str, Any]
) -> dict[str, Any]:
    """Parse public AWBW game HTML into renderer-compatible map data."""
    map_id = _extract_int(page_html, r"const\s+mapId\s*=\s*(\d+)\s*;")
    width = _extract_int(page_html, r"const\s+maxX\s*=\s*(\d+)\s*;")
    height = _extract_int(page_html, r"const\s+maxY\s*=\s*(\d+)\s*;")
    game_day = _extract_int(page_html, r"let\s+gameDay\s*=\s*(\d+)\s*;")
    current_turn = _extract_int(page_html, r"let\s+currentTurn\s*=\s*(\d+)\s*;")

    buildings_info = _extract_json_assignment(page_html, "buildingsInfo")
    units_info = _extract_json_assignment(page_html, "unitsInfo")
    generic_units = _extract_json_assignment(page_html, "genericUnits")
    viewer_colors = _extract_json_assignment(page_html, "viewerColors")

    map_data = dict(base_map_data)
    map_data["source"] = "game"
    map_data["id"] = map_id
    map_data["game_id"] = game_id
    map_data["game_day"] = game_day
    map_data["current_turn"] = current_turn
    map_data["current_turn_country"] = viewer_colors.get(str(current_turn), "")
    map_data["size_w"] = width
    map_data["size_h"] = height
    map_data["name"] = _extract_game_title(page_html) or map_data.get(
        "name", f"Game {game_id}"
    )

    terrain = _copy_terrain(map_data.get("terr", []))
    _overlay_buildings(terrain, width, height, buildings_info)
    map_data["terr"] = terrain
    map_data["unit"] = _parse_units(units_info, buildings_info, generic_units)

    return map_data


def _extract_int(text: str, pattern: str) -> int:
    match = re.search(pattern, text)
    if not match:
        raise AWBWGameParseError(f"Could not find pattern: {pattern}")
    return int(match.group(1))


def _extract_json_assignment(text: str, name: str) -> Any:
    match = re.search(rf"(?:let|const|var)\s+{re.escape(name)}\s*=", text)
    if not match:
        raise AWBWGameParseError(f"Could not find JS assignment for {name}")

    start = text.find("{", match.end())
    if start == -1:
        raise AWBWGameParseError(f"Could not find JSON object for {name}")

    try:
        value, _ = json.JSONDecoder().raw_decode(text[start:])
    except json.JSONDecodeError as exc:
        raise AWBWGameParseError(f"Could not decode {name}: {exc}") from exc

    return value


def _extract_game_title(text: str) -> str | None:
    match = re.search(r"<title>\s*Game\s+-\s*(.*?)\s*-\s*AWBW", text, re.S)
    if not match:
        return None
    title = re.sub(r"\s+", " ", html.unescape(match.group(1))).strip()
    return title or None


def _copy_terrain(terrain: Any) -> Any:
    if isinstance(terrain, list):
        return [row.copy() if isinstance(row, list) else row for row in terrain]
    return terrain


def _overlay_buildings(
    terrain: Any, width: int, height: int, buildings_info: dict[str, Any]
) -> None:
    for by_x in buildings_info.values():
        if not isinstance(by_x, dict):
            continue
        for building in by_x.values():
            if not isinstance(building, dict):
                continue
            x = int(building.get("buildings_x", -1))
            y = int(building.get("buildings_y", -1))
            terrain_id = int(building.get("terrain_id", 0))
            if not (0 <= x < width and 0 <= y < height and terrain_id > 0):
                continue
            _set_terrain_at(terrain, x, y, width, height, terrain_id)


def _set_terrain_at(
    terrain: Any, x: int, y: int, width: int, height: int, terrain_id: int
) -> None:
    if terrain and isinstance(terrain[0], list):
        if len(terrain) == width and len(terrain[x]) == height:
            terrain[x][y] = terrain_id
        elif len(terrain) == height and len(terrain[y]) == width:
            terrain[y][x] = terrain_id
        return

    index = x * height + y
    if 0 <= index < len(terrain):
        terrain[index] = terrain_id


def _parse_units(
    units_info: dict[str, Any],
    buildings_info: dict[str, Any],
    generic_units: dict[str, Any],
) -> list[dict[str, Any]]:
    units = []
    for unit in units_info.values():
        if not isinstance(unit, dict):
            continue
        if unit.get("units_carried") == "Y":
            continue
        unit_id = _to_int(unit.get("generic_id"), 0)
        x = _to_int(unit.get("units_x"), -1)
        y = _to_int(unit.get("units_y"), -1)
        if unit_id <= 0 or x < 0 or y < 0:
            continue
        unit_name = str(unit.get("units_name", ""))
        cargo1 = unit.get("units_cargo1_units_id", 0)
        cargo2 = unit.get("units_cargo2_units_id", 0)
        units.append(
            {
                "id": unit_id,
                "x": x,
                "y": y,
                "ctry": unit.get("countries_code", ""),
                "hp": _parse_hp(unit.get("units_hit_points", 10)),
                "capturing": _is_capturing(unit_name, x, y, buildings_info),
                "loaded": _has_cargo(cargo1) or _has_cargo(cargo2),
                "hidden_cargo": cargo1 == "?",
                "low_ammo": _has_low_ammo(unit, generic_units),
            }
        )
    return units


def _is_capturing(
    unit_name: str, x: int, y: int, buildings_info: dict[str, Any]
) -> bool:
    if unit_name.lower() not in {"infantry", "mech"}:
        return False
    building = buildings_info.get(str(x), {}).get(str(y))
    if not isinstance(building, dict):
        return False
    return _to_int(building.get("buildings_capture"), 20) < 20


def _has_cargo(cargo_id: Any) -> bool:
    return cargo_id == "?" or _to_int(cargo_id, 0) > 0


def _has_low_ammo(unit: dict[str, Any], generic_units: dict[str, Any]) -> bool:
    unit_name = str(unit.get("units_name", ""))
    generic_unit = generic_units.get(unit_name)
    if not isinstance(generic_unit, dict):
        return False

    full_ammo = _to_int(generic_unit.get("units_ammo"), 0)
    current_ammo = _to_int(unit.get("units_ammo"), 0)
    if full_ammo <= 0:
        return False
    return current_ammo < ((full_ammo + 1) // 2)


def _parse_hp(value: Any) -> int | str:
    if value == "?":
        return "?"
    return _to_int(value, 10)


def _to_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except TypeError, ValueError:
        return default
