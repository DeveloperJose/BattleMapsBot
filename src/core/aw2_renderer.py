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
from src.config import config

logger = logging.getLogger(__name__)

TILE_SIZE = config.renderer["tile_size"]
MAX_PROP_EXTENSION = config.renderer["max_prop_extension"]


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
        sprite[:, :] = config.renderer["fallback_color"]
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

            # Resize to fixed width as per config
            target_w = config.renderer.get("image_size", 1000)
            img_w, img_h = img.size

            if img_w != target_w and img_w > 0:
                scale = target_w / img_w
                new_h = int(img_h * scale)
                # Use NEAREST for pixel art style
                img = img.resize((target_w, new_h), resample=Image.Resampling.NEAREST)

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
        """Render map using vectorized numpy operations for the base layer."""

        # 1. Analyze sprites and build a Look-Up Table (LUT)
        unique_ids = np.unique(terrain_ids)
        
        # LUT stores the final 16x16 tile sprite for each unique terrain ID
        lut = np.zeros((len(unique_ids), TILE_SIZE, TILE_SIZE, 4), dtype=np.uint8)
        
        # Caches for complex sprites (non-16x16) and their final PIL images
        complex_sprite_cache = {}
        
        # Ensure plain sprite is RGBA for compositing
        plain_arr = self._plain_sprite
        if plain_arr.shape[2] == 3:
            plain_arr = np.dstack([plain_arr, np.full((TILE_SIZE, TILE_SIZE), 255, dtype=np.uint8)])

        for i, tid in enumerate(unique_ids):
            sprite_arr = self._get_sprite_for_terrain(tid)

            # Ensure sprite is RGBA
            if sprite_arr.shape[2] == 3:
                sprite_arr = np.dstack([sprite_arr, np.full((sprite_arr.shape[0], sprite_arr.shape[1]), 255, dtype=np.uint8)])

            h, w, _ = sprite_arr.shape

            # Case 1: Simple 16x16 tile. Place it in the LUT.
            if h == TILE_SIZE and w == TILE_SIZE:
                # If transparent, composite with plain tile first
                if np.any(sprite_arr[:, :, 3] < 255):
                    alpha = (sprite_arr[:, :, 3] / 255.0)[:, :, np.newaxis]
                    
                    # Blend RGB channels
                    comp_rgb = sprite_arr[:, :, :3] * alpha + plain_arr[:, :, :3] * (1.0 - alpha)
                    
                    # Create final RGBA sprite (now fully opaque)
                    lut[i] = np.dstack([comp_rgb.astype(np.uint8), np.full((h, w), 255, dtype=np.uint8)])
                else:
                    lut[i] = sprite_arr
            # Case 2: Complex (non-16x16) tile. Use plain tile as a base and cache the complex sprite.
            else:
                lut[i] = plain_arr
                
                sprite_img = Image.fromarray(sprite_arr, "RGBA")
                # Pre-composite tall sprites with a plain background for simplicity
                if h > TILE_SIZE:
                    comp = Image.new("RGBA", (w, h))
                    plain_img = Image.fromarray(plain_arr, "RGBA")
                    comp.paste(plain_img, (0, h - TILE_SIZE))
                    comp.alpha_composite(sprite_img)
                    complex_sprite_cache[tid] = comp
                else:
                     complex_sprite_cache[tid] = sprite_img


        # 2. Construct Base Layer using the LUT (Vectorized)
        # Map terrain_ids to LUT indices
        max_id = unique_ids.max() if len(unique_ids) > 0 else 0
        mapper = np.zeros(max_id + 1, dtype=int)
        mapper[unique_ids] = np.arange(len(unique_ids))
        indices = mapper[terrain_ids]

        # Build the grid of tiles from the LUT
        grid = lut[indices]  # Shape: (H, W, 16, 16, 4)

        # Reshape into a single image array
        base_layer_arr = grid.transpose(0, 2, 1, 3, 4).reshape(
            height * TILE_SIZE, width * TILE_SIZE, 4
        )
        
        # Create PIL image from the base layer
        canvas_width = width * TILE_SIZE
        canvas_height = height * TILE_SIZE + MAX_PROP_EXTENSION
        output = Image.new("RGBA", (canvas_width, canvas_height), (0, 0, 0, 0))
        base_layer_img = Image.fromarray(base_layer_arr, "RGBA")
        output.paste(base_layer_img, (0, MAX_PROP_EXTENSION))

        # 3. Render Complex Overlays
        # Iterate only over the coordinates of complex tiles
        if complex_sprite_cache:
            for tid, sprite in complex_sprite_cache.items():
                ys, xs = np.where(terrain_ids == tid)
                for y, x in zip(ys, xs):
                    px = x * TILE_SIZE
                    py = y * TILE_SIZE + MAX_PROP_EXTENSION
                    
                    paste_y = py - (sprite.height - TILE_SIZE)
                    
                    output.paste(sprite, (px, paste_y), mask=sprite)

        # 4. Render Units (same as before, remains iterative)
        for unit in units:
            x, y = unit.get("x", -1), unit.get("y", -1)
            if not (0 <= x < width and 0 <= y < height):
                continue

            ctry_str = str(unit.get("ctry", ""))
            ctry_id = AWBW_COUNTRY_CODE.get(ctry_str, 0)
            unit_id_val = int(unit.get("id", 0))
            internal_unit_id = AWBW_UNIT_CODE.get(unit_id_val, 0)

            unit_sprite_arr = self._get_sprite_for_unit(internal_unit_id, ctry_id)
            if unit_sprite_arr is not None:
                unit_sprite = Image.fromarray(unit_sprite_arr, mode="RGBA")
                px = x * TILE_SIZE
                py = y * TILE_SIZE + MAX_PROP_EXTENSION
                paste_y = py - (unit_sprite.height - TILE_SIZE) if unit_sprite.height > TILE_SIZE else py
                output.paste(unit_sprite, (px, paste_y), mask=unit_sprite)

                hp = int(unit.get("hp", 10))
                if 1 <= hp <= 9:
                    hp_sprite_arr = self.atlas.get(str(hp))
                    if hp_sprite_arr is not None:
                        hp_sprite = Image.fromarray(hp_sprite_arr, mode="RGBA")
                        hp_w, hp_h = hp_sprite.size
                        hp_x = px + TILE_SIZE - hp_w
                        hp_y = py + TILE_SIZE - hp_h
                        output.paste(hp_sprite, (hp_x, hp_y), mask=hp_sprite)
        
        return output