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
        max_id = 0
        all_specs = [STATIC_ID_TO_SPEC, ANIM_ID_TO_SPEC, UNIT_ID_TO_SPEC]
        for d in all_specs:
            for ids in d.values():
                if ids:
                    max_id = max(max_id, max(ids))

        for ids in ANIM_ID_TO_SPEC.values():
            self.animated_ids.update(ids)
        for ids in UNIT_ID_TO_SPEC.values():
            self.animated_ids.update(ids)

        atlas = np.zeros((max_id + 1, 8, 4, 4, 4), dtype=np.uint8)

        def parse_grid(grid_str):
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

        priority_specs = [
            (ANIM_ID_TO_SPEC, "ANIM"),
            (STATIC_ID_TO_SPEC, "STATIC"),
            (UNIT_ID_TO_SPEC, "UNIT"),
        ]

        claimed_ids = set()

        for spec_dict, spec_name in priority_specs:
            for name, ids in spec_dict.items():
                if name not in SPRITES:
                    continue

                layers = SPRITES[name]
                sprite_anim = np.zeros((8, 4, 4, 4), dtype=np.uint8)

                for color_name, grid_str in layers:
                    if color_name not in PALETTE:
                        continue

                    pal_val = PALETTE[color_name]
                    grid = np.array(parse_grid(grid_str))
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

        logger.info(f"Atlas built. Size: {atlas.nbytes / 1024:.2f} KB")
        return atlas
