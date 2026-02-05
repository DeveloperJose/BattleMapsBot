import numpy as np
import logging
from src.core.data import SPRITES, PALETTE, STATIC_ID_TO_SPEC, ANIM_ID_TO_SPEC, UNIT_ID_TO_SPEC

logger = logging.getLogger(__name__)

class SpriteCache:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SpriteCache, cls).__new__(cls)
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
        
        # Shape: (MaxID + 1, 4, 4, 4)  (RGBA)
        # Using uint16 for ID indexing, so max_id < 65536
        atlas = np.zeros((max_id + 1, 4, 4, 4), dtype=np.uint8)
        
        # Helper to parse grid string
        def parse_grid(grid_str):
            lines = grid_str.strip().split()
            # Ensure 4x4
            grid = []
            for line in lines:
                row = [int(c) for c in line.strip()]
                if len(row) != 4:
                     # fallback or error?
                     row = [0,0,0,0] 
                grid.append(row)
            while len(grid) < 4:
                grid.append([0,0,0,0])
            return grid

        # Combine all dicts
        full_spec = {}
        for d in all_specs:
            full_spec.update(d)
        
        for name, ids in full_spec.items():
            if name not in SPRITES:
                continue
                
            layers = SPRITES[name]
            # Start with transparent 4x4x4
            sprite_img = np.zeros((4, 4, 4), dtype=np.uint8)
            
            for color_name, grid_str in layers:
                if color_name not in PALETTE:
                    continue 
                
                rgb = PALETTE[color_name]
                grid = np.array(parse_grid(grid_str)) # (4,4) 0s and 1s
                
                mask = grid == 1
                # Write RGB
                sprite_img[mask, :3] = rgb
                # Write Alpha (255)
                sprite_img[mask, 3] = 255
            
            # Assign to all IDs for this sprite
            for i in ids:
                if i <= max_id:
                    atlas[i] = sprite_img
                
        logger.info(f"Atlas built. Size: {atlas.nbytes / 1024:.2f} KB")
        return atlas
