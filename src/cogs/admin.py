import discord
from discord import app_commands
from discord.ext import commands
import traceback
import os
import sys
import platform
from datetime import datetime, timedelta
from src.core.repository import MapRepository
from src.core.stats import BotStats
from src.core.aw2_atlas import SpriteAtlas


from src.config import config


class Admin(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.repo = MapRepository()
        self.start_time = datetime.now()

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        is_owner = await self.bot.is_owner(interaction.user)
        if not is_owner:
            await interaction.response.send_message(
                "You are not authorized to use this command.", ephemeral=True
            )
        return is_owner

    async def cog_unload(self):
        await self.repo.close()

    @app_commands.command(name="sync", description="Sync slash commands")
    async def sync_tree(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        await self.bot.tree.sync()
        await interaction.followup.send("Slash commands synced.")

    @app_commands.command(name="reload", description="Reload all cogs")
    async def reload_all(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        # Reload configuration
        try:
            config.reload()
            config_msg = "Config reloaded."
        except Exception as e:
            config_msg = f"Config reload failed: {e}"
            traceback.print_exc()

        reloaded = []
        failed = []

        extensions = list(self.bot.extensions.keys())

        for ext in extensions:
            try:
                await self.bot.reload_extension(ext)
                reloaded.append(ext)
            except Exception as e:
                failed.append(f"{ext}: {e}")
                traceback.print_exc()

        msg = f"{config_msg}\n\n**Reloaded ({len(reloaded)}):**\n" + "\n".join(reloaded)
        if failed:
            msg += f"\n\n**Failed ({len(failed)}):**\n" + "\n".join(failed)

        await self.bot.tree.sync()
        msg += "\n\nSlash commands synced."

        await interaction.followup.send(msg)

    @app_commands.command(
        name="map_refresh", description="Refresh a map's data and cache"
    )
    @app_commands.describe(awbw_id="The ID of the map to refresh")
    async def map_refresh(self, interaction: discord.Interaction, awbw_id: int):
        await interaction.response.defer(ephemeral=True)

        try:
            self.repo.clear_cache(awbw_id)
            data = await self.repo.get_map_data(awbw_id, refresh=True)
            await interaction.followup.send(
                f"Successfully refreshed map {awbw_id}: **{data.get('name')}**"
            )
        except Exception as e:
            await interaction.followup.send(f"Failed to refresh map {awbw_id}: {e}")

    @app_commands.command(
        name="map_purge_cache", description="Purge ALL map caches (DB only)"
    )
    async def map_purge_cache(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        try:
            self.repo.clear_cache(None)
            await interaction.followup.send("All map caches purged (Database).")
        except Exception as e:
            await interaction.followup.send(f"Failed to purge cache: {e}")

    async def stats(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        try:
            # Bot stats
            uptime = datetime.now() - self.start_time
            uptime_str = str(timedelta(seconds=int(uptime.total_seconds())))

            # Guild/Server info
            guilds = self.bot.guilds
            total_guilds = len(guilds)
            total_members = sum(g.member_count or 0 for g in guilds)
            total_channels = sum(len(g.channels) for g in guilds)

            # Build guild list (limit to 20 to avoid message too long)
            guild_list = []
            for guild in sorted(
                guilds, key=lambda g: g.member_count or 0, reverse=True
            )[:20]:
                guild_list.append(
                    f"• {guild.name} ({guild.id}) - {guild.member_count} members"
                )

            guilds_text = "\n".join(guild_list)
            if len(guilds) > 20:
                guilds_text += f"\n... and {len(guilds) - 20} more servers"

            # Cache stats
            cache_stats = self.repo.get_cache_stats()

            # Atlas stats
            atlas = SpriteAtlas()
            atlas_size_mb = atlas.size_bytes / (1024 * 1024)
            atlas_count = len(atlas)

            # Telemetry stats
            bot_stats = BotStats()
            api_stats = bot_stats.get_api_stats()
            render_stats = bot_stats.get_render_stats()

            # System info
            python_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
            discord_version = discord.__version__

            # Memory usage (rough estimate)
            try:
                import psutil

                process = psutil.Process(os.getpid())
                memory_mb = process.memory_info().rss / (1024 * 1024)
                memory_str = f"{memory_mb:.1f} MB"
            except ImportError:
                memory_str = "N/A (psutil not installed)"

            longest_render_map_id = render_stats.get("longest_map_id", 0)
            if longest_render_map_id:
                longest_render_str = f"{render_stats['longest'] * 1000:.1f} ms (Map ID: {longest_render_map_id})"
            else:
                longest_render_str = f"{render_stats['longest'] * 1000:.1f} ms"

            msg = (
                f"**🤖 Bot Statistics**\n"
                f"```\n"
                f"Uptime:           {uptime_str}\n"
                f"Python:           {python_version}\n"
                f"Discord.py:       {discord_version}\n"
                f"Platform:         {platform.system()} {platform.release()}\n"
                f"Memory Usage:     {memory_str}\n"
                f"```\n"
                f"**📊 Server Info**\n"
                f"```\n"
                f"Total Servers:    {total_guilds}\n"
                f"Total Members:    {total_members}\n"
                f"Total Channels:   {total_channels}\n"
                f"```\n"
                f"**🗄️ Cache & Atlas**\n"
                f"```\n"
                f"DB Cache Size:    {cache_stats['db_size_mb']:.2f} MB / {cache_stats['size_limit_mb']} MB\n"
                f"Cached Maps:      {cache_stats['entry_count']}\n"
                f"Cache TTL:        {cache_stats['ttl_hours']} hours\n"
                f"Atlas Size:       {atlas_size_mb:.2f} MB\n"
                f"Atlas Sprites:    {atlas_count}\n"
                f"```\n"
                f"**🌐 API Statistics**\n"
                f"```\n"
                f"Total Requests:   {api_stats['total_uptime']} (Uptime)\n"
                f"Last 24 Hours:    {api_stats['total_24h']}\n"
                f"Last Hour:        {api_stats['total_1h']}\n"
                f"Last Minute:      {api_stats['total_1m']}\n"
                f"Avg Duration:     {api_stats['average'] * 1000:.1f} ms\n"
                f"Longest Req:      {api_stats['longest'] * 1000:.1f} ms\n"
                f"```\n"
                f"**🎨 Render Statistics**\n"
                f"```\n"
                f"Total Renders:    {render_stats['count']}\n"
                f"Total Time:       {render_stats['total_time']:.2f} s\n"
                f"Avg Render:       {render_stats['average'] * 1000:.1f} ms\n"
                f"Longest Render:   {longest_render_str}\n"
                f"```"
            )

            # Send guild list separately if it's long
            if len(msg) + len(guilds_text) < 1900:
                msg += (
                    f"\n**🏠 Servers ({total_guilds} total):**\n```\n{guilds_text}\n```"
                )
                await interaction.followup.send(msg)
            else:
                await interaction.followup.send(msg)
                await interaction.followup.send(
                    f"**🏠 Servers ({total_guilds} total):**\n```\n{guilds_text}\n```"
                )

        except Exception as e:
            await interaction.followup.send(f"Failed to get stats: {e}")
            traceback.print_exc()


async def setup(bot: commands.Bot):
    await bot.add_cog(Admin(bot))
