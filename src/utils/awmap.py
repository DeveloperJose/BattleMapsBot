from __future__ import annotations

from csv import reader
from io import BytesIO
from math import cos, sin, pi, trunc

from PIL.Image import Resampling, Image, new
from PIL.ImageDraw import Draw
from typing import Dict, Generator, List, Optional, Set, Tuple, Union, Any

from src.core.awbw import AWBWClient
from .tools import bytespop
from src.utils.data.element_id import (
    MAIN_TERR,
    MAIN_UNIT,
    MAIN_CTRY,
    MAIN_TERR_CAT,
    AWBW_TERR,
    AWBW_UNIT_CODE,
    AWBW_COUNTRY_CODE,
    AWBW_AWARENESS,
    AWS_TERR,
    AWS_UNIT,
    main_terr_to_awbw,
    main_terr_to_aws,
    main_unit_to_aws,
)
from src.core.data import (
    BITMAP_SPEC,
    STATIC_ID_TO_SPEC,
    ANIM_ID_TO_SPEC,
    UNIT_ID_TO_SPEC,
    PALETTE,
)


class AWMap:
    def __init__(self) -> None:

        self.raw_data: bytearray = bytearray()

        self.map: Dict = dict()

        self.size_w: int = 0
        self.size_h: int = 0

        self.style = 0

        self.title: str = ""
        self.author: str = ""
        self.desc: str = ""

        self.pass_buffer: list = list()

        self.awbw_id: str = ""
        self.override_awareness: bool = True

        self.nyv: bool = False

        self.countries: list = list()

        self.custom_countries: list = list()
        self.country_conversion: dict = dict()

    def __repr__(self) -> str:
        return (
            f"<{self.__class__.__name__}:Title='{self.title}' Author='{self.author}>'"
        )

    def __str__(self) -> str:
        ret = ""
        if self.title:
            ret += f"Map Title: {self.title}"
        if self.author:
            ret += f"\nMap Author: {self.author}"
        if self.desc:
            ret += f"\nMap Description: {self.desc}"
        return ret

    def __iter__(self) -> Generator[AWTile, None, None]:
        for y in range(self.size_h):
            for x in range(self.size_w):
                yield self.tile(x, y)

    def from_aws(self, data: Union[bytes, bytearray]) -> AWMap:
        self.raw_data = bytearray(data)

        self.size_w, self.size_h, self.style = self.raw_data[10:13]

        terr_data = [
            int.from_bytes(self.raw_data[x + 13 : x + 15], "little")
            for x in range(0, self.map_size * 2, 2)
        ]

        unit_data = [
            int.from_bytes(
                self.raw_data[
                    x + (self.map_size * 2) + 13 : x + (self.map_size * 2) + 15
                ],
                "little",
            )
            for x in range(0, self.map_size * 2, 2)
        ]

        map_data = {
            x: {
                y: AWTile(
                    self,
                    x,
                    y,
                    **self._terr_from_aws(x, y, terr_data),
                    **self._unit_from_aws(x, y, unit_data),
                )
                for y in range(self.size_h)
            }
            for x in range(self.size_w)
        }

        self.map = {
            y: {x: map_data[x][y] for x in range(self.size_w)}
            for y in range(self.size_h)
        }

        metadata = self.raw_data[13 + (self.map_size * 4) :]

        t_size_raw, metadata = bytespop(metadata, 4, "int")
        t_size = int(t_size_raw)  # Ensure t_size is an integer
        title_raw, metadata = bytespop(metadata, t_size, "utf8")
        self.title = str(title_raw)  # Ensure title is a string

        a_size_raw, metadata = bytespop(metadata, 4, "int")
        a_size = int(a_size_raw)  # Ensure a_size is an integer
        author_raw, metadata = bytespop(metadata, a_size, "utf8")
        self.author = str(author_raw)  # Ensure author is a string

        self.desc = metadata[4:].decode("utf8")

        return self

    async def from_awbw(
        self, data: str = "", title: str = "", awbw_id: Optional[int] = None
    ) -> Union[AWMap, None]:
        if awbw_id:
            awbw_client = AWBWClient()
            try:
                awbw_map = await awbw_client.get_map(map_id=awbw_id)
                self.load_from_data(awbw_map)
            finally:
                await awbw_client.close()
            return self

        elif data:
            csv_map = [*reader(data.strip("\n").split("\n"))]
            # Assuming 'data' here is raw CSV string, not a full AWBW map JSON
            # _parse_awbw_csv expects List[List[int]], so this needs careful handling if 'data' is not already parsed to int
            # For now, keeping the original _parse_awbw_csv call.
            csv_map_int = [[int(cell) for cell in row] for row in csv_map]
            self._parse_awbw_csv(csvdata=csv_map_int)

            self.title = title if title else "[Untitled]"

            return self

        return

    def load_from_data(self, map_data: Dict[str, Any]) -> AWMap:
        self.title = map_data.get("name", "[Untitled]")
        self.author = map_data.get("author", "Unknown")
        self.awbw_id = str(map_data.get("id", ""))
        self.desc = f"https://awbw.amarriner.com/prevmaps.php?maps_id={self.awbw_id}"

        if "terr" in map_data:
            self._parse_awbw_csv(csvdata=map_data["terr"])

        if "unit" in map_data:
            for unit in map_data["unit"]:
                u_id = unit.get("id")
                if u_id is None:
                    u_id = unit.get("Unit ID")

                u_x = unit.get("x")
                if u_x is None:
                    u_x = unit.get("Unit X")

                u_y = unit.get("y")
                if u_y is None:
                    u_y = unit.get("Unit Y")

                u_ctry = unit.get("ctry")
                if u_ctry is None:
                    u_ctry = unit.get("Country Code")

                main_id = AWBW_UNIT_CODE.get(int(u_id) if u_id is not None else 0)
                main_ctry = AWBW_COUNTRY_CODE.get(u_ctry)

                if (
                    main_id
                    and main_ctry is not None
                    and u_x is not None
                    and u_y is not None
                ):
                    self.tile(int(u_x), int(u_y)).mod_unit(main_id, main_ctry)

        return self

    def _parse_awbw_csv(self, csvdata: List[List[int]]) -> None:
        assert all(map(lambda r: len(r) == len(csvdata[0]), csvdata))

        self.size_h, self.size_w = len(csvdata), len(csvdata[0])

        for y in range(self.size_h):
            self.map[y] = dict()
            for x in range(self.size_w):
                self.map[y][x] = AWTile(
                    self, x, y, **self.terr_from_awbw(csvdata[y][x])
                )

    def _terr_from_aws(self, x: int, y: int, data: List[int]) -> Dict[str, int]:
        offset = y + (x * self.size_h)
        terr, t_ctry = AWS_TERR.get(data[offset], (0, 0))
        return {"terr": terr, "t_ctry": t_ctry}

    def _unit_from_aws(self, x: int, y: int, data: List[int]) -> Dict[str, int]:
        offset = y + (x * self.size_h)

        unit, u_ctry = AWS_UNIT.get(data[offset], (0, 0))
        return {"unit": unit, "u_ctry": u_ctry}

    @staticmethod
    def terr_from_awbw(terr: int) -> Dict[str, int]:
        if terr == 195:
            main_id, main_ctry = 999, 0
        else:
            terr = int(terr)
            main_id, main_ctry = AWBW_TERR.get(terr, (1, 0))
        if main_id in AWBW_AWARENESS["aware_of"].keys():
            offset = terr - int(main_terr_to_awbw(main_id, main_ctry)[0])
            _awareness = AWBW_AWARENESS[main_id]
            override = next(
                (k for k, v in _awareness.items() if v == offset),
                0,  # Default or error value if not found, adjust if different behavior is needed
            )

            return {
                "terr": main_id,
                "t_ctry": main_ctry,
                "awareness_override": override,
            }
        else:
            return {
                "terr": main_id,
                "t_ctry": main_ctry,
            }

    def tile(self, x: int, y: int) -> AWTile:
        try:
            tile = self.map[y][x]
            try:
                assert tile.x == x
                assert tile.y == y
                return tile
            except AssertionError:
                print(
                    f"Received tile from index with differing coordinates\n"
                    f"Requested:     ({x}, {y})\n"
                    f"Tile Property: ({tile.x}, {tile.y})\n"
                    f"Tile Contents: (T: {tile.terr}, U: {tile.unit})"
                )
                return tile
        except KeyError:
            return AWTile(self, x, y, 999, 0)

    @property
    def map_size(self) -> int:
        return self.size_h * self.size_w

    @property
    def playable_countries(self) -> Set[int]:
        countries = {
            i: {"has_hq": False, "has_units": False, "has_prod": False}
            for i in range(1, 17)
        }

        playable = set()

        for i in countries.keys():
            props = self.owned_props(i)
            units = self.deployed_units(i)

            for tile in props:
                if tile is not None and tile.is_hq:
                    countries[i]["has_hq"] = True
                elif tile is not None and tile.is_prod:
                    countries[i]["has_prod"] = True

            for tile in units:
                if tile is not None and tile.unit:
                    countries[i]["has_units"] = True

            if countries[i]["has_hq"] and (
                countries[i]["has_units"] or countries[i]["has_prod"]
            ):
                playable.add(i)

        return playable

    def owned_props(self, t_ctry: int) -> List[Optional[AWTile]]:
        tiles = list()

        for tile in self:
            if tile.t_ctry == t_ctry:
                tiles.append(tile)

        return tiles

    def deployed_units(self, u_ctry: int) -> List[Optional[AWTile]]:
        tiles = list()

        for tile in self:
            if tile.u_ctry == u_ctry:
                tiles.append(tile)

        return tiles

    def mod_terr(self, x: int, y: int, terr: int, t_ctry: int) -> None:
        self.tile(x, y).mod_terr(terr, t_ctry)

    def mod_unit(self, x: int, y: int, unit: int, u_ctry: int) -> None:
        self.tile(x, y).mod_terr(unit, u_ctry)

    @property
    def to_awbw(self) -> str:
        csvdata = "\n".join(
            [
                ",".join([str(self.tile(x, y).awbw_id) for x in range(self.size_w)])
                for y in range(self.size_h)
            ]
        )
        return csvdata

    @property
    def to_aws(self) -> bytearray:
        ret = bytearray(b"AWSMap001") + b"\x00"

        style = self.style if self.style else 5

        for b in [m.to_bytes(1, "little") for m in [self.size_w, self.size_h, style]]:
            ret += b

        terr_data = [
            terr.to_bytes(2, "little")
            for terr in [
                self.tile(x, y).aws_terr_id
                for x in range(self.size_w)
                for y in range(self.size_h)
            ]
        ]

        for t in terr_data:
            ret += t

        unit_data = [
            unit.to_bytes(2, "little")
            for unit in [
                self.tile(x, y).aws_unit_id
                for x in range(self.size_w)
                for y in range(self.size_h)
            ]
        ]

        for u in unit_data:
            ret += u

        ret += len(self.title).to_bytes(4, "little") + self.title.encode("utf-8")
        ret += len(self.author).to_bytes(4, "little") + self.author.encode("utf-8")
        ret += len(self.desc).to_bytes(4, "little") + self.desc.encode("utf-8")

        return ret

    @property
    def minimap(self) -> BytesIO:
        return AWMinimap(self).map


class AWTile:
    def __init__(
        self,
        awmap: AWMap,
        x: int = 0,
        y: int = 0,
        terr: int = 0,
        t_ctry: int = 0,
        unit: int = 0,
        u_ctry: int = 0,
        awareness_override: int = 0,
    ):
        self.x = x
        self.y = y
        self.terr = terr
        self.t_ctry = t_ctry
        self.unit = unit
        self.u_ctry = u_ctry
        self.awmap = awmap
        self.awareness_override = awareness_override

    def __repr__(self) -> str:
        return (
            f"({self.x + 1}, {self.y + 1}): "
            f"<{self.terr}:{MAIN_TERR.get(self.terr, 'Plain')}>"
            f"<{self.unit}:{MAIN_UNIT.get(self.unit, 'Empty')}>"
        )

    def __str__(self) -> str:
        return self.__repr__()

    def tile(self, x: int, y: int):
        return self.awmap.tile(x, y)

    @property
    def terr_name(self) -> str:
        return MAIN_TERR.get(self.terr, "InvalidTerrID")

    @property
    def is_hq(self) -> bool:
        return self.terr in (101, 107)

    @property
    def is_prop(self) -> bool:
        return self.terr in MAIN_TERR_CAT["properties"]

    @property
    def is_prod(self) -> bool:
        return self.terr in (103, 104, 105)

    @property
    def aws_terr_id(self) -> int:
        return main_terr_to_aws(self.terr, self.t_ctry)[0]

    @property
    def aws_unit_id(self) -> int:
        return main_unit_to_aws(self.unit, self.u_ctry)[0]

    @property
    def awbw_id(self) -> int:
        terr_list = main_terr_to_awbw(self.terr, self.t_ctry)
        if self.terr in AWBW_AWARENESS.get("aware_of", {}).keys():
            return int(terr_list[self.awbw_awareness])
        else:
            return int(terr_list[0])

    @property
    def awbw_awareness(self) -> int:
        if self.terr in AWBW_AWARENESS:
            # Explicitly cast to the expected dictionary type for direct awareness
            awareness_map: Dict[int, int] = AWBW_AWARENESS[self.terr]  # type: ignore
            if self.awmap.override_awareness and isinstance(
                self.awareness_override, int
            ):
                return awareness_map.get(self.awareness_override, 0)
            else:
                mask = 0
                # Explicitly cast to the expected list type for adjacent awareness
                if self.terr in AWBW_AWARENESS.get("aware_of", {}):
                    adjacent_terrs_to_check: List[int] = AWBW_AWARENESS["aware_of"][
                        self.terr
                    ]  # type: ignore
                    for adjacent_terr_id in adjacent_terrs_to_check:
                        mask |= self.adj_match(adjacent_terr_id)
                return awareness_map.get(mask, 0)

        return 0

    def adj_match(self, terr: Optional[int] = None) -> int:
        if not terr:
            terr = self.terr

        awareness_mask = 0
        for i in range(4):
            adj = self.tile(
                self.x - trunc(sin(pi * (i + 1) / 2)),
                self.y - trunc(cos(pi * (i + 1) / 2)),
            )
            if adj.terr == terr:
                awareness_mask += 2**i

        return awareness_mask

    def mod_terr(self, terr: int, t_ctry: int = 0) -> None:
        try:
            assert terr in MAIN_TERR.keys()
            assert t_ctry in MAIN_CTRY.keys()
            if terr not in MAIN_TERR_CAT["properties"]:
                assert t_ctry == 0
        except AssertionError:
            raise ValueError("Invalid Terrain Data")
        else:
            self.terr, self.t_ctry = terr, t_ctry

    def mod_unit(self, unit: int, u_ctry: int) -> None:
        if unit in MAIN_UNIT.keys() and u_ctry in MAIN_CTRY.keys():
            self.unit, self.u_ctry = unit, u_ctry
        else:
            raise ValueError("Invalid Unit Data")


class AWMinimap:
    def __init__(self, awmap: AWMap):
        self.im = new("RGBA", (4 * awmap.size_w, 4 * awmap.size_h))
        self.ims = list()
        self.animated = False
        self.anim_buffer = list()
        self.final_im: BytesIO = BytesIO()

        # Add all terrain sprites (buffer animated sprites)
        for x in range(awmap.size_w):
            for y in range(awmap.size_h):
                terr = awmap.tile(x, y).terr + (awmap.tile(x, y).t_ctry * 10)
                sprite, animated = AWMinimap.get_sprite(terr)
                if animated:
                    self.anim_buffer.append((x, y, sprite))
                    self.animated = True
                    continue
                if isinstance(sprite, Image):
                    self.im.paste(sprite, (x * 4, y * 4))

        # Add all unit sprites to buffer
        for x in range(awmap.size_w):
            for y in range(awmap.size_h):
                unit = awmap.tile(x, y).unit + (awmap.tile(x, y).u_ctry * 100)
                if unit:
                    sprite, _ = AWMinimap.get_sprite(unit, True)
                    self.animated = True
                    self.anim_buffer.append((x, y, sprite))

        # Copy map to 8 frames, then add the animated sprites
        if self.animated:
            self.ims = []
            for _ in range(8):
                self.ims.append(self.im.copy())
            for x, y, sprite_frames in self.anim_buffer:
                if isinstance(sprite_frames, list):
                    for i in range(8):
                        self.ims[i].paste(
                            sprite_frames[i],
                            (x * 4, y * 4, (x * 4) + 4, (y * 4) + 4),
                            sprite_frames[i],
                        )

        # Smaller maps can be sized up
        if awmap.size_w * awmap.size_h <= 1600:
            if self.animated:
                for i, f in enumerate(self.ims):
                    self.ims[i] = f.resize(
                        (awmap.size_w * 16, awmap.size_h * 16),
                        resample=Resampling.NEAREST,
                    )
            else:
                self.im = self.im.resize(
                    (awmap.size_w * 16, awmap.size_h * 16), resample=Resampling.NEAREST
                )
        elif awmap.size_w * awmap.size_h <= 3200:
            if self.animated:
                for i, f in enumerate(self.ims):
                    self.ims[i] = f.resize(
                        (awmap.size_w * 8, awmap.size_h * 8),
                        resample=Resampling.NEAREST,
                    )
            else:
                self.im = self.im.resize(
                    (awmap.size_w * 8, awmap.size_h * 8), resample=Resampling.NEAREST
                )

        if self.animated:
            self.final_im = AWMinimap.compile_gif(self.ims)
        else:
            img = BytesIO()
            self.im.save(
                fp=img,
                format="PNG",
            )
            img.seek(0)
            self.final_im = img

    @staticmethod
    def _parse_pixel_map(pixel_string: str) -> List[Tuple[int, int]]:
        """Parses a pixel map string into a list of points."""
        points = []
        lines = [line.strip() for line in pixel_string.strip().split("\n")]
        for y, line in enumerate(lines):
            for x, char in enumerate(line):
                if char == "1":
                    points.append((x, y))
        return points

    @staticmethod
    def get_sprite(
        sprite_id: int, unit: bool = False
    ) -> Union[Tuple[Image, bool], Tuple[List[Image], bool]]:
        if unit:
            if sprite_id in [i for v in UNIT_ID_TO_SPEC.values() for i in v]:
                sprite_name = [k for k, v in UNIT_ID_TO_SPEC.items() if sprite_id in v][
                    0
                ]
                return AWMinimap.get_unit_sprite(sprite_name)
            else:
                return new("RGBA", (4, 4)), False
        else:
            if sprite_id in [i for v in STATIC_ID_TO_SPEC.values() for i in v]:
                sprite_name = [
                    k for k, v in STATIC_ID_TO_SPEC.items() if sprite_id in v
                ][0]
                return AWMinimap.get_static_sprite(sprite_name)
            elif sprite_id in [i for v in ANIM_ID_TO_SPEC.values() for i in v]:
                sprite_name = [k for k, v in ANIM_ID_TO_SPEC.items() if sprite_id in v][
                    0
                ]
                return AWMinimap.get_anim_sprite(sprite_name)
            else:
                return new("RGBA", (4, 4)), False

    @staticmethod
    def get_static_sprite(sprite_name: str) -> Tuple[Image, bool]:
        im = new("RGBA", (4, 4))
        draw = Draw(im, "RGBA")
        spec = BITMAP_SPEC[sprite_name]
        for color_name, pixel_string in spec:
            points = AWMinimap._parse_pixel_map(pixel_string)
            color = PALETTE[color_name]
            if isinstance(color, list):
                color = color[0]
            draw.point(points, fill=color)
        return im, False

    @staticmethod
    def get_anim_sprite(sprite_name: str) -> Tuple[List[Image], bool]:
        ims = []
        for i in range(8):
            im = new("RGBA", (4, 4))
            draw = Draw(im, "RGBA")
            spec = BITMAP_SPEC[sprite_name]
            for color_name, pixel_string in spec:
                points = AWMinimap._parse_pixel_map(pixel_string)
                color = PALETTE[color_name]
                if isinstance(color, list):
                    draw.point(points, fill=color[i % len(color)])
                else:
                    draw.point(points, fill=color)
            ims.append(im)
        return ims, True

    @staticmethod
    def get_unit_sprite(sprite_name: str) -> Tuple[List[Image], bool]:
        ims = []
        for i in range(8):
            im = new("RGBA", (4, 4))
            if 1 < i < 6:
                draw = Draw(im, "RGBA")
                spec = BITMAP_SPEC[sprite_name]
                for color_name, pixel_string in spec:
                    points = AWMinimap._parse_pixel_map(pixel_string)
                    color = PALETTE[color_name]
                    if isinstance(color, list):
                        draw.point(points, fill=color[i % len(color)])
                    else:
                        draw.point(points, fill=color)
            ims.append(im)
        return ims, True

    @staticmethod
    def compile_gif(frames: List[Image]) -> BytesIO:
        img_bytes = BytesIO()
        if not frames:
            return img_bytes
        first_frame = frames[0]
        other_frames = frames[1:]
        first_frame.save(
            img_bytes,
            format="GIF",
            save_all=True,
            append_images=other_frames,
            loop=0,
            duration=150,
            optimize=False,
        )
        img_bytes.seek(0)
        return img_bytes

    @property
    def map(self) -> BytesIO:
        return self.final_im
