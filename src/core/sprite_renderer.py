"""Fast, original BattleMaps four-pixel sprite renderer for ``!sprite``."""

from __future__ import annotations

import io
from typing import Any

import numpy as np
from PIL import Image

from src.core.legacy_dot_data import (
    ANIM_ID_TO_SPEC,
    BITMAP_SPEC,
    PALETTE,
    STATIC_ID_TO_SPEC,
    UNIT_ID_TO_SPEC,
)
from src.utils.data.element_id import AWBW_COUNTRY_CODE, AWBW_TERR, AWBW_UNIT_CODE


UNIT_ID_OFFSET = 10_000


class DotSpriteRenderer:
    """Render using the optimized historical NumPy sprite atlas.

    This is the same 4x4 dot-art data and animation cadence as the original
    BattleMaps previews, adapted only to the current map-data interface.
    """

    def __init__(self) -> None:
        self.atlas, self.animated_ids = self._build_atlas()

    @staticmethod
    def _build_atlas() -> tuple[np.ndarray, set[int]]:
        max_terrain_id = max(
            max(ids)
            for spec in (STATIC_ID_TO_SPEC, ANIM_ID_TO_SPEC)
            for ids in spec.values()
        )
        max_unit_id = max(max(ids) for ids in UNIT_ID_TO_SPEC.values())
        atlas = np.zeros(
            (UNIT_ID_OFFSET + max(max_terrain_id, max_unit_id) + 1, 8, 4, 4, 4),
            dtype=np.uint8,
        )
        animated_ids = {item for ids in ANIM_ID_TO_SPEC.values() for item in ids}
        animated_ids.update(
            UNIT_ID_OFFSET + item for ids in UNIT_ID_TO_SPEC.values() for item in ids
        )

        DotSpriteRenderer._add_sprites(atlas, STATIC_ID_TO_SPEC)
        DotSpriteRenderer._add_sprites(atlas, ANIM_ID_TO_SPEC)
        DotSpriteRenderer._add_sprites(atlas, UNIT_ID_TO_SPEC, UNIT_ID_OFFSET)
        return atlas, animated_ids

    @staticmethod
    def _add_sprites(
        atlas: np.ndarray, id_to_name: dict[str, list[int]], offset: int = 0
    ) -> None:
        for name, ids in id_to_name.items():
            layers = BITMAP_SPEC.get(name)
            if layers is None:
                continue
            sprite = np.zeros((8, 4, 4, 4), dtype=np.uint8)
            for color_name, grid_string in layers:
                grid = np.array(
                    [[int(pixel) for pixel in row] for row in grid_string.split()]
                )
                colors = PALETTE[color_name]
                colors = colors if isinstance(colors, list) else [colors] * 8
                for frame, color in enumerate(colors):
                    if offset and not 1 < frame < 6:
                        continue
                    sprite[frame, grid == 1, :3] = color
                    sprite[frame, grid == 1, 3] = 255
            for item_id in ids:
                atlas[offset + item_id] = sprite

    def render_map(self, map_data: dict[str, Any]) -> tuple[bool, io.BytesIO]:
        width, height = int(map_data["size_w"]), int(map_data["size_h"])
        terrain_ids = np.asarray(map_data["terr"], dtype=np.int32)
        if terrain_ids.ndim == 1:
            terrain_ids = terrain_ids.reshape(width, height).T
        else:
            terrain_ids = terrain_ids.T
        terrain_ids = terrain_ids[:height, :width]
        terrain_ids = self._sprite_terrain_ids(terrain_ids)
        unit_ids = self._sprite_unit_ids(map_data.get("unit", []), width, height)
        animated = bool(
            np.isin(terrain_ids, tuple(self.animated_ids)).any()
            or np.isin(unit_ids, tuple(self.animated_ids)).any()
        )

        frames = [
            self._render_frame(terrain_ids, unit_ids, frame) for frame in range(8)
        ]
        frames = [self._resize(frame, width, height) for frame in frames]
        output = io.BytesIO()
        if animated:
            frames[0].save(
                output,
                format="GIF",
                save_all=True,
                append_images=frames[1:],
                loop=0,
                duration=150,
                optimize=False,
                disposal=2,
            )
        else:
            frames[0].save(output, format="PNG")
        output.seek(0)
        return animated, output

    @staticmethod
    def _sprite_terrain_ids(terrain_ids: np.ndarray) -> np.ndarray:
        lookup = np.zeros(max(AWBW_TERR) + 1, dtype=np.int32)
        for awbw_id, (terrain, country) in AWBW_TERR.items():
            lookup[awbw_id] = terrain + country * 10
        result = np.zeros_like(terrain_ids)
        valid = (terrain_ids >= 0) & (terrain_ids < len(lookup))
        result[valid] = lookup[terrain_ids[valid]]
        return result

    @staticmethod
    def _sprite_unit_ids(
        units: list[dict[str, Any]], width: int, height: int
    ) -> np.ndarray:
        result = np.zeros((height, width), dtype=np.int32)
        for unit in units:
            try:
                x, y = int(unit["x"]), int(unit["y"])
            except KeyError, TypeError, ValueError:
                continue
            if 0 <= x < width and 0 <= y < height:
                unit_id = AWBW_UNIT_CODE.get(int(unit.get("id", 0)), 0)
                country_id = AWBW_COUNTRY_CODE.get(str(unit.get("ctry", "")), 0)
                result[y, x] = UNIT_ID_OFFSET + unit_id + country_id * 100
        return result

    def _render_frame(
        self, terrain_ids: np.ndarray, unit_ids: np.ndarray, frame: int
    ) -> Image.Image:
        terrain = self.atlas[terrain_ids, frame]
        units = self.atlas[unit_ids, frame]
        unit_mask = units[..., 3] > 0
        grid = np.where(unit_mask[..., np.newaxis], units, terrain)
        height, width = terrain_ids.shape
        pixels = grid.transpose(0, 2, 1, 3, 4).reshape(height * 4, width * 4, 4)
        return Image.fromarray(pixels, "RGBA")

    @staticmethod
    def _resize(image: Image.Image, width: int, height: int) -> Image.Image:
        scale = 4 if width * height <= 1600 else 2 if width * height <= 3200 else 1
        if scale == 1:
            return image
        return image.resize(
            (image.width * scale, image.height * scale), Image.Resampling.NEAREST
        )
