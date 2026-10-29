# BattleMaps Bot

A Discord bot for previewing Advance Wars By Web (AWBW) maps.

![BattleMaps Bot map preview](battlemaps_preview.png)

## What it does

BattleMaps Bot brings AWBW maps into Discord. Paste a map link or run `/map <awbw_id>` and it replies with a rendered preview, property counts, and the map's predeployed units. It can also watch chat and preview map links as they appear.

Server owners get a small set of maintenance commands for reloading, syncing, and refreshing map data.

## Community code archive

Scripts, snippets, and project links shared by the AWBW community in the "Community Development" thread are indexed in [community-code/README.md](community-code/README.md). The archive excludes raw messages, media, and archives; see [community-code/NOTICE.md](community-code/NOTICE.md) for attribution and removal requests.

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

## Map preview tabs and league tiers

Tabs are Preview, League Info, Properties. League Info is shown only for maps in the current league snapshot; other maps retain Preview and Properties. Map titles omit the [Map] prefix. The map data fetch time appears in the embed footer using a native Discord timestamp. The league settings fetch age appears as a Discord relative timestamp in the embed description. Both reflect successful fetch times, so reading cached data does not reset the age.

The public league API snapshot is shared across all maps and saved to `data/league.db` beside the persistent stats database (override with `LEAGUE_DB_PATH`). A background task checks every five minutes and refreshes data after six hours. The first preview can also populate an empty cache. Concurrent requests share one refresh; failures retain the last successful snapshot and retry after five minutes. Maps absent from the current pool have no League Info tab, regardless of historical category labels. The tab shows enabled CO tiers and the setup-specific unit bans, unit limit, and capture limit.
