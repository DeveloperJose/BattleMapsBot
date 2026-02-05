import numpy as np
import io
from typing import Dict, Any, Tuple
from PIL import Image
from src.core.resources import SpriteCache
from src.utils.data.element_id import AWBW_TERR, AWBW_UNIT_CODE
import logging

logger = logging.getLogger(__name__)


class NumpyRenderer:
    def __init__(self):
        self.sprite_cache = SpriteCache()
        self.atlas = self.sprite_cache.atlas
        self.animated_ids = self.sprite_cache.animated_ids

    def _has_animated_content(
        self, terrain_ids: np.ndarray, unit_grid: np.ndarray
    ) -> bool:
        unique_terr = np.unique(terrain_ids)
        unique_units = np.unique(unit_grid)

        for uid in unique_units:
            if uid in self.animated_ids:
                return True

        for tid in unique_terr:
            if tid in self.animated_ids:
                return True

        return False

    def _render_frame(
        self,
        terrain_ids: np.ndarray,
        unit_grid: np.ndarray,
        frame: int,
        is_static: bool = False,
    ) -> np.ndarray:
        terrain_sprites = self.atlas[terrain_ids, frame]

        unit_sprites = self.atlas[unit_grid, frame]

        if not is_static:
            units_on_frame = 1 < frame < 6
            if not units_on_frame:
                unit_sprites = np.zeros_like(unit_sprites)

        unit_mask = unit_sprites[..., 3] > 0
        unit_mask_4 = np.repeat(unit_mask[..., np.newaxis], 4, axis=-1)

        final_grid = np.where(unit_mask_4, unit_sprites, terrain_sprites)

        height, width = terrain_ids.shape
        final_image_arr = final_grid.transpose(0, 2, 1, 3, 4).reshape(
            height * 4, width * 4, 4
        )

        return final_image_arr

    def render_map(self, map_data: Dict[str, Any]) -> Tuple[bool, io.BytesIO]:
        width = map_data["size_w"]
        height = map_data["size_h"]
        terrain_ids = np.array(map_data["terr"], dtype=np.int32)

        max_awbw_id = max(AWBW_TERR.keys()) + 1
        terr_lookup = np.zeros(max_awbw_id, dtype=np.int32)

        for awbw_id, (terr, ctry) in AWBW_TERR.items():
            terr_lookup[awbw_id] = terr + (ctry * 10)

        base_sprite_ids = np.zeros_like(terrain_ids)
        valid_mask = terrain_ids < max_awbw_id
        base_sprite_ids[valid_mask] = terr_lookup[terrain_ids[valid_mask]]

        unit_grid = np.zeros((height, width), dtype=np.int32)

        from src.utils.data.element_id import AWBW_COUNTRY_CODE

        for u in map_data.get("unit", []):
            u_id = u["id"]
            x, y = u["x"], u["y"]
            ctry_str = u["ctry"]

            internal_unit = AWBW_UNIT_CODE.get(u_id, 0)
            ctry_id = AWBW_COUNTRY_CODE.get(ctry_str, 0)

            sprite_id = internal_unit + (ctry_id * 100)

            if 0 <= y < height and 0 <= x < width:
                unit_grid[y, x] = sprite_id

        is_animated = self._has_animated_content(base_sprite_ids, unit_grid)

        if is_animated:
            frames = []
            for f in range(8):
                frame_arr = self._render_frame(
                    base_sprite_ids, unit_grid, f, is_static=False
                )
                img = Image.fromarray(frame_arr, mode="RGBA")

                total_pixels = width * height
                if total_pixels <= 1600:
                    img = img.resize(
                        (width * 16, height * 16), resample=Image.Resampling.NEAREST
                    )
                elif total_pixels <= 3200:
                    img = img.resize(
                        (width * 8, height * 8), resample=Image.Resampling.NEAREST
                    )

                frames.append(img)

            out = io.BytesIO()
            frames[0].save(
                out,
                format="GIF",
                save_all=True,
                append_images=frames[1:],
                loop=0,
                duration=150,
                optimize=False,
                version="GIF89a",
            )
            out.seek(0)
            return True, out
        else:
            final_image_arr = self._render_frame(
                base_sprite_ids, unit_grid, 0, is_static=True
            )
            img = Image.fromarray(final_image_arr, mode="RGBA")

            total_pixels = width * height
            if total_pixels <= 1600:
                img = img.resize(
                    (width * 16, height * 16), resample=Image.Resampling.NEAREST
                )
            elif total_pixels <= 3200:
                img = img.resize(
                    (width * 8, height * 8), resample=Image.Resampling.NEAREST
                )

            out = io.BytesIO()
            img.save(out, format="PNG")
            out.seek(0)
            return False, out
