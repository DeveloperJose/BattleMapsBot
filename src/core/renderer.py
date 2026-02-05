import numpy as np
import io
from typing import Dict, Any
from PIL import Image
from src.core.resources import SpriteCache
from src.utils.data.element_id import AWBW_TERR, AWBW_UNIT_CODE
import logging

logger = logging.getLogger(__name__)

class NumpyRenderer:
    def __init__(self):
        self.sprite_cache = SpriteCache()
        self.atlas = self.sprite_cache.atlas

    def render_map(self, map_data: Dict[str, Any]) -> io.BytesIO:
        """
        Renders the map using vectorized Numpy operations.
        Returns a PNG image as BytesIO.
        """
        width = map_data["size_w"]
        height = map_data["size_h"]
        terrain_ids = np.array(map_data["terr"], dtype=np.int32) # (H, W)
        
        # 1. Convert AWBW IDs to Internal IDs
        # We need a vectorized lookup. Since AWBW IDs are sparse, a direct array lookup might be too big if IDs are huge.
        # But AWBW IDs seem to be < 2000. Let's check.
        # Max ID in AWBW_TERR is around 209 (Noir Eclipse Port).
        # We can use a lookup array.
        
        # Build lookup table for Terrain: AWBW_ID -> (Internal_Terr_ID, Country_ID)
        # Note: We need to handle awareness. This is tricky to vectorize perfectly without complex logic.
        # For V1, let's do a semi-vectorized approach or just basic mapping first.
        # Actually, let's try to map AWBW ID directly to the Sprite ID (Internal ID) if possible.
        # But Internal ID depends on Awareness (which depends on neighbors).
        
        # --- Awareness Step ---
        # This is the "slow" part in Python loops.
        # However, we can do it with numpy shifting!
        # internal_ids = lookup[terrain_ids]
        # neighbors = ... shift internal_ids ...
        # awareness_mask = ...
        # final_ids = base_ids + awareness_mask lookup
        
        # For now, to keep it simple and robust, let's just map AWBW -> Internal Base ID 
        # and skip complex awareness (pipes/shores) for the very first pass 
        # OR implement a basic awareness loop.
        
        # Let's map AWBW ID -> Internal ID (Terr + Country*10 or something?)
        # The atlas uses just the integer ID.
        # Wait, the atlas uses the IDs from `STATIC_ID_TO_SPEC` etc.
        # Those are e.g. "plain": [1, 12]. 1 is normal, 12 is broken seam.
        # `AWBW_TERR` maps 1 -> (1, 0) (Plain, Neutral)
        
        # We need to construct the final "Sprite ID" for the atlas.
        # The logic in `AWMinimap` was: `terr = tile.terr + (tile.t_ctry * 10)`
        # And `unit = tile.unit + (tile.u_ctry * 100)`
        
        # Let's build a translation table: AWBW_ID -> Base Sprite ID
        max_awbw_id = max(AWBW_TERR.keys()) + 1
        terr_lookup = np.zeros(max_awbw_id, dtype=np.int32)
        
        for awbw_id, (terr, ctry) in AWBW_TERR.items():
            terr_lookup[awbw_id] = terr + (ctry * 10)
            
        # Apply lookup
        # Some map data might have IDs outside range, handle safely?
        # AWBW IDs are generally safe.
        base_sprite_ids = np.zeros_like(terrain_ids)
        valid_mask = terrain_ids < max_awbw_id
        base_sprite_ids[valid_mask] = terr_lookup[terrain_ids[valid_mask]]
        
        # --- Units ---
        # Create a layer for units
        unit_grid = np.zeros((height, width), dtype=np.int32)
        
        # Predeployed units
        # "unit": [{"id": 1, "x": 1, "y": 1, "ctry": "os"}, ...]
        # We need to map Country Code string to Country ID.
        from src.utils.data.element_id import AWBW_COUNTRY_CODE
        
        # Map AWBW Unit ID -> Internal Unit ID
        # `AWBW_UNIT_CODE`: 1 -> 1 (Infantry)
        
        for u in map_data.get("unit", []):
            u_id = u["id"]
            x, y = u["x"], u["y"]
            ctry_str = u["ctry"]
            
            internal_unit = AWBW_UNIT_CODE.get(u_id, 0)
            ctry_id = AWBW_COUNTRY_CODE.get(ctry_str, 0)
            
            # Formula: unit + (ctry * 100)
            sprite_id = internal_unit + (ctry_id * 100)
            
            # AWBW uses 0-based or 1-based coords?
            # API doc says "x": 1. Usually 0-based in array.
            # Let's check `awbw_api.py`.
            # "terr": [[1,2,3],...] By column, then by row: terr[y][x]
            # Wait, `get_map` implementation: `map_data["terr"] = [list(r) for r in zip(*j_map["Terrain Map"])]`
            # This transposes it? 
            # Original JSON is Column-Major (x, y)?
            # "By column, then by row" implies list of columns.
            # `zip(*...)` converts list of columns to list of rows.
            # So `map_data["terr"]` is row-major `[y][x]`.
            # Units `x`, `y` are likely 0-based in our array access?
            # In `AWMinimap`: `awmap.tile(x, y)`
            # Let's assume 0-based for now. API example says 1, but maybe that's 1-based?
            # "x": 1. If width is 3. 
            # Standard AWBW is 0-based for arrays but X/Y in JSON might be 0 or 1.
            # Usually coordinate systems in these APIs are 0-based.
            # Let's assume 0-based.
            
            if 0 <= y < height and 0 <= x < width:
                unit_grid[y, x] = sprite_id

        # --- Vectorized Rendering ---
        
        # 1. Look up terrain sprites from Atlas
        # Atlas shape: (MaxID, 4, 4, 4)
        # base_sprite_ids shape: (H, W)
        # Result: (H, W, 4, 4, 4)
        terrain_sprites = self.atlas[base_sprite_ids] 
        
        # 2. Look up unit sprites
        unit_sprites = self.atlas[unit_grid] # (H, W, 4, 4, 4)
        
        # 3. Composite (Alpha Blending)
        # We need to overlay units on terrain.
        # Basic alpha blending: result = unit * unit_alpha + terrain * (1 - unit_alpha)
        # Since our sprites are 0 or 255 alpha (mostly), simple masking works.
        # But let's do it properly for future proofing.
        
        # Normalize to 0..1 float for blending or stick to uint8?
        # uint8 is faster.
        # If unit alpha > 0, show unit, else terrain. (Since units are opaque in non-transparent areas)
        
        unit_mask = unit_sprites[..., 3] > 0 # (H, W, 4, 4) boolean
        # Expand mask for RGB broadcasting: (H, W, 4, 4, 1) -> broadcast to 4 channels
        unit_mask_4 = np.repeat(unit_mask[..., np.newaxis], 4, axis=-1)
        
        # Composite
        final_grid = np.where(unit_mask_4, unit_sprites, terrain_sprites) # (H, W, 4, 4, 4)
        
        # 4. Reshape to final Image
        # We have (H, W, 4, 4, 4) -> (y, x, sub_y, sub_x, rgba)
        # We want (H * 4, W * 4, 4)
        # Transpose to (H, 4, W, 4, 4) -> (Row, SubRow, Col, SubCol, Channel)
        # Reshape to (H*4, W*4, 4)
        final_image_arr = final_grid.transpose(0, 2, 1, 3, 4).reshape(height * 4, width * 4, 4)
        
        # 5. Convert to PIL
        img = Image.fromarray(final_image_arr, mode="RGBA")
        
        # 6. Resize if needed (mimic old logic)
        # Smaller maps can be sized up
        total_pixels = width * height
        if total_pixels <= 1600:
             img = img.resize((width * 16, height * 16), resample=Image.Resampling.NEAREST)
        elif total_pixels <= 3200:
             img = img.resize((width * 8, height * 8), resample=Image.Resampling.NEAREST)
             
        out = io.BytesIO()
        img.save(out, format="PNG")
        out.seek(0)
        return out

