from __future__ import annotations

from csv import reader
from io import BytesIO
from math import cos, sin, pi, trunc

from PIL.Image import Resampling, Image, new
from PIL.ImageDraw import Draw
from typing import Dict, Generator, List, Optional, Set, Tuple, Union, Any

from .awbw_api import get_map
from .tools import bytespop
from .data import (
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

    BITMAP_SPEC,
    STATIC_ID_TO_SPEC,
    ANIM_ID_TO_SPEC,
    UNIT_ID_TO_SPEC
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
        return f"<{self.__class__.__name__}:" \
               f"Title='{self.title}' Author='{self.author}>'"

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
            int.from_bytes(
                self.raw_data[x + 13:x + 15],
                'little'
            ) for x in range(0, self.map_size * 2, 2)
        ]

        unit_data = [
            int.from_bytes(
                self.raw_data[x + (self.map_size*2) + 13:x + (self.map_size*2) + 15],
                'little'
            ) for x in range(0, self.map_size * 2, 2)
        ]

        map_data = {
            x: {
                y: AWTile(
                    self, x, y,
                    **self._terr_from_aws(x, y, terr_data),
                    **self._unit_from_aws(x, y, unit_data),
                ) for y in range(self.size_h)
            } for x in range(self.size_w)
        }

        self.map = {
            y: {
                x: map_data[x][y]
                for x in range(self.size_w)
            } for y in range(self.size_h)
        }

        metadata = self.raw_data[13 + (self.map_size * 4):]

        t_size, metadata = bytespop(metadata, 4, "int")
        self.title, metadata = bytespop(metadata, t_size, "utf8")

        a_size, metadata = bytespop(metadata, 4, "int")
        self.author, metadata = bytespop(metadata, a_size, "utf8")

        self.desc = metadata[4:].decode("utf8")

        return self

    async def from_awbw(
            self,
            data: str = "",
            title: str = "",
            awbw_id: int = None,
            verify: bool = True
    ) -> Union[AWMap, None]:
        if awbw_id:
            awbw_map = await get_map(maps_id=awbw_id, verify=verify)
            self._parse_awbw_csv(csvdata=awbw_map["terr"])

            if awbw_map["unit"]:
                for unit in awbw_map["unit"]:
                    main_id = AWBW_UNIT_CODE.get(unit["id"])
                    main_ctry = AWBW_COUNTRY_CODE.get(unit["ctry"])
                    self.tile(unit["x"], unit["y"]).mod_unit(main_id, main_ctry)

            self.author = awbw_map["author"]
            self.title = awbw_map["name"]
            self.awbw_id = str(awbw_id)
            self.desc = f"https://awbw.amarriner.com/prevmaps.php?maps_id={awbw_id}"

            return self

        elif data:
            csv_map = [*reader(data.strip('\n').split('\n'))]
            self._parse_awbw_csv(csvdata=csv_map)

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
                
                if main_id and main_ctry is not None and u_x is not None and u_y is not None:
                     self.tile(int(u_x), int(u_y)).mod_unit(main_id, main_ctry)
        
        return self

    def _parse_awbw_csv(self, csvdata: List[List[int]]) -> None:
        assert all(map(lambda r: len(r) == len(csvdata[0]), csvdata))

        self.size_h, self.size_w = len(csvdata), len(csvdata[0])

        for y in range(self.size_h):
            self.map[y] = dict()
            for x in range(self.size_w):
                self.map[y][x] = AWTile(self, x, y, **self.terr_from_awbw(csvdata[y][x]))

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
            offset = terr - main_terr_to_awbw(main_id, main_ctry)[0]
            _awareness = AWBW_AWARENESS[main_id]
            override = list(_awareness.keys())[
                list(_awareness.values()).index(offset)
            ]  # TODO: Reeeefaaaactoooor

            return {
                "terr": main_id,
                "t_ctry": main_ctry,
                "awareness_override": override
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
                print(f"Received tile from index with differing coordinates\n"
                      f"Requested:     ({x}, {y})\n"
                      f"Tile Property: ({tile.x}, {tile.y})\n"
                      f"Tile Contents: (T: {tile.terr}, U: {tile.unit})")
                return tile
        except KeyError:
            return AWTile(self, x, y, 999, 0)

    @property
    def map_size(self) -> int:
        return self.size_h * self.size_w

    @property
    def playable_countries(self) -> Set[int]:
        countries = {
            i: {
                "has_hq": False,
                "has_units": False,
                "has_prod": False
            } for i in range(1, 17)
        }

        playable = set()

        for i in countries.keys():
            props = self.owned_props(i)
            units = self.deployed_units(i)

            for tile in props:
                if tile.is_hq:
                    countries[i]["has_hq"] = True
                elif tile.is_prod:
                    countries[i]["has_prod"] = True

            for tile in units:
                if tile.unit:
                    countries[i]["has_units"] = True

            if countries[i]["has_hq"] and (countries[i]["has_units"] or countries[i]["has_prod"]):
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
        csvdata = '\n'.join(
            [','.join(
                [
                    str(self.tile(x, y).awbw_id)
                    for x in range(self.size_w)
                ]
            ) for y in range(self.size_h)]
        )
        return csvdata

    @property
    def to_aws(self) -> bytearray:
        ret = bytearray(b'AWSMap001') + b'\x00'

        style = self.style if self.style else 5

        for b in [m.to_bytes(1, 'little') for m in [self.size_w, self.size_h, style]]:
            ret += b

        terr_data = [
            terr.to_bytes(2, 'little')
            for terr in [
                self.tile(x, y).aws_terr_id
                for x in range(self.size_w)
                for y in range(self.size_h)
            ]
        ]

        for t in terr_data:
            ret += t

        unit_data = [
            unit.to_bytes(2, 'little')
            for unit in [
                self.tile(x, y).aws_unit_id
                for x in range(self.size_w)
                for y in range(self.size_h)
            ]
        ]

        for u in unit_data:
            ret += u

        ret += len(self.title).to_bytes(4, 'little') + self.title.encode('utf-8')
        ret += len(self.author).to_bytes(4, 'little') + self.author.encode('utf-8')
        ret += len(self.desc).to_bytes(4, 'little') + self.desc.encode('utf-8')

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
            awareness_override: int = 0
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
        return f"({self.x + 1}, {self.y + 1}): " \
               f"<{self.terr}:{MAIN_TERR.get(self.terr, 'Plain')}>" \
               f"<{self.unit}:{MAIN_UNIT.get(self.unit, 'Empty')}>"

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
        terr = main_terr_to_awbw(self.terr, self.t_ctry)
        if self.terr in AWBW_AWARENESS["aware_of"].keys():
            return terr[self.awbw_awareness]
        else:
            return terr[0]

    @property
    def awbw_awareness(self) -> int:
        if self.terr in AWBW_AWARENESS.keys():
            if self.awmap.override_awareness:
                return AWBW_AWARENESS[self.terr][self.awareness_override]
            else:
                mask = 0
                for tile in AWBW_AWARENESS["aware_of"][self.terr]:
                    mask = mask | self.adj_match(tile)
                return AWBW_AWARENESS[self.terr][mask]
        else:
            return 0

    def adj_match(self, terr=None) -> int:
        if not terr:
            terr = self.terr

        awareness_mask = 0
        for i in range(4):
            adj = self.tile(
                    self.x - trunc(sin(pi * (i + 1)/2)),
                    self.y - trunc(cos(pi * (i + 1)/2))
            )
            if adj.terr == terr:
                awareness_mask += 2 ** i

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
        self.final_im = None

        # Add all terrain sprites (buffer animated sprites)
        for x in range(awmap.size_w):
            for y in range(awmap.size_h):
                terr = awmap.tile(x, y).terr + (awmap.tile(x, y).t_ctry * 10)
                sprite, animated = AWMinimap.get_sprite(terr)
                if animated:
                    self.anim_buffer.append((x, y, sprite))
                    self.animated = True
                    continue
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
            for x, y, sprite in self.anim_buffer:
                for i in range(8):
                    self.ims[i].paste(
                        sprite[i],
                        (x * 4, y * 4, (x * 4) + 4, (y * 4) + 4),
                        sprite[i]
                    )

        # Smaller maps can be sized up
        if awmap.size_w * awmap.size_h <= 1600:
            if self.animated:
                for i, f in enumerate(self.ims):
                    self.ims[i] = f.resize(
                        (awmap.size_w * 16, awmap.size_h * 16),
                        resample=Resampling.NEAREST
                    )
            else:
                self.im = self.im.resize((awmap.size_w * 16, awmap.size_h * 16), resample=Resampling.NEAREST)
        elif awmap.size_w * awmap.size_h <= 3200:
            if self.animated:
                for i, f in enumerate(self.ims):
                    self.ims[i] = f.resize(
                        (awmap.size_w * 8, awmap.size_h * 8),
                        resample=Resampling.NEAREST
                    )
            else:
                self.im = self.im.resize((awmap.size_w * 8, awmap.size_h * 8), resample=Resampling.NEAREST)

        if self.animated:
            self.final_im = AWMinimap.compile_gif(self.ims)
        else:
            img = BytesIO()
            self.im.save(fp=img, format="PNG", )
            img.seek(0)
            self.final_im = img

    @staticmethod
    def get_sprite(
            sprite_id: int,
            unit: bool = False
    ) -> Union[Tuple[Image, bool], Tuple[List[Image], bool]]:
        if unit:
            if sprite_id in [i for v in UNIT_ID_TO_SPEC.values() for i in v]:
                sprite_name = [k for k, v in UNIT_ID_TO_SPEC.items() if sprite_id in v][0]
                return AWMinimap.get_unit_sprite(sprite_name)
            else:
                return new("RGBA", (4, 4)), False
        else:
            if sprite_id in [i for v in STATIC_ID_TO_SPEC.values() for i in v]:
                sprite_name = [
                    k
                    for k, v
                    in STATIC_ID_TO_SPEC.items()
                    if sprite_id in v
                ][0]
                return AWMinimap.get_static_sprite(sprite_name)
            elif sprite_id in [i for v in ANIM_ID_TO_SPEC.values() for i in v]:
                sprite_name = [k for k, v in ANIM_ID_TO_SPEC.items() if sprite_id in v][0]
                return AWMinimap.get_anim_sprite(sprite_name)
            else:
                return new("RGBA", (4, 4)), False

    @staticmethod
    def get_static_sprite(sprite_name: str) -> Tuple[Image, bool]:
        im = new("RGBA", (4, 4))
        draw = Draw(im, "RGBA")
        spec = BITMAP_SPEC[sprite_name]
        for _layer in spec:
            draw.point(**_layer)
        return im, False

    @staticmethod
    def get_anim_sprite(sprite_name: str) -> Tuple[List[Image], bool]:
        ims = []
        for _ in range(8):
            ims.append(new("RGBA", (4, 4)))
        spec = BITMAP_SPEC[sprite_name]
        for frame in range(8):
            draw = Draw(ims[frame], "RGBA")
            for _layer in spec:
                draw.point(xy=_layer["xy"][frame], fill=_layer["fill"][frame])
        return ims, True

    @staticmethod
    def get_unit_sprite(sprite_name: str) -> Tuple[List[Image], bool]:
        ims = []
        for _ in range(8):
            ims.append(new("RGBA", (4, 4)))
        spec = BITMAP_SPEC[sprite_name]
        for i in range(8):
            if 1 < i < 6:
                draw = Draw(ims[i], "RGBA")
                for _layer in spec:
                    draw.point(**_layer)
        return ims, True

    @staticmethod
    def compile_gif(frames: List[Image]) -> BytesIO:
        img_bytes = BytesIO()
        first_frame = frames.pop(0)
        first_frame.save(
            img_bytes,
            format="GIF",
            save_all=True,
            append_images=frames,
            loop=0,
            duration=150,
            optimize=False,
            version='GIF89a'
        )
        img_bytes.seek(0)
        return img_bytes

    @property
    def map(self) -> BytesIO:
        return self.final_im
