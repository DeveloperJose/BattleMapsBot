import numpy as np
import logging
from src.core.data import (
    BITMAP_SPEC,
    PALETTE,
    STATIC_ID_TO_SPEC,
    ANIM_ID_TO_SPEC,
    UNIT_ID_TO_SPEC,
)

logger = logging.getLogger(__name__)

# Offset to separate unit sprite IDs from terrain sprite IDs
# Terrain uses IDs 1-999, units will use IDs 10001+
UNIT_ID_OFFSET = 10000


def _parse_grid(grid_str):
    """Parse a 4x4 grid string into a 2D list"""
    lines = grid_str.strip().split()
    grid = []
    for line in lines:
        row = [int(c) for c in line.strip()]
        if len(row) != 4:
            row = [0, 0, 0, 0]
        grid.append(row)
    while len(grid) < 4:
        grid.append([0, 0, 0, 0])
    return grid


class SpriteCache:
    _instance = None
    animated_ids = None
    atlas = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SpriteCache, cls).__new__(cls)
            cls._instance.animated_ids = set()
            cls._instance.atlas = cls._instance._build_atlas()
        return cls._instance

    def _build_atlas(self):
        logger.info("Building Sprite Atlas...")
        max_terr_id = 0
        max_raw_unit_id = 0
        max_country_id = 0

        # Find max terrain ID
        for d in [STATIC_ID_TO_SPEC, ANIM_ID_TO_SPEC]:
            for ids in d.values():
                if ids:
                    max_terr_id = max(max_terr_id, max(ids))

        # Find max raw unit ID and max country ID
        for ids in UNIT_ID_TO_SPEC.values():
            if ids:
                max_raw_unit_id = max(max_raw_unit_id, max(ids))
        # Assuming a maximum of 20 countries based on previous context. Will verify later if needed.
        max_country_id = 20

        # Total atlas size: terrain IDs + (raw unit IDs + country offset) + UNIT_ID_OFFSET
        max_unit_offset_id = max_raw_unit_id + (max_country_id * 100) # Max possible unit ID without UNIT_ID_OFFSET
        max_id = max(max_terr_id, UNIT_ID_OFFSET + max_unit_offset_id)

        # Track animated IDs (for terrain and offset units)
        for ids in ANIM_ID_TO_SPEC.values():
            self.animated_ids.update(ids)
        for ids in UNIT_ID_TO_SPEC.values():
            self.animated_ids.update(i + UNIT_ID_OFFSET for i in ids)

        atlas = np.zeros((max_id + 1, 8, 4, 4, 4), dtype=np.uint8)

        claimed_ids = set()

        # Build terrain sprites (STATIC and ANIM)
        for spec_dict in [STATIC_ID_TO_SPEC, ANIM_ID_TO_SPEC]:
            for name, ids in spec_dict.items():
                if name not in BITMAP_SPEC:
                    continue

                layers = BITMAP_SPEC[name]
                sprite_anim = np.zeros((8, 4, 4, 4), dtype=np.uint8)

                for color_name, grid_str in layers:
                    if color_name not in PALETTE:
                        continue

                    pal_val = PALETTE[color_name]
                    grid = np.array(_parse_grid(grid_str))
                    mask = grid == 1

                    if isinstance(pal_val, list):
                        colors = pal_val
                    else:
                        colors = [pal_val] * 8

                    for f in range(8):
                        rgb = colors[f]
                        if len(rgb) == 3:
                            sprite_anim[f, mask] = [*rgb, 255] # Add alpha if missing
                        else:
                            sprite_anim[f, mask] = rgb # Use existing RGBA

                for i in ids:
                    if i <= max_id and i not in claimed_ids:
                        atlas[i] = sprite_anim
                        claimed_ids.add(i)

        # Build unit sprites (with offset)
        for name, ids in UNIT_ID_TO_SPEC.items():
            if name not in BITMAP_SPEC:
                continue

            layers = BITMAP_SPEC[name]
            sprite_anim = np.zeros((8, 4, 4, 4), dtype=np.uint8)

            for color_name, grid_str in layers:
                if color_name not in PALETTE:
                    continue

                pal_val = PALETTE[color_name]
                grid = np.array(_parse_grid(grid_str))
                mask = grid == 1

                if isinstance(pal_val, list):
                    colors = pal_val
                else:
                    colors = [pal_val] * 8

                for f in range(8):
                    # Unit sprites only render on frames 2-5 (matching old behavior)
                    if not (1 < f < 6):
                        continue
                    rgb = colors[f]
                    if len(rgb) == 3:
                        sprite_anim[f, mask] = [*rgb, 255] # Add alpha if missing
                    else:
                        sprite_anim[f, mask] = rgb # Use existing RGBA

            for i in ids:
                # Correctly calculate offset_id by adding UNIT_ID_OFFSET at this stage
                offset_id = i + UNIT_ID_OFFSET
                if offset_id <= max_id and offset_id not in claimed_ids:
                    atlas[offset_id] = sprite_anim
                    claimed_ids.add(offset_id)

        logger.info(f"Atlas built. Size: {atlas.nbytes / 1024:.2f} KB")
        return atlas
