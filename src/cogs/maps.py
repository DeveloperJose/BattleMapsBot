import discord
from discord import app_commands, ui
from discord.ext import commands
import re
import traceback
import logging
from urllib.parse import quote

from src.core.repository import MapRepository
from src.core.renderer import NumpyRenderer
from src.utils.awbw_data import (
    UNIT_NAMES,
    CTRY_NAMES,
)
from src.utils.map_helpers import format_k, count_properties, count_units

logger = logging.getLogger(__name__)

RE_AWL = re.compile(
    r"(?i)https?://(www\.)?awbw\.amarriner\.com/prevmaps\.php\?maps_id=(?P<id>[0-9]+)"
)


class TabbedMapView(ui.View):
    def __init__(self, awbw_id: int, embeds: dict):
        super().__init__(timeout=None)
        self.awbw_id = awbw_id
        self.embeds = embeds

    @ui.button(
        label="Preview",
        emoji="🗺️",
        style=discord.ButtonStyle.primary,
        custom_id="map_tab_preview",
    )
    async def tab_preview(self, interaction: discord.Interaction, button: ui.Button):
        await self.update_tab(interaction, button, "preview")

    @ui.button(
        label="Properties",
        emoji="🏠",
        style=discord.ButtonStyle.secondary,
        custom_id="map_tab_properties",
    )
    async def tab_properties(self, interaction: discord.Interaction, button: ui.Button):
        await self.update_tab(interaction, button, "properties")

    @ui.button(
        label="Predeployed",
        emoji="🎖️",
        style=discord.ButtonStyle.secondary,
        custom_id="map_tab_units",
    )
    async def tab_units(self, interaction: discord.Interaction, button: ui.Button):
        await self.update_tab(interaction, button, "units")

    async def update_tab(
        self, interaction: discord.Interaction, button: ui.Button, tab_name: str
    ):
        self.set_active_button(button)
        await interaction.response.edit_message(embed=self.embeds[tab_name], view=self)

    def set_active_button(self, active_button: ui.Button):
        for child in self.children:
            child.style = discord.ButtonStyle.secondary
        active_button.style = discord.ButtonStyle.primary


class Maps(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.repo = MapRepository()
        self.renderer = NumpyRenderer()

    async def cog_unload(self):
        await self.repo.close()

    def build_embeds(self, awbw_id: int, map_data: dict, image_filename: str) -> dict:
        author = map_data.get("author", "Unknown")
        author_url = f"https://awbw.amarriner.com/profile.php?username={quote(author)}"

        if author == "[Unknown]":
            author_line = "Design map by [Unknown]"
        else:
            author_line = f"Design map by [{author}]({author_url})"

        preview_links = (
            f"[Games](https://awbw.amarriner.com/gamescurrent.php?maps_id={awbw_id}) ・ "
            f"[New Game](https://awbw.amarriner.com/create.php?maps_id={awbw_id}) ・ "
            f"[Planner](https://awbw.amarriner.com/moveplanner.php?maps_id={awbw_id}) ・ "
            f"[Map Analysis](https://awbw.amarriner.com/analysis.php?maps_id={awbw_id})"
        )

        prop_counts, income = count_properties(map_data.get("terr", []))
        unit_counts = count_units(map_data.get("unit", []))

        active_ctries = [
            i for i in range(21) if prop_counts.get(i) or unit_counts.get(i)
        ]
        active_ctries.sort(key=lambda i: (0 if prop_counts.get(i) else 1, i))

        size_w = map_data.get("size_w", 0)
        size_h = map_data.get("size_h", 0)
        published = map_data.get("published", "Unknown")[:10]
        active_players = len([i for i in active_ctries if i != 0])

        header_desc = (
            f"{author_line} ・ **Players:** {active_players} ・ **Size:** {size_w}x{size_h} ・ **Published:** {published}\n\n"
            f"{preview_links}"
        )

        preview_embed = discord.Embed(
            title=map_data.get("name", f"Map {awbw_id}"),
            url=f"https://awbw.amarriner.com/prevmaps.php?maps_id={awbw_id}",
            description=header_desc,
        )
        preview_embed.set_image(url=f"attachment://{image_filename}")

        if not active_ctries:
            prop_embed = discord.Embed(
                title=map_data.get("name", f"Map {awbw_id}"),
                url=f"https://awbw.amarriner.com/prevmaps.php?maps_id={awbw_id}",
                description=f"{header_desc}\n\nNo properties found on this map.",
            )
            unit_embed = discord.Embed(
                title=map_data.get("name", f"Map {awbw_id}"),
                url=f"https://awbw.amarriner.com/prevmaps.php?maps_id={awbw_id}",
                description=f"{header_desc}\n\nNo units found on this map.",
            )
        else:
            total_props_all = sum(sum(c.values()) for c in prop_counts.values())

            hq_count = sum(p.get(101, 0) for p in prop_counts.values())
            city_count = sum(p.get(102, 0) for p in prop_counts.values())
            base_count = sum(p.get(103, 0) for p in prop_counts.values())
            air_count = sum(p.get(104, 0) for p in prop_counts.values())
            port_count = sum(p.get(105, 0) for p in prop_counts.values())

            income_props = hq_count + city_count + base_count + air_count + port_count

            base_income_k = 2 if map_data.get("is_hfog", False) else 1
            total_income_all = income_props * base_income_k

            players = map_data.get("player_count", active_players)
            funds_per_player = (
                round(total_income_all / players, 1) if players > 0 else 0
            )
            funds_per_base = (
                round(total_income_all / base_count, 1) if base_count > 0 else 0
            )

            stats_desc = (
                f"{header_desc}\n\n"
                f"**Total:** {total_props_all} props | **{format_k(total_income_all * 1000)}**/day\n"
                f"**{format_k(funds_per_player * 1000)}**/player | **{format_k(funds_per_base * 1000)}**/base"
            )

            prop_embed = discord.Embed(
                title=map_data.get("name", f"Map {awbw_id}"),
                url=f"https://awbw.amarriner.com/prevmaps.php?maps_id={awbw_id}",
                description=stats_desc,
            )

            unit_embed = discord.Embed(
                title=map_data.get("name", f"Map {awbw_id}"),
                url=f"https://awbw.amarriner.com/prevmaps.php?maps_id={awbw_id}",
                description=header_desc,
            )

            for ctry_id in active_ctries:
                name = CTRY_NAMES.get(ctry_id, f"Country {ctry_id}")
                props = prop_counts.get(ctry_id, {})
                hq = props.get(101, 0)
                city = props.get(102, 0)
                base = props.get(103, 0)
                air = props.get(104, 0)
                port = props.get(105, 0)
                tower = props.get(106, 0)
                lab = props.get(107, 0)
                inc = format_k(income.get(ctry_id, 0))

                # Build dot-separated property list
                prop_parts = []
                if hq > 0:
                    prop_parts.append(f"**HQ:** {hq}")
                if lab > 0:
                    prop_parts.append(f"**Lab:** {lab}")
                if tower > 0:
                    prop_parts.append(f"**Tower:** {tower}")
                if city > 0:
                    prop_parts.append(f"**City:** {city}")
                if base > 0:
                    prop_parts.append(f"**Base:** {base}")
                if air > 0:
                    prop_parts.append(f"**Airport:** {air}")
                if port > 0:
                    prop_parts.append(f"**Port:** {port}")

                prop_text = " ・ ".join(prop_parts) if prop_parts else "No properties"

                prop_embed.add_field(
                    name=f"{name} ({inc}/day)",
                    value=prop_text,
                    inline=False,
                )

            for ctry_id in active_ctries:
                if ctry_id == 0:
                    continue
                name = CTRY_NAMES.get(ctry_id, f"Country {ctry_id}")
                units = unit_counts.get(ctry_id, {})
                if not units:
                    unit_embed.add_field(name=name, value="—", inline=False)
                else:
                    # Build dot-separated unit list
                    unit_parts = [
                        f"**{UNIT_NAMES.get(uid, f'Unit{uid}')}:** {count}"
                        for uid, count in sorted(units.items())
                    ]
                    unit_embed.add_field(
                        name=name, value=" ・ ".join(unit_parts), inline=False
                    )

        return {"preview": preview_embed, "properties": prop_embed, "units": unit_embed}

    async def generate_map_response(
        self, awbw_id: int
    ) -> tuple[discord.Embed, discord.File, ui.View] | None:
        try:
            map_data = await self.repo.get_map_data(awbw_id)
            is_animated, image_bytes = self.renderer.render_map(map_data)
            ext = "gif" if is_animated else "png"
            filename = f"awbw_{awbw_id}.{ext}"
            file = discord.File(image_bytes, filename=filename)

            embeds = self.build_embeds(awbw_id, map_data, filename)
            view = TabbedMapView(awbw_id, embeds)

            return embeds["preview"], file, view

        except Exception as e:
            logger.error(f"Error generating map {awbw_id}: {e}")
            traceback.print_exc()
            return None

    @app_commands.command(name="map", description="Preview an AWBW map")
    @app_commands.describe(awbw_id="The ID of the AWBW map")
    async def map_preview(self, interaction: discord.Interaction, awbw_id: int):
        await interaction.response.defer()
        result = await self.generate_map_response(awbw_id)
        if result:
            embed, file, view = result
            await interaction.followup.send(embed=embed, file=file, view=view)
        else:
            await interaction.followup.send(
                f"Error loading map ID {awbw_id}. Please check if the ID is valid."
            )

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return
        match = RE_AWL.search(message.content)
        if match:
            map_id = int(match.group("id"))
            async with message.channel.typing():
                result = await self.generate_map_response(map_id)
                if result:
                    embed, file, view = result
                    await message.reply(
                        embed=embed, file=file, view=view, mention_author=False
                    )


async def setup(bot: commands.Bot):
    await bot.add_cog(Maps(bot))
