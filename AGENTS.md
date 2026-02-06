# BattleMapsBot Agent Guidelines

This document provides essential instructions for AI agents working on the BattleMapsBot repository.

## 1. Project Context
BattleMapsBot is a Discord utility bot for the AWBW (Advance Wars By Web) server.
- **Framework:** `discord.py` (v2.0+) using Application Commands (Slash Commands).
- **Package Manager:** `uv` is used for dependency management and running commands.
- **Python Version:** >= 3.12 (Check `pyproject.toml` or `.python-version`).
- **Structure:** Source code is located in `src/`.

## 2. Build & Run Commands
Always use `uv run` to execute commands within the project environment.

### Setup
```bash
uv sync
```

### Running the Bot
```bash
uv run src/main.py
```

### Linting, Formatting & Types
The project uses `ruff` for linting/formatting and `pyright` for static type checking.

```bash
# Check for linting errors
uv run ruff check .

# Fix linting errors automatically where possible
uv run ruff check --fix .

# Format code
uv run ruff format .

# Run static type checking (Pyright)
# Note: Pyright is configured via pyrightconfig.json
uv run pyright .
```

### Testing
**Important:** There are currently **no automated tests** (pytest is not configured).
- **Do not run `pytest`**.
- **Verification:** You must manually verify changes by running the bot and testing the relevant commands (e.g., `/map <id>`) or logic.
- **Self-Verification:** When implementing complex logic (e.g., rendering algorithms), create a small, temporary script to verify the output before integrating it.

## 3. Code Style Guidelines

### Imports
Follow this order:
1.  **Standard Library** (`import os`, `import json`, `import asyncio`)
2.  **Third-Party** (`import discord`, `import numpy`, `import aiohttp`)
3.  **Local Application** (`from src.core...`, `from src.utils...`)

### Naming Conventions
- **Classes:** `PascalCase` (e.g., `MapRepository`, `AW2Renderer`)
- **Functions/Methods:** `snake_case` (e.g., `get_map_data`, `render_map`)
- **Variables:** `snake_case` (e.g., `map_id`, `preview_bytes`)
- **Constants:** `SCREAMING_SNAKE_CASE` (e.g., `CACHE_TTL_HOURS`)

### Types & Annotations
- Use Python type hints extensively.
- Run `uv run pyright` to verify types.
- Common imports: `from typing import Optional, Dict, Any, List`

### Async/Await
- **Network I/O:** Always use `aiohttp` for HTTP requests. **Never** use blocking `requests` or `urllib`.
- **File I/O:** For small files, standard synchronous I/O is acceptable. For larger operations, consider running in an executor:
  ```python
  loop = asyncio.get_running_loop()
  await loop.run_in_executor(None, self._heavy_operation, args)
  ```

### Error Handling & Logging
- **Logging:** Use the `logging` module. Do not use `print()`.
  ```python
  import logging
  logger = logging.getLogger(__name__)
  logger.error(f"Error doing X: {e}")
  ```
- **Exceptions:** Catch specific exceptions where possible. Log full tracebacks for unexpected errors using `traceback.print_exc()` or `logger.exception()`.
- **User Feedback:** If a command fails, provide a user-friendly error message via `interaction.followup.send()`.

## 4. Architecture & Design
- **Core (`src/core/`):** Contains business logic (API, DB, Rendering).
    - `repository.py`: Offline-first data layer (SQLite + Filesystem).
    - `aw2_renderer.py`: **Numpy-based** renderer. Avoid `PIL` pixel loops for performance.
- **Commands (`src/cogs/`):** Discord command handlers.
    - Keep logic in `src/core` and use Cogs for interface/handling.
- **Configuration:** Use `src.config` for accessing configuration values.

## 5. Key Constraints
- **No External Cloud:** Use SQLite (`data/maps.db`) and local files (`cache/`).
- **Performance:** Optimize for speed. Map rendering should be fast.
- **Rate Limiting:** Respect AWBW rate limits (2 req/s). Use `AWBWClient` or `MapRepository`.

## 6. Workflow for Agents
1.  **Explore:** Use `ls -R` or `find` to locate relevant files.
2.  **Read:** Read existing code to understand patterns.
3.  **Plan:** Create a plan before editing.
4.  **Edit:** Apply changes.
5.  **Verify:** Run linting (`ruff`) and type checking (`pyright`). Manually verify functionality if possible.
