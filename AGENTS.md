# BattleMapsBot Agent Guidelines

This document provides instructions for AI agents working on the BattleMapsBot repository.

## 1. Project Context
BattleMapsBot is a Discord utility bot for the AWBW (Advance Wars By Web) server.
- **Framework:** `discord.py` (v2.0+) using Application Commands (Slash Commands).
- **Package Manager:** `uv`.
- **Python Version:** >= 3.12
- **Structure:** `src/` layout.

## 2. Architecture & Design
The bot uses a high-performance architecture for map rendering:
- **Core (`src/core/`):**
    - `awbw.py`: API Client with `aiolimiter` for rate limiting (max 2 req/s).
    - `repository.py`: Offline-first data layer using SQLite (`data/maps.db`) and Filesystem Cache (`cache/maps/`).
    - `aw2_renderer.py`: **Numpy-based** renderer using actual AW2 game sprites.
    - `aw2_atlas.py`: Manages the Sprite Atlas (builds/loads from `cache/aw2_atlas.npz`).
    - `aw2_data.py`: Contains terrain/unit to sprite name mappings.
- **Commands (`src/cogs/`):**
    - `maps.py`: Handles `/map` command using `MapRepository` and `AW2Renderer`.
    - `admin.py`: Handles admin commands (`/sync`, `/reload`, `/map_refresh`, `/map_purge_cache`).

**Key Constraints:**
- **No External Cloud:** Do not add Redis or AWS S3. Use SQLite and local files.
- **Speed:** Prefer Numpy operations for image manipulation over `PIL` loops.
- **Rate Limiting:** Always use `AWBWClient` or `MapRepository` to fetch data. Never request `awbw.amarriner.com` directly in loops without limiting.

## 3. Build & Run Commands
Always use `uv run` to execute commands within the project environment.

### Setup
```bash
uv sync
```

### Running the Bot
```bash
uv run src/main.py
```

### Linting & Formatting
The project uses `ruff` for both linting and formatting.
```bash
# Check for linting errors
uv run ruff check .

# Fix linting errors automatically where possible
uv run ruff check --fix .

# Format code
uv run ruff format .
```

### Testing
*Note: Testing frameworks (pytest) have been removed. Manual verification via bot commands is preferred.*

## 4. Code Style Guidelines

### Imports
1.  **Lib** (Standard Library)
2.  **Site** (Third-party packages: `numpy`, `discord`, `aiohttp`, `PIL`)
3.  **Local** (Project modules, relative or absolute `src.`)

### Naming Conventions
- **Classes:** `PascalCase`
- **Functions/Methods:** `snake_case`
- **Variables:** `snake_case`
- **Constants:** `SCREAMING_SNAKE_CASE`

### Async
- Prefer `aiohttp` for network requests. Avoid blocking `requests`.

## 5. File Structure
- `src/`: Main source code.
  - `main.py`: Entry point.
  - `core/`: Core business logic (API, DB, Rendering).
  - `cogs/`: Discord command modules.
  - `utils/`: Shared constants (`element_id.py`).
