# BattleMapsBot Agent Guidelines

This document provides instructions for AI agents working on the BattleMapsBot repository.

## 1. Project Context
BattleMapsBot is a Discord utility bot for the AWBW (Advance Wars By Web) server.
- **Framework:** `discord.py` (v2.0+) using Application Commands (Slash Commands).
- **Package Manager:** `uv`.
- **Python Version:** >= 3.12
- **Structure:** `src/` layout.

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
*Note: The project uses `pytest`.*
```bash
# Run all tests
uv run pytest
```

## 3. Code Style Guidelines

### Imports
1.  **Lib** (Standard Library)
2.  **Site** (Third-party packages)
3.  **Local** (Project modules, relative or absolute `src.`)

### Naming Conventions
- **Classes:** `PascalCase`
- **Functions/Methods:** `snake_case`
- **Variables:** `snake_case`
- **Constants:** `SCREAMING_SNAKE_CASE`

### Typing
- Use type hints for all function arguments and return values.
- Use `typing` module (e.g., `List`, `Union`, `Optional`) or modern syntax (`list[]`, `|`) if compatible with Python 3.12+.

### Async
- Prefer `aiohttp` for network requests. Avoid blocking `requests`.

## 4. File Structure
- `src/`: Main source code.
  - `main.py`: Entry point.
  - `config.py`: Configuration loading.
  - `utils/`: Utility modules (`awmap`, `awbw_api`, etc.).
- `archive_v1/`: Archived version 1 of the bot.

## 5. General Rules
- **Dependencies:** Do not add new dependencies without checking if an existing one suffices.
- **Safety:** Never commit secrets (tokens, passwords). Use `.env`.
