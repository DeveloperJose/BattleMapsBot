import discord
from discord import app_commands
from discord.ext import commands
import traceback
from src.core.repository import MapRepository

class Admin(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.repo = MapRepository()

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        is_owner = await self.bot.is_owner(interaction.user)
        if not is_owner:
            await interaction.response.send_message("You are not authorized to use this command.", ephemeral=True)
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

        msg = f"**Reloaded ({len(reloaded)}):**\n" + "\n".join(reloaded)
        if failed:
            msg += f"\n\n**Failed ({len(failed)}):**\n" + "\n".join(failed)

        await self.bot.tree.sync()
        msg += "\n\nSlash commands synced."

        await interaction.followup.send(msg)

    @app_commands.command(name="map_refresh", description="Refresh a map's data and cache")
    @app_commands.describe(awbw_id="The ID of the map to refresh")
    async def map_refresh(self, interaction: discord.Interaction, awbw_id: int):
        await interaction.response.defer(ephemeral=True)

        try:
            self.repo.clear_cache(awbw_id)
            data = await self.repo.get_map_data(awbw_id, refresh=True)
            await interaction.followup.send(f"Successfully refreshed map {awbw_id}: **{data.get('name')}**")
        except Exception as e:
            await interaction.followup.send(f"Failed to refresh map {awbw_id}: {e}")

    @app_commands.command(name="map_purge_cache", description="Purge ALL map caches (DB and Files)")
    async def map_purge_cache(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        try:
            self.repo.clear_cache(None)
            await interaction.followup.send("All map caches purged (Database and Files).")
        except Exception as e:
            await interaction.followup.send(f"Failed to purge cache: {e}")

async def setup(bot: commands.Bot):
    await bot.add_cog(Admin(bot))
