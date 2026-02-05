import discord
from discord import app_commands
from discord.ext import commands
import re
import traceback
import logging
from src.core.repository import MapRepository
from src.utils.awmap import AWMap, AWMinimap

logger = logging.getLogger(__name__)

# Regex to find AWBW map links
RE_AWL = re.compile(r"(?i)(http[s]?://)?(www\.)?awbw.amarriner.com/(glenstorm/|2030/)?prevmaps.php\?maps_id=(?P<id>[0-9]+)")

class Maps(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.repo = MapRepository()

    async def cog_unload(self):
        await self.repo.close()

    async def generate_map_preview(self, awbw_id: int) -> tuple[discord.Embed, discord.File] | None:
        """Generates the embed and file for a map preview."""
        try:
            # Fetch Map Data (Cache -> API -> DB)
            map_data = await self.repo.get_map_data(awbw_id)
            
            # Render Map using AWMap (Legacy Logic with GIF support)
            awmap = AWMap().load_from_data(map_data)
            minimap = AWMinimap(awmap)
            image_bytes = minimap.map
            
            ext = "gif" if minimap.animated else "png"
            filename = f"awbw_{awbw_id}.{ext}"

            # We could save to cache here, but MapRepository cache is data-only currently.
            # We can rely on just generating it on the fly or implementing file cache later if needed.
            # For now, let's just return the file.
            
            file = discord.File(image_bytes, filename=filename)
            
            # Construct Embed
            embed = discord.Embed(
                title=map_data.get("name", f"Map {awbw_id}"),
                url=f"https://awbw.amarriner.com/prevmaps.php?maps_id={awbw_id}"
            )
            embed.set_image(url=f"attachment://{filename}")
            author = map_data.get("author", "Unknown")
            embed.set_footer(text=f"Map by {author}")
            
            return embed, file
            
        except Exception as e:
            logger.error(f"Error generating map {awbw_id}: {e}")
            traceback.print_exc()
            return None

    @app_commands.command(name="map", description="Preview an AWBW map")
    @app_commands.describe(awbw_id="The ID of the AWBW map")
    async def map_preview(self, interaction: discord.Interaction, awbw_id: int):
        # Defer response as map generation might take > 3 seconds (mostly network)
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
