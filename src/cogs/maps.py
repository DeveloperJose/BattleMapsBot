import discord
from discord import app_commands
from discord.ext import commands
import re
from src.utils.awmap import AWMap, AWMinimap
import traceback

# Regex to find AWBW map links
RE_AWL = re.compile(r"(http[s]?://)?awbw.amarriner.com/(glenstorm/|2030/)?prevmaps.php\?maps_id=(?P<id>[0-9]+)(?i)")

class Maps(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def generate_map_preview(self, awbw_id: int) -> tuple[discord.Embed, discord.File] | None:
        """Generates the embed and file for a map preview."""
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
            
            return embed, file
            
        except Exception as e:
            print(f"Error generating map {awbw_id}: {e}")
            traceback.print_exc()
            return None

    @app_commands.command(name="map", description="Preview an AWBW map")
    @app_commands.describe(awbw_id="The ID of the AWBW map")
    async def map_preview(self, interaction: discord.Interaction, awbw_id: int):
        # Defer response as map generation might take > 3 seconds
        await interaction.response.defer()
        
        result = await self.generate_map_preview(awbw_id)
        
        if result:
            embed, file = result
            await interaction.followup.send(embed=embed, file=file)
        else:
            await interaction.followup.send(f"Error loading map ID {awbw_id}. Please check if the ID is valid.")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # Ignore messages from bots
        if message.author.bot:
            return

        # Check for map links
        match = RE_AWL.search(message.content)
        if match:
            map_id = int(match.group("id"))
            # Trigger typing to indicate processing
            async with message.channel.typing():
                result = await self.generate_map_preview(map_id)
                
                if result:
                    embed, file = result
                    await message.reply(embed=embed, file=file, mention_author=False)

async def setup(bot: commands.Bot):
    await bot.add_cog(Maps(bot))
