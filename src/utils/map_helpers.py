from typing import Dict, Any, List
from src.utils.data.element_id import (
    AWBW_TERR,
    AWBW_COUNTRY_CODE,
    AWBW_UNIT_CODE,
)
from src.utils.awbw_data import PROPERTY_TERRAINS, PROPERTY_VALUE


def format_k(num: float) -> str:
    num = int(num)
    if num >= 1000000:
        return f"{num / 1000000:.2f}M"
    elif num >= 1000:
        return f"{num / 1000:.1f}k"
    else:
        return str(num)


def count_properties(
    terr_map: List[List[int]],
) -> tuple[Dict[int, Dict[int, int]], Dict[int, int]]:
    counts = {i: {} for i in range(21)}
    total_income = {i: 0 for i in range(21)}
    for row in terr_map:
        for terr_id in row:
            terr, ctry = AWBW_TERR.get(terr_id, (0, 0))
            if terr in PROPERTY_TERRAINS and 0 <= ctry <= 20:
                counts[ctry][terr] = counts[ctry].get(terr, 0) + 1
                total_income[ctry] += PROPERTY_VALUE.get(terr, 0)
    return counts, total_income


def count_units(unit_list: List[Dict[str, Any]]) -> Dict[int, Dict[int, int]]:
    counts = {i: {} for i in range(21)}
    for u in unit_list:
        ctry_id = AWBW_COUNTRY_CODE.get(u.get("ctry", ""), 0)
        unit_type_id = AWBW_UNIT_CODE.get(u.get("id", 0), 0)
        if ctry_id in counts:
            counts[ctry_id][unit_type_id] = counts[ctry_id].get(unit_type_id, 0) + 1
    return counts
