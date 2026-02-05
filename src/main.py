import discord
from discord import app_commands
from discord.ext import commands
from src.config import DISCORD_TOKEN
from src.utils.awmap import AWMap, AWMinimap
import io
import sys

# Ensure src is in path if running as module or script
# but typically uv run python src/main.py works if configured right
# We will see.

class BattleMapsBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        # Message content might be needed if we were using prefix commands, but for slash interactions it's fine.
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        await self.tree.sync()
        print("Commands synced")

    async def on_ready(self):
        print(f'Logged in as {self.user} (ID: {self.user.id})')

bot = BattleMapsBot()

@bot.tree.command(name="map", description="Preview an AWBW map")
@app_commands.describe(awbw_id="The ID of the AWBW map")
async def map_preview(interaction: discord.Interaction, awbw_id: int):
    # Defer response as map generation might take > 3 seconds
    await interaction.response.defer()
    
    try:
        awmap = AWMap()
        # Verify connection implicitly via https, but allow failure
        await awmap.from_awbw(awbw_id=awbw_id)
        
        # Manually create minimap to check for animation
        minimap = AWMinimap(awmap)
        image_bytes = minimap.map
        
        # Check if animated
        is_animated = minimap.animated
        ext = "gif" if is_animated else "png"
        filename = f"awbw_{awbw_id}.{ext}"
        
        file = discord.File(image_bytes, filename=filename)
        
        embed = discord.Embed(title=awmap.title, url=f"https://awbw.amarriner.com/prevmaps.php?maps_id={awbw_id}")
        embed.set_image(url=f"attachment://{filename}")
        embed.set_footer(text=f"Map by {awmap.author}")
        
        await interaction.followup.send(embed=embed, file=file)
        
    except Exception as e:
        # Print error to console for debugging
        import traceback
        traceback.print_exc()
        await interaction.followup.send(f"Error loading map: {e}")

if __name__ == "__main__":
    if not DISCORD_TOKEN:
        print("Error: DISCORD_TOKEN not found in .env")
        print("Please create a .env file with DISCORD_TOKEN=your_token_here")
    else:
        bot.run(DISCORD_TOKEN)
