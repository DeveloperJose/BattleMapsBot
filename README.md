# BattleMaps Bot

A discord bot for previewing Advance Wars By Web (AWBW) maps.

## Features

- `/map <awbw_id>`: Generates a rich preview of an AWBW map, including a rendered image, property counts, and predeployed unit lists.
- **Link Detection**: Automatically generates a map preview when an AWBW map link is posted in chat.
- **Admin Commands**: A suite of owner-only commands including `/reload`, `/sync`, and `/map_refresh` for maintenance.

## Setup

1.  Install dependencies:
    ```bash
    uv sync
    ```

2.  Create a `.env` file for your Discord token:
    ```
    DISCORD_TOKEN=your_token_here
    ```

3.  Run the bot:
    ```bash
    uv run src/main.py
    ```

## Permissions & Intents

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
*   **Send Messages**
*   **Embed Links**
*   **Attach Files**

If the bot doesn't respond to links, check that it has both **View Channels** and **Send Messages** permissions in the channel.
