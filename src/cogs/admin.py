import discord
from discord import app_commands
from discord.ext import commands
import traceback

class Admin(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        # Only allow bot owner to use these commands
        is_owner = await self.bot.is_owner(interaction.user)
        if not is_owner:
            await interaction.response.send_message("You are not authorized to use this command.", ephemeral=True)
        return is_owner

    @app_commands.command(name="sync", description="Sync slash commands")
    async def sync_tree(self, interaction: discord.Interaction):
        """Syncs the slash command tree."""
        await interaction.response.defer(ephemeral=True)
        await self.bot.tree.sync()
        await interaction.followup.send("Slash commands synced.")

    @app_commands.command(name="reload", description="Reload all cogs")
    async def reload_all(self, interaction: discord.Interaction):
        """Reloads all loaded cogs."""
        await interaction.response.defer(ephemeral=True)
        
        reloaded = []
        failed = []
        
        # Get a list of current extensions to avoid modifying the list while iterating
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
            
        # Resync the tree after reloading
        await self.bot.tree.sync()
        msg += "\n\nSlash commands synced."
        
        await interaction.followup.send(msg)

async def setup(bot: commands.Bot):
    await bot.add_cog(Admin(bot))
