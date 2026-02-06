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
)
from src.core.stats import BotStats
from src.utils.data.element_id import AWBW_COUNTRY_CODE, AWBW_UNIT_CODE

logger = logging.getLogger(__name__)

TILE_SIZE = 16


class AW2Renderer:
    """Renderer using actual AW2 game sprites."""

    # Terrain IDs that are properties (need plains underneath)
    # Includes: city, base, airport, port, hq, comtower, lab for all factions
    PROPERTY_IDS = {
        # Neutral properties (34-37)
        34,
        35,
        36,
        37,
        # OS properties (38-42)
        38,
        39,
        40,
        41,
        42,
        # BM properties (43-47)
        43,
        44,
        45,
        46,
        47,
        # GE properties (48-52)
        48,
        49,
        50,
        51,
        52,
        # YC properties (53-57)
        53,
        54,
        55,
        56,
        57,
        # Red Fire properties (81-85)
        81,
        82,
        83,
        84,
        85,
        # Grey Sky properties (86-90)
        86,
        87,
        88,
        89,
        90,
        # Black Hole properties (91-95)
        91,
        92,
        93,
        94,
        95,
        # Brown Desert properties (96-100)
        96,
        97,
        98,
        99,
        100,
        # Com Towers (127-137)
        127,
        128,
        129,
        130,
        131,
        132,
        133,
        134,
        135,
        136,
        137,
        # Labs (138-148)
        138,
        139,
        140,
        141,
        142,
        143,
        144,
        145,
        146,
        147,
        148,
        # Cobalt Ice properties (149-155)
        149,
        150,
        151,
        152,
        153,
        154,
        155,
        # Pink Cosmos properties (156-162)
        156,
        157,
        158,
        159,
        160,
        161,
        162,
        # Teal Galaxy properties (163-169)
        163,
        164,
        165,
        166,
        167,
        168,
        169,
        # Purple Lightning properties (170-176)
        170,
        171,
        172,
        173,
        174,
        175,
        176,
        # Acid Rain properties (181-187)
        181,
        182,
        183,
        184,
        185,
        186,
        187,
        # White Nova properties (188-194)
        188,
        189,
        190,
        191,
        192,
        193,
        194,
        # Azure Asteroid properties (196-202)
        196,
        197,
        198,
        199,
        200,
        201,
        202,
        # Noir Eclipse properties (203-209)
        203,
        204,
        205,
        206,
        207,
        208,
        209,
        # Silver Claw properties (210-216)
        210,
        211,
        212,
        213,
        214,
        215,
        216,
        # Umber Wilds properties (217-223)
        217,
        218,
        219,
        220,
        221,
        222,
        223,
    }

    def __init__(self):
        self.atlas = SpriteAtlas()
        self._fallback_sprite = self._create_fallback_sprite()
        plain = self.atlas.get("plain")
        self._plain_sprite = plain if plain is not None else self._fallback_sprite

    def _create_fallback_sprite(self) -> np.ndarray:
        """Create a magenta fallback sprite for missing terrain."""
        sprite = np.zeros((TILE_SIZE, TILE_SIZE, 4), dtype=np.uint8)
        sprite[:, :] = [255, 0, 255, 255]  # Magenta
        return sprite

    def _get_sprite_for_terrain(self, terrain_id: int) -> np.ndarray:
        """Get sprite array for a terrain ID."""
        sprite_name = TERRAIN_ID_TO_SPRITE.get(terrain_id)

        if sprite_name is None:
            logger.warning(f"Unknown terrain ID: {terrain_id}")
            return self._fallback_sprite

        sprite = self.atlas.get(sprite_name)
        if sprite is None:
            logger.warning(f"Sprite not found: {sprite_name} for terrain ID {terrain_id}")
            return self._fallback_sprite

        return sprite

    def _get_sprite_for_unit(self, unit_id: int, country_id: int) -> np.ndarray | None:
        """Get sprite array for a unit."""
        if country_id not in COUNTRY_ID_TO_PREFIX:
            return None

        prefix = COUNTRY_ID_TO_PREFIX[country_id]
        suffix = UNIT_ID_TO_SPRITE_NAME.get(unit_id)

        if not suffix:
            logger.warning(f"No sprite suffix found for unit ID {unit_id} (Country: {country_id})")
            return None

        sprite_name = f"{prefix}{suffix}"
        sprite = self.atlas.get(sprite_name)

        if sprite is None:
            logger.warning(f"Sprite not found in atlas: {sprite_name} (Unit ID: {unit_id})")
            return None

        return sprite

    def _is_property(self, terrain_id: int) -> bool:
        """Check if terrain ID is a property that needs plains underneath."""
        return terrain_id in self.PROPERTY_IDS

    def render_map(self, map_data: Dict[str, Any]) -> Tuple[bool, io.BytesIO]:
        """Render map using AW2 sprites.

        Args:
            map_data: Map data from API containing size_w, size_h, terr, unit

        Returns:
            Tuple of (is_animated, image_bytes)
            Always returns is_animated=False for now.
        """
        start_time = time.time()
        try:
            width = map_data["size_w"]
            height = map_data["size_h"]

            # API returns terrain as flat array in column-major order (W, H)
            # Reshape to (W, H) then transpose to (H, W) for rendering
            terrain_data = np.array(map_data["terr"], dtype=np.int32)

            if terrain_data.ndim == 1:
                # Flat array - reshape to (W, H) then transpose to (H, W)
                terrain_ids = terrain_data.reshape(width, height).T
            else:
                # Already 2D - just transpose to (H, W)
                terrain_ids = terrain_data.T

            # Validate dimensions
            if terrain_ids.shape != (height, width):
                logger.warning(
                    f"Terrain shape {terrain_ids.shape} doesn't match map size {height}x{width}"
                )
                terrain_ids = terrain_ids[:height, :width]

            # Render map image (terrain + units)
            img = self._render(terrain_ids, map_data.get("unit", []), width, height)

            # Scale down very large maps to fit Discord's limits
            total_pixels = width * height
            img_w, img_h = img.size

            if total_pixels > 3200:
                # Large maps: scale to 50%
                new_w = img_w // 2
                new_h = img_h // 2
                img = img.resize((new_w, new_h), resample=Image.Resampling.NEAREST)
            elif total_pixels > 1600:
                # Medium maps: scale to 75%
                new_w = (img_w * 3) // 4
                new_h = (img_h * 3) // 4
                img = img.resize((new_w, new_h), resample=Image.Resampling.NEAREST)

            # Save to buffer
            out = io.BytesIO()
            img.save(out, format="PNG")
            out.seek(0)

            return False, out
        finally:
            BotStats().record_render(time.time() - start_time)

    def _render(
        self,
        terrain_ids: np.ndarray,
        units: list[dict],
        width: int,
        height: int,
    ) -> Image.Image:
        """Render map to PIL Image with universal alpha compositing.

        Any sprite with transparency (forests, mountains, properties, etc.)
        gets a plains tile underneath first, then the sprite is alpha-composited on top.
        """
        # Properties can extend upward (max ~32px for HQ sprites)
        MAX_PROP_EXTENSION = 16

        # Create output canvas as PIL Image for proper alpha compositing
        canvas_width = width * TILE_SIZE
        canvas_height = height * TILE_SIZE + MAX_PROP_EXTENSION
        output = Image.new("RGBA", (canvas_width, canvas_height), (0, 0, 0, 0))

        # Build sprite lookup for this map
        unique_ids = np.unique(terrain_ids)
        sprite_cache = {}
        has_transparency_cache = {}

        plain_img = Image.fromarray(self._plain_sprite, mode="RGBA")

        for tid in unique_ids:
            sprite_array = self._get_sprite_for_terrain(tid)
            # Convert numpy array to PIL Image
            sprite_img = Image.fromarray(sprite_array, mode="RGBA")
            sprite_cache[tid] = sprite_img

            # Check if sprite has any transparency (alpha < 255)
            alpha = sprite_array[:, :, 3]
            has_transparency_cache[tid] = np.any(alpha < 255)

        # 1. Render all terrain tiles
        for y in range(height):
            for x in range(width):
                terrain_id = int(terrain_ids[y, x])
                sprite = sprite_cache.get(terrain_id, plain_img)
                has_transparency = has_transparency_cache.get(terrain_id, False)

                # Calculate position
                px = x * TILE_SIZE
                py = y * TILE_SIZE + MAX_PROP_EXTENSION

                # Get sprite height
                sprite_h = sprite.height

                # For tall sprites (mountains, forests, properties), align bottom with tile base
                if sprite_h > TILE_SIZE:
                    offset = sprite_h - TILE_SIZE
                    paste_y = py - offset
                else:
                    paste_y = py

                # If sprite has transparency, draw plains underneath first
                if has_transparency:
                    output.paste(plain_img, (px, py))

                # Alpha-composite the sprite on top
                r, g, b, alpha = sprite.split()
                output.paste(sprite, (px, paste_y), mask=alpha)

        # 2. Render all units on top
        for unit in units:
            x, y = unit.get("x", -1), unit.get("y", -1)

            # Skip invalid coordinates
            if not (0 <= x < width and 0 <= y < height):
                continue

            unit_id = unit.get("id")
            ctry_str = unit.get("ctry")
            ctry_id = AWBW_COUNTRY_CODE.get(ctry_str, 0)
            
            # Map AWBW Unit ID to Internal Unit ID
            internal_unit_id = AWBW_UNIT_CODE.get(unit_id, 0)

            unit_sprite_arr = self._get_sprite_for_unit(internal_unit_id, ctry_id)
            if unit_sprite_arr is not None:
                unit_sprite = Image.fromarray(unit_sprite_arr, mode="RGBA")

                # Calculate position (units are centered or aligned to tile)
                # Typically units are 16x16, sometimes larger?
                # The atlas says 16x16 for unit tiles (based on TILE_SIZE=16)
                # If they are larger, we align bottom

                px = x * TILE_SIZE
                py = y * TILE_SIZE + MAX_PROP_EXTENSION

                sprite_h = unit_sprite.height
                if sprite_h > TILE_SIZE:
                    offset = sprite_h - TILE_SIZE
                    paste_y = py - offset
                else:
                    paste_y = py

                r, g, b, alpha = unit_sprite.split()
                output.paste(unit_sprite, (px, paste_y), mask=alpha)

        return output
