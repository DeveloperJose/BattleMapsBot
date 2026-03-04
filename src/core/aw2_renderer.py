"""AW2 Sprite-based map renderer.

Uses real AW2 terrain sprites from the game.
Simple approach: terrain only, no units, no shadows, no neighbor variants.
"""

import io
import time
import numpy as np
from PIL import Image
from typing import Dict, Any, Tuple
import logging

from src.core.aw2_atlas import SpriteAtlas
from src.core.aw2_data import (
    TERRAIN_ID_TO_SPRITE,
    COUNTRY_ID_TO_PREFIX,
    UNIT_ID_TO_SPRITE_NAME,
    RIVER_SVC,
    RIVER_EHC,
    RIVER_WHC,
    RIVER_NVC,
    LAND_IDS,
    SEA_ID,
    SHOAL_IDS,
    PROPERTY_IDS,
)
from src.core.aw2_sea_data import (
    SEA_MASK_TO_SPRITE,
    RIVER_CONNECT_N,
    RIVER_CONNECT_W,
    RIVER_CONNECT_S,
    RIVER_CONNECT_E,
    SEA_WATER_IDS,
)
from src.core.stats import BotStats
from src.utils.data.element_id import AWBW_COUNTRY_CODE, AWBW_UNIT_CODE
from src.config import config

logger = logging.getLogger(__name__)

TILE_SIZE = config.renderer["tile_size"]
MAX_PROP_EXTENSION = config.renderer["max_prop_extension"]


class AW2Renderer:
    """Renderer using actual AW2 game sprites."""

    def __init__(self):
        self.atlas = SpriteAtlas()
        self._fallback_sprite = self._create_fallback_sprite()
        plain_arr = self.atlas.get("plain")
        self._plain_sprite = (
            plain_arr if plain_arr is not None else self._fallback_sprite
        )

        # Pre-cache Pillow Image objects to avoid repeated fromarray calls
        self._sprite_image_cache = {}
        for name in self.atlas.sprite_names:
            sprite_arr = self.atlas.get(name)
            if sprite_arr is not None:
                self._sprite_image_cache[name] = Image.fromarray(sprite_arr, "RGBA")

        self._plain_image = self._sprite_image_cache.get("plain")

    def _create_fallback_sprite(self) -> np.ndarray:
        """Create a magenta fallback sprite for missing terrain."""
        sprite = np.zeros((TILE_SIZE, TILE_SIZE, 4), dtype=np.uint8)
        sprite[:, :] = config.renderer["fallback_color"]
        return sprite

    def _get_sprite_for_terrain(self, terrain_id: int) -> Tuple[np.ndarray, str]:
        """Get sprite array and name for a terrain ID."""
        sprite_name = TERRAIN_ID_TO_SPRITE.get(terrain_id, "")

        if not sprite_name:
            logger.warning(f"Unknown terrain ID: {terrain_id}")
            return self._fallback_sprite, ""

        sprite = self.atlas.get(sprite_name)
        if sprite is None:
            logger.warning(
                f"Sprite not found: {sprite_name} for terrain ID {terrain_id}"
            )
            return self._fallback_sprite, ""

        return sprite, sprite_name

    def _get_sprite_name_for_unit(self, unit_id: int, country_id: int) -> str | None:
        """Get sprite name for a unit."""
        if country_id not in COUNTRY_ID_TO_PREFIX:
            return None

        prefix = COUNTRY_ID_TO_PREFIX[country_id]
        suffix = UNIT_ID_TO_SPRITE_NAME.get(unit_id)

        if not suffix:
            logger.warning(
                f"No sprite suffix found for unit ID {unit_id} (Country: {country_id})"
            )
            return None

        return f"{prefix}{suffix}"

    def _get_sea_sprite_name(self, x: int, y: int, terrain_ids: np.ndarray) -> str:
        """Get the numbered sea sprite based on neighbor bitmask.
        
        Matches the logic from map_renderer.js getSea() method.
        Uses newseas sprites: sea0 through sea255.
        """
        height, width = terrain_ids.shape

        def get_terrain_id(px, py):
            if 0 <= py < height and 0 <= px < width:
                return terrain_ids[py, px]
            return 32  # Out of bounds treated as land (plain)

        total = 0
        border = [
            (x - 1, y - 1),  # NW (k=0)
            (x, y - 1),      # N (k=1)
            (x + 1, y - 1),  # NE (k=2)
            (x + 1, y),      # E (k=3)
            (x + 1, y + 1),  # SE (k=4)
            (x, y + 1),      # S (k=5)
            (x - 1, y + 1),  # SW (k=6)
            (x - 1, y),      # W (k=7)
        ]

        for k, (bx, by) in enumerate(border):
            tid = get_terrain_id(bx, by)
            # Water: sea, reef, bridge, shoal, teleport
            if 26 <= tid <= 33 or tid == 195:
                continue
            elif 4 <= tid <= 14:  # rivers
                if k == 1 and tid in RIVER_SVC:
                    total |= 0x05
                elif k == 3 and tid in RIVER_WHC:
                    total |= 0x14
                elif k == 5 and tid in RIVER_NVC:
                    total |= 0x50
                elif k == 7 and tid in RIVER_EHC:
                    total |= 0x41
                else:
                    total |= 1 << k
            else:
                total |= 1 << k

        # Clean up diagonal artifacts - matches JS: total &= ~((total << 1 | total >> 1 | total >> 7) & 0x55)
        total &= ~(((total << 1) | (total >> 1) | (total >> 7)) & 0x55)

        return f"sea{total}"

    def _get_shoal_sprite_name(self, x: int, y: int, terrain_ids: np.ndarray) -> str:
        """Get the sprite name for a shoal tile based on its neighbors."""
        height, width = terrain_ids.shape
        total = 0

        # Define border coordinates [top, left, right, bottom]
        border = [
            (y - 1, x),  # Top
            (y, x - 1),  # Left
            (y, x + 1),  # Right
            (y + 1, x),  # Bottom
        ]

        for k, (by, bx) in enumerate(border):
            tval = 2
            if not (0 <= by < height and 0 <= bx < width):
                tval = 0  # Treat out-of-bounds as sea
            else:
                b_tid = terrain_ids[by, bx]
                if b_tid in {28, 33}:  # sea or reef is a connection
                    tval = 0
                elif 4 <= b_tid <= 14:  # rivers
                    tval = 2  # Default to no connection
                    if k == 0 and b_tid in RIVER_SVC:
                        tval = 1
                    elif k == 1 and b_tid in RIVER_EHC:
                        tval = 1
                    elif k == 2 and b_tid in RIVER_WHC:
                        tval = 1
                    elif k == 3 and b_tid in RIVER_NVC:
                        tval = 1
                elif b_tid == 26:  # hbridge
                    if k == 0 or k == 3:  # Connects vertically
                        tval = 1
                elif b_tid == 27:  # vbridge
                    if k == 1 or k == 2:  # Connects horizontally
                        tval = 1
                elif b_tid in SHOAL_IDS or b_tid == 195:  # shoal or teleporter is land
                    tval = 1

            total += (3**k) * tval

        return f"shoal{total}"

    def _get_sprite_image(self, sprite_name: str) -> Image.Image | None:
        """Get a sprite Image from the cache, converting on-demand if needed."""
        if sprite_name in self._sprite_image_cache:
            return self._sprite_image_cache[sprite_name]

        sprite_arr = self.atlas.get(sprite_name)
        if sprite_arr is not None:
            image = Image.fromarray(sprite_arr, "RGBA")
            self._sprite_image_cache[sprite_name] = image
            return image

        logger.warning(f"Sprite not found in atlas or cache: {sprite_name}")
        return None

    def render_map(self, map_data: Dict[str, Any]) -> Tuple[bool, io.BytesIO]:
        """Render map using AW2 sprites."""
        start_time = time.time()
        try:
            width = map_data["size_w"]
            height = map_data["size_h"]

            terrain_data = np.array(map_data["terr"], dtype=np.int32)

            if terrain_data.ndim == 1:
                terrain_ids = terrain_data.reshape(width, height).T
            else:
                terrain_ids = terrain_data.T

            if terrain_ids.shape != (height, width):
                logger.warning(
                    f"Terrain shape {terrain_ids.shape} doesn't match map size {height}x{width}"
                )
                terrain_ids = terrain_ids[:height, :width]

            img = self._render(terrain_ids, map_data.get("unit", []), width, height)

            target_w = config.renderer.get("image_size", 1000)
            img_w, img_h = img.size

            if img_w != target_w and img_w > 0:
                scale = target_w / img_w
                new_h = int(img_h * scale)
                img = img.resize((target_w, new_h), resample=Image.Resampling.NEAREST)

            out = io.BytesIO()
            img.save(out, format="WEBP", lossless=True)
            out.seek(0)

            return False, out
        finally:
            map_id = map_data.get("id", 0)
            BotStats().record_render(time.time() - start_time, map_id)

    def _render(
        self,
        terrain_ids: np.ndarray,
        units: list[dict],
        width: int,
        height: int,
    ) -> Image.Image:
        """Render map using vectorized numpy operations for the base layer."""

        unique_ids = np.unique(terrain_ids)
        lut = np.zeros((len(unique_ids), TILE_SIZE, TILE_SIZE, 4), dtype=np.uint8)
        complex_sprite_cache = {}
        property_sprite_cache = {}

        plain_arr = self._plain_sprite

        for i, tid in enumerate(unique_ids):
            sprite_arr, sprite_name = self._get_sprite_for_terrain(tid)

            if tid in PROPERTY_IDS:
                lut[i] = plain_arr
                sprite_img = self._get_sprite_image(sprite_name)
                if sprite_img:
                    h, w = sprite_img.height, sprite_img.width
                    if h > TILE_SIZE:
                        comp = Image.new("RGBA", (w, h))
                        if self._plain_image:
                            comp.paste(self._plain_image, (0, h - TILE_SIZE))
                        comp.alpha_composite(sprite_img)
                        property_sprite_cache[tid] = comp
                    else:
                        property_sprite_cache[tid] = sprite_img
                continue

            h, w, c = sprite_arr.shape

            # Ensure sprite is RGBA for LUT
            final_sprite_arr = sprite_arr
            if c == 3:
                alpha_channel = np.full((h, w, 1), 255, dtype=np.uint8)
                final_sprite_arr = np.concatenate([sprite_arr, alpha_channel], axis=2)

            if h == TILE_SIZE and w == TILE_SIZE:
                if np.any(final_sprite_arr[:, :, 3] < 255):
                    alpha = (final_sprite_arr[:, :, 3] / 255.0)[:, :, np.newaxis]
                    comp_rgb = final_sprite_arr[:, :, :3] * alpha + plain_arr[
                        :, :, :3
                    ] * (1.0 - alpha)
                    lut[i] = np.dstack(
                        [
                            comp_rgb.astype(np.uint8),
                            np.full((h, w), 255, dtype=np.uint8),
                        ]
                    )
                else:
                    lut[i] = final_sprite_arr
            else:
                lut[i] = plain_arr
                sprite_img = self._get_sprite_image(sprite_name)
                if sprite_img:
                    if h > TILE_SIZE:
                        comp = Image.new("RGBA", (w, h))
                        if self._plain_image:
                            comp.paste(self._plain_image, (0, h - TILE_SIZE))
                        comp.alpha_composite(sprite_img)
                        complex_sprite_cache[tid] = comp
                    else:
                        complex_sprite_cache[tid] = sprite_img

        max_id = unique_ids.max() if len(unique_ids) > 0 else 0
        mapper = np.zeros(max_id + 1, dtype=int)
        mapper[unique_ids] = np.arange(len(unique_ids))
        indices = mapper[terrain_ids]

        grid = lut[indices]
        base_layer_arr = grid.transpose(0, 2, 1, 3, 4).reshape(
            height * TILE_SIZE, width * TILE_SIZE, 4
        )

        canvas_width = width * TILE_SIZE
        canvas_height = height * TILE_SIZE + MAX_PROP_EXTENSION
        output = Image.new("RGBA", (canvas_width, canvas_height), (0, 0, 0, 0))
        base_layer_img = Image.fromarray(base_layer_arr, "RGBA")
        output.paste(base_layer_img, (0, MAX_PROP_EXTENSION))

        paste = output.paste
        if complex_sprite_cache:
            for tid, sprite in complex_sprite_cache.items():
                ys, xs = np.where(terrain_ids == tid)
                for y, x in zip(ys, xs):
                    px = x * TILE_SIZE
                    py = y * TILE_SIZE + MAX_PROP_EXTENSION
                    paste_y = py - (sprite.height - TILE_SIZE)
                    paste(sprite, (px, paste_y), mask=sprite)

        # Correct seas after base rendering
        sea_ys, sea_xs = np.where(terrain_ids == SEA_ID)
        for y, x in zip(sea_ys, sea_xs):
            sprite_name = self._get_sea_sprite_name(x, y, terrain_ids)
            sprite_img = self._get_sprite_image(sprite_name)
            if sprite_img:
                px = x * TILE_SIZE
                py = y * TILE_SIZE + MAX_PROP_EXTENSION
                paste(sprite_img, (px, py), mask=sprite_img)

        # Correct shoals after base rendering
        shoal_ys, shoal_xs = np.where(np.isin(terrain_ids, list(SHOAL_IDS)))

        for y, x in zip(shoal_ys, shoal_xs):
            sprite_name = self._get_shoal_sprite_name(x, y, terrain_ids)
            sprite_img = self._get_sprite_image(sprite_name)
            if sprite_img:
                px = x * TILE_SIZE
                py = y * TILE_SIZE + MAX_PROP_EXTENSION
                # We need to paste the plain sprite underneath first for transparency
                if self._plain_image:
                    output.paste(self._plain_image, (px, py))
                paste(sprite_img, (px, py), mask=sprite_img)

        # Draw properties on top of terrain and shoals
        if property_sprite_cache:
            for tid, sprite in property_sprite_cache.items():
                ys, xs = np.where(terrain_ids == tid)
                for y, x in zip(ys, xs):
                    px = x * TILE_SIZE
                    py = y * TILE_SIZE + MAX_PROP_EXTENSION

                    # For standard size props, paste plains first for transparency
                    # Tall props have plains pre-composited.
                    if sprite.height == TILE_SIZE and self._plain_image:
                        output.paste(self._plain_image, (px, py))

                    paste_y = py - (sprite.height - TILE_SIZE)
                    paste(sprite, (px, paste_y), mask=sprite)

        for unit in units:
            x, y = unit.get("x", -1), unit.get("y", -1)
            if not (0 <= x < width and 0 <= y < height):
                continue

            ctry_str = str(unit.get("ctry", ""))
            ctry_id = AWBW_COUNTRY_CODE.get(ctry_str, 0)
            unit_id_val = int(unit.get("id", 0))
            internal_unit_id = AWBW_UNIT_CODE.get(unit_id_val, 0)

            sprite_name = self._get_sprite_name_for_unit(internal_unit_id, ctry_id)
            if sprite_name:
                unit_sprite = self._get_sprite_image(sprite_name)
                if unit_sprite:
                    px = x * TILE_SIZE
                    py = y * TILE_SIZE + MAX_PROP_EXTENSION
                    paste_y = (
                        py - (unit_sprite.height - TILE_SIZE)
                        if unit_sprite.height > TILE_SIZE
                        else py
                    )
                    paste(unit_sprite, (px, paste_y), mask=unit_sprite)

                    hp = int(unit.get("hp", 10))
                    if 1 <= hp <= 9:
                        hp_sprite = self._get_sprite_image(str(hp))
                        if hp_sprite:
                            hp_w, hp_h = hp_sprite.size
                            hp_x = px + TILE_SIZE - hp_w
                            hp_y = py + TILE_SIZE - hp_h
                            paste(hp_sprite, (hp_x, hp_y), mask=hp_sprite)
        return output
