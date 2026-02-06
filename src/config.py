import yaml
import os
from pathlib import Path
from typing import Any, Dict
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

class Config:
    _instance = None
    _config: Dict[str, Any] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Config, cls).__new__(cls)
            cls._instance._load_config()
        return cls._instance

    def _load_config(self):
        config_path = Path("config.yaml")
        if not config_path.exists():
            # Fallback for when running from src directory or tests
            config_path = Path("../config.yaml")
            
        if config_path.exists():
            with open(config_path, "r") as f:
                self._config = yaml.safe_load(f)
        else:
            # Default values if config.yaml is missing
            self._config = {
                "api": {
                    "map_url": "https://awbw.amarriner.com/api/map/map_info.php",
                    "rate_limit": {"calls": 2, "period": 1.0}
                },
                "cache": {
                    "db_path": "cache/maps.db",
                    "ttl_hours": 24,
                    "max_size_mb": 250
                },
                "renderer": {
                    "tile_size": 16,
                    "max_prop_extension": 16,
                    "sprite_dir": "/home/devj/local-arch/code/awbw/public_html/terrain/aw2",
                    "atlas_path": "cache/aw2_atlas.npz",
                    "fallback_color": [255, 0, 255, 255],
                    "image_size": 1024
                }
            }

    def reload(self):
        """Reload the configuration from file."""
        self._load_config()

    @property
    def api(self) -> Dict[str, Any]:
        return self._config.get("api", {})

    @property
    def cache(self) -> Dict[str, Any]:
        return self._config.get("cache", {})

    @property
    def renderer(self) -> Dict[str, Any]:
        return self._config.get("renderer", {})

# Global instance
config = Config()
