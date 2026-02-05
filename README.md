# BattleMaps Bot

A discord bot for previewing Advance Wars By Web (AWBW) maps.

## Features

- `/map <awbw_id>`: Generates a preview image (PNG or GIF) of an AWBW map.

## Setup

1.  Install dependencies:
    ```bash
    uv sync
    ```

2.  Create `.env` file:
    ```
    DISCORD_TOKEN=your_token_here
    ```

3.  Run the bot:
    ```bash
    uv run src/main.py
    ```
