"""AW2 Sprite Atlas builder and loader.

Builds a compressed sprite atlas from AW2 terrain GIFs.
Filters: *.gif, exclude _rain, _snow, gs_ prefixes.
Outputs: data/sprites/aw2_atlas.npz
"""

import re
import numpy as np
from pathlib import Path
from PIL import Image
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)

TILE_SIZE = 16
SPRITE_DIR = Path("/home/devj/local-arch/code/awbw/public_html/terrain/aw2")
ATLAS_PATH = Path("data/sprites/aw2_atlas.npz")

# Regex to filter files:
# - Must end with .gif
# - Must NOT contain _rain or _snow
# - Must NOT start with gs_
VALID_SPRITE_PATTERN = re.compile(r'^(?!gs_).*\.gif$')
EXCLUDE_WEATHER_PATTERN = re.compile(r'_(rain|snow)\.gif$')


def _should_include_file(filename: str) -> bool:
    """Check if a file should be included in the atlas."""
    if not VALID_SPRITE_PATTERN.match(filename):
        return False
    if EXCLUDE_WEATHER_PATTERN.search(filename):
        return False
    return True


def _extract_sprite_name(filename: str) -> Optional[str]:
    """Extract sprite name from filename (without .gif extension)."""
    if not filename.endswith('.gif'):
        return None
    return filename[:-4]  # Remove .gif extension


def _load_gif_frame(path: Path) -> Optional[np.ndarray]:
    """Load first frame from GIF file as RGBA numpy array."""
    try:
        with Image.open(path) as img:
            # Convert to RGBA if needed
            if img.mode != 'RGBA':
                img = img.convert('RGBA')
            
            # Get first frame
            frame = np.array(img)
            
            # Ensure correct shape (H, W, 4)
            if len(frame.shape) == 3 and frame.shape[2] == 4:
                return frame
            elif len(frame.shape) == 3 and frame.shape[2] == 3:
                # Add alpha channel
                alpha = np.full((frame.shape[0], frame.shape[1], 1), 255, dtype=np.uint8)
                return np.concatenate([frame, alpha], axis=2)
            else:
                logger.warning(f"Unexpected image shape: {frame.shape} for {path}")
                return None
    except Exception as e:
        logger.warning(f"Failed to load {path}: {e}")
        return None


def build_atlas(force: bool = False) -> Dict[str, np.ndarray]:
    """Build sprite atlas from AW2 terrain GIFs.
    
    Args:
        force: If True, rebuild even if atlas exists.
        
    Returns:
        Dictionary mapping sprite names to RGBA arrays at native resolution.
    """
    if ATLAS_PATH.exists() and not force:
        logger.info(f"Loading existing atlas from {ATLAS_PATH}")
        return load_atlas()
    
    logger.info(f"Building sprite atlas from {SPRITE_DIR}")
    
    if not SPRITE_DIR.exists():
        raise FileNotFoundError(f"Sprite directory not found: {SPRITE_DIR}")
    
    atlas = {}
    
    for gif_file in sorted(SPRITE_DIR.glob("*.gif")):
        filename = gif_file.name
        
        if not _should_include_file(filename):
            continue
        
        sprite_name = _extract_sprite_name(filename)
        if sprite_name is None:
            continue
        
        sprite_data = _load_gif_frame(gif_file)
        if sprite_data is None:
            continue
        
        # Validate that it's a proper RGBA image
        if len(sprite_data.shape) != 3 or sprite_data.shape[2] != 4:
            logger.warning(f"Unexpected sprite shape {sprite_data.shape} for {filename}, skipping")
            continue
        
        # Store at native resolution - don't resize
        atlas[sprite_name] = sprite_data
        logger.debug(f"Added sprite: {sprite_name} ({sprite_data.shape[0]}x{sprite_data.shape[1]})")
    
    logger.info(f"Built atlas with {len(atlas)} sprites")
    
    # Save to compressed NPZ
    ATLAS_PATH.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(ATLAS_PATH, **atlas)
    logger.info(f"Saved atlas to {ATLAS_PATH}")
    
    return atlas


def load_atlas() -> Dict[str, np.ndarray]:
    """Load sprite atlas from NPZ file.
    
    Returns:
        Dictionary mapping sprite names to 16x16x4 RGBA arrays.
    """
    if not ATLAS_PATH.exists():
        return build_atlas()
    
    data = np.load(ATLAS_PATH)
    atlas = {key: data[key] for key in data.files}
    logger.info(f"Loaded {len(atlas)} sprites from atlas")
    return atlas


class SpriteAtlas:
    """Lazy-loading sprite atlas singleton."""
    
    _instance: Optional['SpriteAtlas'] = None
    _atlas: Optional[Dict[str, np.ndarray]] = None
    
    def __new__(cls) -> 'SpriteAtlas':
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._atlas is None:
            self._atlas = load_atlas()
    
    def get(self, name: str) -> Optional[np.ndarray]:
        """Get sprite by name. Returns None if not found."""
        return self._atlas.get(name)
    
    def has(self, name: str) -> bool:
        """Check if sprite exists in atlas."""
        return name in self._atlas
    
    @property
    def sprite_names(self):
        """Return list of all sprite names."""
        return list(self._atlas.keys())
    
    def __len__(self) -> int:
        return len(self._atlas)
