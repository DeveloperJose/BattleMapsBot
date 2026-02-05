import numpy as np
import logging
from src.core.data import (
    SPRITES,
    PALETTE,
    STATIC_ID_TO_SPEC,
    ANIM_ID_TO_SPEC,
    UNIT_ID_TO_SPEC,
)

logger = logging.getLogger(__name__)


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
        # Determine max ID
        max_id = 0
        all_specs = [STATIC_ID_TO_SPEC, ANIM_ID_TO_SPEC, UNIT_ID_TO_SPEC]
        for d in all_specs:
            for ids in d.values():
                if ids:
                    max_id = max(max_id, max(ids))

        # Populate animated_ids set
        # Terrain animations
        for ids in ANIM_ID_TO_SPEC.values():
            self.animated_ids.update(ids)
        # Unit animations (implicitly animated via flashing, but good to track)
        for ids in UNIT_ID_TO_SPEC.values():
            self.animated_ids.update(ids)

        # Shape: (MaxID + 1, 8, 4, 4, 4)  (Frame, RGBA)
        # Using uint16 for ID indexing, so max_id < 65536
        atlas = np.zeros((max_id + 1, 8, 4, 4, 4), dtype=np.uint8)

        # Helper to parse grid string
        def parse_grid(grid_str):
            lines = grid_str.strip().split()
            # Ensure 4x4
            grid = []
            for line in lines:
                row = [int(c) for c in line.strip()]
                if len(row) != 4:
                    # fallback or error?
                    row = [0, 0, 0, 0]
                grid.append(row)
            while len(grid) < 4:
                grid.append([0, 0, 0, 0])
            return grid

        # Combine all dicts
        full_spec = {}
        for d in all_specs:
            full_spec.update(d)

        for name, ids in full_spec.items():
            if name not in SPRITES:
                continue

            layers = SPRITES[name]
            # Start with transparent 8x4x4x4
            sprite_anim = np.zeros((8, 4, 4, 4), dtype=np.uint8)

            for color_name, grid_str in layers:
                if color_name not in PALETTE:
                    continue

                pal_val = PALETTE[color_name]
                grid = np.array(parse_grid(grid_str))  # (4,4) 0s and 1s
                mask = grid == 1

                # Check if palette is static (tuple) or animated (list)
                if isinstance(pal_val, list):
                    # Animated color
                    colors = pal_val
                    # Ensure we have 8 frames, wrap or cycle if needed, but BLINK is exactly 8
                    if len(colors) != 8:
                        # Fallback: extend or truncate
                        # For now assume 8
                        pass
                else:
                    # Static color: repeat 8 times
                    colors = [pal_val] * 8

                for f in range(8):
                    rgb = colors[f]
                    # Write RGB
                    sprite_anim[f, mask, :3] = rgb
                    # Write Alpha (255)
                    sprite_anim[f, mask, 3] = 255

            # Assign to all IDs for this sprite
            for i in ids:
                if i <= max_id:
                    atlas[i] = sprite_anim

        logger.info(f"Atlas built. Size: {atlas.nbytes / 1024:.2f} KB")
        return atlas
