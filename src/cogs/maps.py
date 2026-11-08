import discord
import aiohttp
from discord import app_commands, ui
from discord.ext import commands, tasks
import re
import traceback
import logging
import time
import asyncio
from contextlib import suppress
from datetime import datetime, timezone
from urllib.parse import quote

from src.core.repository import MapRepository
from src.core.league import LeagueRepository
from src.core.aw2_renderer import AW2Renderer
from src.core.stats import BotStats
from src.utils.awbw_data import CTRY_NAMES
from src.utils.map_helpers import format_k, count_properties, count_units

logger = logging.getLogger(__name__)
MAX_MAP_TILES = 80 * 80
AUTO_PREVIEW_COOLDOWN_SECONDS = 20

RE_AWL = re.compile(
    r"(?i)https?://(?:www\.)?awbw\.amarriner\.com/prevmaps\.php\?(?:[^\s#]*?&)?maps_id=(?P<id>[0-9]+)"
)
RE_GAME = re.compile(
    r"(?i)https?://(?:www\.)?awbw\.amarriner\.com/game\.php\?games_id=(?P<id>[0-9]+)(?:&ndx=(?P<ndx>[0-9]+))?"
)
RE_GAME_REQUEST = re.compile(r"(?i)(?:^|\s)!game\s+(?:<)?" + RE_GAME.pattern[4:])


class TabbedMapView(ui.View):
    def __init__(self, awbw_id: int, embeds: dict):
        super().__init__(timeout=None)
        self.awbw_id = awbw_id
        self.embeds = embeds
        if "tiers" not in embeds:
            self.remove_item(self.tab_tiers)
        if "details" not in embeds:
            self.remove_item(self.tab_details)

    @ui.button(
        label="Preview",
        emoji="🗺️",
        style=discord.ButtonStyle.primary,
        custom_id="map_tab_preview",
        disabled=True,
    )
    async def tab_preview(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.defer()

    @ui.button(
        label="League Info",
        emoji="🏆",
        style=discord.ButtonStyle.secondary,
        custom_id="map_tab_tiers",
    )
    async def tab_tiers(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_message(
            embed=self.embeds["tiers"], ephemeral=True
        )

    @ui.button(
        label="Map Details",
        emoji="ℹ️",
        style=discord.ButtonStyle.secondary,
        custom_id="map_tab_details",
    )
    async def tab_details(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_message(
            embed=self.embeds["details"], ephemeral=True
        )


class PersistentMapView(ui.View):
    """Restore Map Details and League Info buttons after a bot restart."""

    def __init__(self, cog: "Maps"):
        super().__init__(timeout=None)
        self.cog = cog

    @ui.button(
        label="League Info",
        emoji="🏆",
        style=discord.ButtonStyle.secondary,
        custom_id="map_tab_tiers",
    )
    async def tab_tiers(self, interaction: discord.Interaction, button: ui.Button):
        await self._send_embed(interaction, "tiers")

    @ui.button(
        label="Map Details",
        emoji="ℹ️",
        style=discord.ButtonStyle.secondary,
        custom_id="map_tab_details",
    )
    async def tab_details(self, interaction: discord.Interaction, button: ui.Button):
        await self._send_embed(interaction, "details")

    async def _send_embed(self, interaction: discord.Interaction, embed_name: str):
        map_id = self.cog.get_map_id_from_message(interaction.message)
        if map_id is None:
            await interaction.response.send_message(
                "I could not identify the map for this preview.", ephemeral=True
            )
            return

        await interaction.response.defer(ephemeral=True, thinking=True)
        embed = await self.cog.get_map_detail_embed(map_id, embed_name)
        if embed is None:
            await interaction.followup.send(
                "I could not reload this map's details.", ephemeral=True
            )
            return
        await interaction.followup.send(embed=embed, ephemeral=True)


class Maps(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.repo = MapRepository()
        self.league = LeagueRepository(self.repo.client)
        self.renderer = AW2Renderer()
        self._auto_preview_last_seen: dict[tuple[int, int], float] = {}
        self._persistent_view = PersistentMapView(self)

    async def cog_load(self):
        self.bot.add_view(self._persistent_view)
        self.refresh_league.start()

    @tasks.loop(minutes=5)
    async def refresh_league(self):
        # Check periodically; the shared cache only fetches once every six hours.
        await self.league.refresh()

    async def cog_unload(self):
        self.bot.remove_view(self._persistent_view)
        task = self.refresh_league.get_task()
        self.refresh_league.cancel()
        if task is not None:
            with suppress(asyncio.CancelledError):
                await task
        await self.repo.close()

    def build_embeds(
        self,
        awbw_id: int,
        map_data: dict,
        preview_filename: str,
        league_data: dict | None = None,
    ) -> dict:
        author = map_data.get("author", "Unknown")
        author_url = f"https://awbw.amarriner.com/profile.php?username={quote(author)}"
        is_game = map_data.get("source") == "game"
        game_id = map_data.get("game_id")
        map_id = map_data.get("id", awbw_id)
        game_ndx = map_data.get("game_ndx")
        source_url = (
            f"https://awbw.amarriner.com/game.php?games_id={game_id}"
            + (f"&ndx={game_ndx}" if game_ndx is not None else "")
            if is_game
            else f"https://awbw.amarriner.com/prevmaps.php?maps_id={awbw_id}"
        )

        if is_game:
            map_line = f"**Map:** [{map_data.get('map_name', 'Unknown')}](https://awbw.amarriner.com/prevmaps.php?maps_id={map_id})"
        else:
            if author == "[Unknown]":
                author_line = "**Map Author:** [Unknown]"
            else:
                author_line = f"**Map Author:** [{author}]({author_url})"

        if is_game:
            preview_links = f"[Game]({source_url}) ・ [Move Planner](https://awbw.amarriner.com/moveplanner.php?games_id={game_id})"
        else:
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
        analysis = map_data.get("analysis", {})
        first_published = analysis.get("first_published")
        last_modified = analysis.get(
            "last_published", map_data.get("published", "Unknown")[:10]
        )
        active_players = len([i for i in active_ctries if i != 0])
        if is_game:
            game_lines = [map_line]
            if map_data.get("game_players"):
                game_lines.append(
                    "**Player Names:** "
                    + ", ".join(
                        discord.utils.escape_markdown(name)
                        for name in map_data["game_players"]
                    )
                )
            if game_ndx is not None and isinstance(game_ndx, int):
                turn = ((game_ndx) // active_players) + 1
                turn_decimal = (game_ndx) % active_players
                game_lines.append(
                    f"**Day:** {turn}.{turn_decimal} / {map_data.get('current_game_day', '?')}"
                )
            else:
                game_lines.append(f"**Day:** {map_data.get('game_day', '?')}")
            header_desc = "\n".join(game_lines) + "\n"
        else:
            timing = (
                f"**Published:** {first_published} ・ "
                f"**Last Modified:** {last_modified}"
                if first_published
                else f"**Last Modified:** {last_modified}"
            )
            header_desc = f"{author_line} ・ **Players:** {active_players} ・ **Size:** {size_w}x{size_h} ・ {timing}\n"
        if is_game:
            header_desc += preview_links
        else:
            categories = map_data.get("categories")
            category_text = (
                ", ".join(
                    discord.utils.escape_markdown(category) for category in categories
                )
                if categories
                else "None"
                if categories == []
                else "Unavailable"
            )
            header_desc += f"**Categories:** {category_text}\n{preview_links}"
        title = map_data.get("name", f"Game {game_id}" if is_game else f"Map {awbw_id}")

        # Preview embed (AW2 sprites) - primary tab with embedded image
        preview_embed = discord.Embed(
            title=title,
            url=source_url,
            description=header_desc,
        )
        preview_embed.set_image(url=f"attachment://{preview_filename}")

        if not active_ctries:
            prop_embed = discord.Embed(
                title=title,
                url=source_url,
                description=f"{header_desc}\n\nNo properties found on this map.",
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
                f"{header_desc}\n\n━━━ 💰 **Income** ━━━\n"
                f"**Total properties:** {total_props_all}\n"
                f"**Total income:** {format_k(total_income_all * 1000)}/day\n"
                f"**Income per player:** {format_k(funds_per_player * 1000)}/day\n"
                f"**Income per base:** {format_k(funds_per_base * 1000)}/day"
            )

            prop_embed = discord.Embed(
                title=title,
                url=source_url,
                description=stats_desc,
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
                    name=f"🏠 {name} — {inc}/day",
                    value=prop_text,
                    inline=False,
                )

        fetched_at = map_data.get("fetched_at")
        if fetched_at is not None:
            for embed in (preview_embed, prop_embed):
                embed.set_footer(text="Map data last fetched")
                embed.timestamp = datetime.fromtimestamp(fetched_at, timezone.utc)

        embeds = {"preview": preview_embed}
        if league_data:
            modes = {"std": "Standard", "fog": "Fog", "hf": "High Funds"}
            sections = []
            for setup in league_data["setups"]:
                lines = [f"**{modes[setup['mode']]} GL**"]
                for tier in setup["tiers"]:
                    tier_name = discord.utils.escape_markdown(tier["name"])
                    names = (
                        ", ".join(
                            discord.utils.escape_markdown(name) for name in tier["cos"]
                        )
                        or "None"
                    )
                    lines.append(f"**{tier_name}:** {names}")
                if not setup["tiers"]:
                    lines.append("No enabled tiers.")
                bans = (
                    ", ".join(
                        discord.utils.escape_markdown(ban) for ban in setup["unit_bans"]
                    )
                    or "None"
                )
                lines.extend(
                    [
                        "",
                        f"**Unit bans:** {bans}",
                        f"**Unit limit:** {setup['unit_limit']}",
                        f"**Capture limit:** {setup['cap_limit']}",
                    ]
                )
                sections.append("\n".join(lines))
            sections.append(
                f"[View Global League Settings](https://awbw.amarriner.com/newleaguesetups.php)\n"
                f"*League settings last fetched <t:{int(league_data['fetched_at'])}:R>*"
            )
            embeds["tiers"] = discord.Embed(
                title=title,
                url=source_url,
                description="\n\n".join(sections),
            )
        embeds["details"] = prop_embed
        if analysis:
            analysis_url = f"https://awbw.amarriner.com/analysis.php?maps_id={map_id}"
            game_fields = (
                ("games", "Games"),
                ("game_days", "Game days"),
                ("avg_game_days", "Average game days"),
                ("real_time_days", "Real-time days"),
                ("avg_rt_days", "Average real-time days"),
                ("official_games", "Official games"),
                ("team_games", "Team games"),
                ("no_cop_games", "No COP games"),
            )
            game_lines = [
                f"**{label}:** {analysis[key]}"
                for key, label in game_fields
                if key in analysis
            ]
            prop_embed.add_field(
                name="━━━ 📊 Game Data ━━━",
                value="\n".join(game_lines),
                inline=False,
            )
            map_stat_lines = [
                f"**{label}:** {analysis[key]}"
                for key, label in (
                    ("rating", "Rating"),
                    ("comments", "Comments"),
                    ("favorites", "Favorites"),
                )
                if key in analysis
            ]
            if map_stat_lines:
                prop_embed.add_field(
                    name="━━━ 📌 Map Stats ━━━",
                    value="\n".join(map_stat_lines),
                    inline=False,
                )
            countries = analysis.get("countries", [])
            if countries:
                country_lines = [
                    f"**{row['country']}:** {row['wins']} wins ({row['win_pct']})"
                    for row in countries
                ]
                prop_embed.add_field(
                    name="━━━ 🏳️ Country Data ━━━",
                    value="\n".join(country_lines),
                    inline=False,
                )
            cos = analysis.get("cos", [])
            if cos:
                co_lines = [
                    f"**{row['name']}:** {row['chosen']} picks ({row['chosen_pct']}) ・ {row['record']} ・ {row['win_pct']} win"
                    for row in cos[:8]
                ]
                prop_embed.add_field(
                    name="━━━ ⭐ Most-Picked COs ━━━",
                    value="\n".join(co_lines),
                    inline=False,
                )
            prop_embed.add_field(
                name="\u200b",
                value=f"[View Full AWBW Analysis]({analysis_url})",
                inline=False,
            )
        return embeds

    def get_map_id_from_message(self, message: discord.Message | None) -> int | None:
        if message is None:
            return None
        for embed in message.embeds:
            match = re.search(r"[?&]maps_id=(\d+)", embed.url or "")
            if match:
                return int(match.group(1))
        return None

    async def get_map_detail_embed(
        self, map_id: int, embed_name: str
    ) -> discord.Embed | None:
        try:
            map_data = await self.repo.get_map_data(map_id)
            league_data = (
                await self.league.get_map_setups(map_id)
                if embed_name == "tiers"
                else None
            )
            if embed_name == "details":
                try:
                    map_data["analysis"] = await self.repo.get_map_analysis(map_id)
                except aiohttp.ClientError, asyncio.TimeoutError, ConnectionError:
                    logger.warning("Could not fetch analysis for map %s", map_id)
            embeds = self.build_embeds(
                map_id, map_data, f"awbw_{map_id}.webp", league_data
            )
            return embeds.get(embed_name)
        except Exception:
            logger.exception("Could not rebuild %s for map %s", embed_name, map_id)
            return None

    async def generate_map_response(
        self, awbw_id: int
    ) -> tuple[discord.Embed, list[discord.File], ui.View] | None:
        try:
            map_data = await self.repo.get_map_data(awbw_id)
            width = int(map_data.get("size_w", 0))
            height = int(map_data.get("size_h", 0))
            if width <= 0 or height <= 0:
                raise ValueError(f"Invalid map size {width}x{height}")
            if width * height > MAX_MAP_TILES:
                raise ValueError(f"Map {awbw_id} too large to render: {width}x{height}")

            # Generate AW2 preview image
            _, preview_bytes = self.renderer.render_map(map_data)

            # Create filename
            preview_filename = f"awbw_{awbw_id}.webp"

            # Create file object
            preview_file = discord.File(preview_bytes, filename=preview_filename)

            files = [preview_file]

            league_data = await self.league.get_map_setups(awbw_id)
            try:
                map_data["analysis"] = await self.repo.get_map_analysis(awbw_id)
            except aiohttp.ClientError, asyncio.TimeoutError, ConnectionError:
                logger.warning("Could not fetch analysis for map %s", awbw_id)
            embeds = self.build_embeds(awbw_id, map_data, preview_filename, league_data)
            view = TabbedMapView(awbw_id, embeds)

            return embeds["preview"], files, view

        except Exception as e:
            logger.error(f"Error generating map {awbw_id}: {e}")
            traceback.print_exc()
            return None

    async def generate_game_response(
        self, game_id: int, ndx: int | None = None
    ) -> tuple[discord.Embed, list[discord.File], ui.View] | None:
        start_time = time.time()
        try:
            map_data = await self.repo.get_game_data(game_id, ndx)
            width = int(map_data.get("size_w", 0))
            height = int(map_data.get("size_h", 0))
            if width <= 0 or height <= 0:
                raise ValueError(f"Invalid game map size {width}x{height}")
            if width * height > MAX_MAP_TILES:
                raise ValueError(
                    f"Game {game_id} too large to render: {width}x{height}"
                )

            _, preview_bytes = self.renderer.render_map(map_data)
            preview_filename = f"awbw_game_{game_id}.webp"
            preview_file = discord.File(preview_bytes, filename=preview_filename)

            embeds = self.build_embeds(game_id, map_data, preview_filename)
            embeds.pop("tiers", None)
            embeds.pop("details", None)
            view = TabbedMapView(game_id, embeds)

            return embeds["preview"], [preview_file], view

        except Exception as e:
            logger.error(f"Error generating game {game_id}: {e}")
            traceback.print_exc()
            return None
        finally:
            BotStats().record_game_generation(time.time() - start_time, game_id)

    @app_commands.command(name="map", description="Preview an AWBW map")
    @app_commands.describe(awbw_id="The ID of the AWBW map")
    async def map_preview(self, interaction: discord.Interaction, awbw_id: int):
        await interaction.response.defer()
        result = await self.generate_map_response(awbw_id)
        if result:
            embed, files, view = result
            await interaction.followup.send(embed=embed, files=files, view=view)
        else:
            await interaction.followup.send(
                f"Error loading map ID {awbw_id}. Please check if the ID is valid."
            )

    @app_commands.command(name="game", description="Preview an AWBW game")
    @app_commands.describe(game="The AWBW game URL or ID")
    async def game_preview(self, interaction: discord.Interaction, game: str):
        await interaction.response.defer()
        game_reference = RE_GAME.search(game)
        if game_reference:
            game_id = int(game_reference.group("id"))
            ndx_text = game_reference.group("ndx")
            ndx = int(ndx_text) if ndx_text else None
        elif game.isdigit():
            game_id, ndx = int(game), None
        else:
            await interaction.followup.send("Please provide an AWBW game URL or ID.")
            return
        result = await self.generate_game_response(game_id, ndx)
        if result:
            embed, files, view = result
            await interaction.followup.send(embed=embed, files=files, view=view)
        else:
            await interaction.followup.send(
                f"Error loading game ID {game_id}. Please check the ID and replay index."
            )

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return
        game_match = RE_GAME_REQUEST.search(message.content)
        if game_match:
            now = time.monotonic()
            channel_id = getattr(message.channel, "id", 0)
            key = (channel_id, message.author.id)
            if (
                now - self._auto_preview_last_seen.get(key, 0)
                < AUTO_PREVIEW_COOLDOWN_SECONDS
            ):
                return
            self._auto_preview_last_seen[key] = now
            async with message.channel.typing():
                ndx_text = game_match.group("ndx")
                result = await self.generate_game_response(
                    int(game_match.group("id")), int(ndx_text) if ndx_text else None
                )
                if result:
                    embed, files, view = result
                    await message.reply(
                        embed=embed, files=files, view=view, mention_author=False
                    )
            return
        match = RE_AWL.search(message.content)
        if match:
            logger.info("Detected map link in message %s", message.id)
            now = time.monotonic()
            channel_id = getattr(message.channel, "id", 0)
            key = (channel_id, message.author.id)
            last_seen = self._auto_preview_last_seen.get(key, 0)
            if now - last_seen < AUTO_PREVIEW_COOLDOWN_SECONDS:
                return
            self._auto_preview_last_seen[key] = now
            preview_id = int(match.group("id"))
            async with message.channel.typing():
                result = await self.generate_map_response(preview_id)
                if result:
                    embed, files, view = result
                    await message.reply(
                        embed=embed, files=files, view=view, mention_author=False
                    )


async def setup(bot: commands.Bot):
    await bot.add_cog(Maps(bot))
