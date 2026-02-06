"""
Regression test: Compare old PIL-based renderer vs new Numpy-based renderer
"""
import sys
import os
import asyncio
import json
import io
from PIL import Image, ImageChops

# Add paths
sys.path.insert(0, os.getcwd())
sys.path.insert(0, os.path.join(os.getcwd(), 'archive'))

from src.core.renderer import NumpyRenderer
from src.core.repository import MapRepository
from utils.awmap import AWMap
from utils.data.element_id import AWBW_UNIT_CODE, AWBW_COUNTRY_CODE

OUTPUT_DIR = "test_output/regression"
os.makedirs(OUTPUT_DIR, exist_ok=True)
CACHE_FILE = "tests/map_ids_cache.json"


def render_old(map_data: dict) -> io.BytesIO:
    """Render map using old PIL-based renderer."""
    aw_map = AWMap()
    
    # AWBW API returns terr as [x][y], AWMap expects [y][x]
    terr = map_data["terr"]
    terr_rows = [list(r) for r in zip(*terr)]
    aw_map._parse_awbw_csv(terr_rows)
    
    for unit in map_data.get("unit", []):
        u_id = unit["id"]
        u_x = unit["x"]
        u_y = unit["y"]
        u_ctry = unit["ctry"]
        
        main_id = AWBW_UNIT_CODE.get(u_id)
        main_ctry = AWBW_COUNTRY_CODE.get(u_ctry)
        
        if main_id is not None and main_ctry is not None:
             aw_map.tile(u_x, u_y).mod_unit(main_id, main_ctry)

    return aw_map.minimap


def render_new(map_data: dict, renderer: NumpyRenderer) -> io.BytesIO:
    """Render map using new Numpy-based renderer."""
    _, img_bytes = renderer.render_map(map_data)
    return img_bytes


def compare_frames(old_img: Image.Image, new_img: Image.Image, map_id: int) -> bool:
    """Compare two images frame by frame. Return True if identical."""
    # Get all frames from old
    old_frames = []
    if getattr(old_img, "is_animated", False):
        for i in range(old_img.n_frames):
            old_img.seek(i)
            old_frames.append(old_img.convert("RGBA"))
    else:
        old_frames.append(old_img.convert("RGBA"))
    
    # Get all frames from new
    new_frames = []
    if getattr(new_img, "is_animated", False):
        for i in range(new_img.n_frames):
            new_img.seek(i)
            new_frames.append(new_img.convert("RGBA"))
    else:
        new_frames.append(new_img.convert("RGBA"))
    
    # Compare frame by frame
    for frame_idx, (old_frame, new_frame) in enumerate(zip(old_frames, new_frames)):
        diff = ImageChops.difference(old_frame, new_frame)
        if diff.getbbox():
            # Mismatch found - save debug images
            print(f"❌ Map {map_id}: MISMATCH in frame {frame_idx}")
            diff.save(os.path.join(OUTPUT_DIR, f"{map_id}_diff_f{frame_idx}.png"))
            old_frame.save(os.path.join(OUTPUT_DIR, f"{map_id}_old_f{frame_idx}.png"))
            new_frame.save(os.path.join(OUTPUT_DIR, f"{map_id}_new_f{frame_idx}.png"))
            return False
    
    return True


def compare_images(old_bytes: io.BytesIO, new_bytes: io.BytesIO, map_id: int) -> bool:
    """Compare two rendered maps. Return True if identical."""
    old_img = Image.open(old_bytes)
    new_img = Image.open(new_bytes)

    if old_img.size != new_img.size:
        print(f"❌ Map {map_id}: SIZE MISMATCH - Old: {old_img.size}, New: {new_img.size}")
        return False
    
    return compare_frames(old_img, new_img, map_id)


async def main():
    # Load map IDs to test
    if not os.path.exists(CACHE_FILE):
        print(f"❌ Cache file not found: {CACHE_FILE}")
        sys.exit(1)
    
    with open(CACHE_FILE, 'r') as f:
        map_ids = json.load(f)
    
    print(f"🧪 Testing {len(map_ids)} maps...")
    print("=" * 50)
    
    repo = MapRepository()
    renderer = NumpyRenderer()
    
    for i, map_id in enumerate(map_ids, 1):
        print(f"\n[{i}/{len(map_ids)}] Testing map {map_id}...")
        
        # 1. Fetch map data
        try:
            map_data = await repo.get_map_data(map_id, refresh=False)
        except Exception as e:
            print(f"❌ Map {map_id}: Failed to fetch data - {e}")
            sys.exit(1)
        
        # 2. Render with old
        try:
            old_bytes = render_old(map_data)
        except Exception as e:
            print(f"❌ Map {map_id}: Old renderer failed - {e}")
            sys.exit(1)
        
        # 3. Render with new
        try:
            new_bytes = render_new(map_data, renderer)
        except Exception as e:
            print(f"❌ Map {map_id}: New renderer failed - {e}")
            sys.exit(1)
        
        # 4. Compare
        match = compare_images(old_bytes, new_bytes, map_id)
        
        if not match:
            print(f"\n❌ REGRESSION FOUND in map {map_id}")
            print("=" * 50)
            sys.exit(1)
        
        print(f"✅ Map {map_id}: OK")
    
    await repo.close()
    print(f"\n✅ All {len(map_ids)} maps passed!")


if __name__ == "__main__":
    asyncio.run(main())
