# BattleMaps Bot

A discord bot for previewing Advance Wars By Web (AWBW) maps.

## Features

- `/map <awbw_id>`: Generates a preview image (PNG or GIF) of an AWBW map.
- **Link Detection**: Automatically generates previews when an AWBW map link is posted in chat.
- **Hot-Reloading**: Use `/reload` (owner only) to update code without restarting.

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

## Permissions & Roles

### Discord Developer Portal
**Crucial**: You must enable **Message Content Intent** for the bot to detect map links.
1. Go to the [Discord Developer Portal](https://discord.com/developers/applications/).
2. Select your application -> **Bot**.
3. Scroll down to **Privileged Gateway Intents**.
4. Toggle **MESSAGE CONTENT INTENT** to **ON**.
5. Save changes.

### Server Permissions
The bot requires the following permissions in the server/channel to function:
*   **View Channels**
*   **Send Messages and Create Posts**
*   **Send Messages in Threads and Posts**
*   **Embed Links**
*   **Attach Files**

If the bot appears "offline" or doesn't respond to links, check that it has both **View Channels** and **Send Messages** permissions in the channel.
