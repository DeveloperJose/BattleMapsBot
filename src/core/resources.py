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

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SpriteCache, cls).__new__(cls)
            cls._instance.animated_ids = set()
            cls._instance.atlas = cls._instance._build_atlas()
        return cls._instance

    def _build_atlas(self):
        logger.info("Building Sprite Atlas...")
        max_terr_id = 0
        max_unit_id = 0

        # Find max terrain ID
        for d in [STATIC_ID_TO_SPEC, ANIM_ID_TO_SPEC]:
            for ids in d.values():
                if ids:
                    max_terr_id = max(max_terr_id, max(ids))

        # Find max unit ID
        for ids in UNIT_ID_TO_SPEC.values():
            if ids:
                max_unit_id = max(max_unit_id, max(ids))

        # Total atlas size: terrain IDs + offset unit IDs
        max_id = max(max_terr_id, UNIT_ID_OFFSET + max_unit_id)

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
                        sprite_anim[f, mask, :3] = rgb
                        sprite_anim[f, mask, 3] = 255

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
                    sprite_anim[f, mask, :3] = rgb
                    sprite_anim[f, mask, 3] = 255

            for i in ids:
                offset_id = i + UNIT_ID_OFFSET
                if offset_id <= max_id and offset_id not in claimed_ids:
                    atlas[offset_id] = sprite_anim
                    claimed_ids.add(offset_id)

        logger.info(f"Atlas built. Size: {atlas.nbytes / 1024:.2f} KB")
        return atlas
