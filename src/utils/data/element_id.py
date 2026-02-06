from typing import Dict, List, Tuple, Union

# Internal Terrain IDs with internal names
MAIN_TERR: Dict[int, str] = {
    1:      "Plain",
    2:      "Wood",
    3:      "Mountain",
    4:      "Road",
    5:      "Bridge",
    6:      "Sea",
    7:      "Shoal",
    8:      "Reef",
    9:      "River",
    10:     "Pipe",
    11:     "Seam",
    12:     "BrokenSeam",
    13:     "Silo",
    14:     "SiloEmpty",
    15:     "Ruins",

    101:    "HQ",
    102:    "City",
    103:    "Base",
    104:    "Airport",
    105:    "Seaport",
    106:    "Tower",
    107:    "Lab",

    500:    "Volcano",
    501:    "GiantMissile",
    502:    "Fortress",
    503:    "FlyingFortressLand",
    504:    "FlyingFortressSea",
    505:    "BlackCannonNorth",
    506:    "BlackCannonSouth",
    507:    "MiniCannonNorth",
    508:    "MiniCannonSouth",
    509:    "MiniCannonEast",
    510:    "MiniCannonWest",
    511:    "LaserCannon",
    512:    "Deathray",
    513:    "Crystal",
    514:    "BlackCrystal",

    999:    "NullTile",
}

# Create "Categories" for terrain type for tile awareness
MAIN_TERR_CAT: Dict[str, List[int]] = {
    "land":         [1, 2, 3, 4, 5, 10, 11, 12, 13, 14, 15, 101, 102, 103, 104, 105, 106, 107],
    "sea":          [6, 8],
    "properties":   [101, 102, 103, 104, 105, 106, 107],
}

# Internal Unit IDs with internal names
MAIN_UNIT: Dict[int, str] = {
    0:      "Empty",
    1:      "Infantry",
    2:      "Mech",
    11:     "APC",
    12:     "Recon",
    13:     "Tank",
    14:     "MDTank",
    15:     "Neotank",
    16:     "Megatank",
    17:     "AntiAir",
    21:     "Artillery",
    22:     "Rocket",
    23:     "Missile",
    24:     "PipeRunner",
    25:     "Oozium",
    31:     "TCopter",
    32:     "BCopter",
    33:     "Fighter",
    34:     "Bomber",
    35:     "Stealth",
    36:     "BBomb",
    41:     "BBoat",
    42:     "Lander",
    43:     "Cruiser",
    44:     "Submarine",
    45:     "Battleship",
    46:     "Carrier",
}

# Internal Country IDs in country order
MAIN_CTRY: Dict[int, str] = {
    0:      "Neutral",
    1:      "Orange Star",
    2:      "Blue Moon",
    3:      "Green Earth",
    4:      "Yellow Comet",
    5:      "Black Hole",
    6:      "Red Fire",
    7:      "Grey Sky",
    8:      "Brown Desert",
    9:      "Amber Blaze",
    10:     "Jade Sun",
    11:     "Cobalt Ice",
    12:     "Pink Cosmos",
    13:     "Teal Galaxy",
    14:     "Purple Lightning",
    15:     "Acid Rain",
    16:     "White Nova",
    17:     "Azure Asteroid",
    18:     "Noir Eclipse",
    19:     "Silver Claw",
    20:     "Umber Wilds"
}

# Relate AWBW Terrain IDs (keys) to Internal Terrain, Country ID pairs (values)
AWBW_TERR: Dict[int, Tuple[int, int]] = {
    195:    (999,  0),  # Teleport Tile

    1:      (1,    0),  # Plain
    2:      (3,    0),  # Mountain
    3:      (2,    0),  # Wood
    4:      (9,    0),  # HRiver
    5:      (9,    0),  # VRiver
    6:      (9,    0),  # CRiver
    7:      (9,    0),  # ESRiver
    8:      (9,    0),  # SWRiver
    9:      (9,    0),  # WNRiver
    10:     (9,    0),  # NERiver
    11:     (9,    0),  # ESWRiver
    12:     (9,    0),  # SWNRiver
    13:     (9,    0),  # WNERiver
    14:     (9,    0),  # NESRiver
    15:     (4,    0),  # HRoad
    16:     (4,    0),  # VRoad
    17:     (4,    0),  # CRoad
    18:     (4,    0),  # ESRoad
    19:     (4,    0),  # SWRoad
    20:     (4,    0),  # WNRoad
    21:     (4,    0),  # NERoad
    22:     (4,    0),  # ESWRoad
    23:     (4,    0),  # SWNRoad
    24:     (4,    0),  # WNERoad
    25:     (4,    0),  # NESRoad
    26:     (5,    0),  # HBridge
    27:     (5,    0),  # VBridge
    28:     (6,    0),  # Sea
    29:     (7,    0),  # HShoal
    30:     (7,    0),  # HShoalN
    31:     (7,    0),  # VShoal
    32:     (7,    0),  # VShoalE
    33:     (8,    0),  # Reef

    34:     (102,  0),  # Neutral City
    35:     (103,  0),  # Neutral Base
    36:     (104,  0),  # Neutral Airport
    37:     (105,  0),  # Neutral Port

    38:     (102,  1),  # Orange Star City
    39:     (103,  1),  # Orange Star Base
    40:     (104,  1),  # Orange Star Airport
    41:     (105,  1),  # Orange Star Port
    42:     (101,  1),  # Orange Star HQ

    43:     (102,  2),  # Blue Moon City
    44:     (103,  2),  # Blue Moon Base
    45:     (104,  2),  # Blue Moon Airport
    46:     (105,  2),  # Blue Moon Port
    47:     (101,  2),  # Blue Moon HQ

    48:     (102,  3),  # Green Earth City
    49:     (103,  3),  # Green Earth Base
    50:     (104,  3),  # Green Earth Airport
    51:     (105,  3),  # Green Earth Port
    52:     (101,  3),  # Green Earth HQ

    53:     (102,  4),  # Yellow Comet City
    54:     (103,  4),  # Yellow Comet Base
    55:     (104,  4),  # Yellow Comet Airport
    56:     (105,  4),  # Yellow Comet Port
    57:     (101,  4),  # Yellow Comet HQ

    81:     (102,  6),  # Red Fire City
    82:     (103,  6),  # Red Fire Base
    83:     (104,  6),  # Red Fire Airport
    84:     (105,  6),  # Red Fire Port
    85:     (101,  6),  # Red Fire HQ

    86:     (102,  7),  # Grey Sky City
    87:     (103,  7),  # Grey Sky Base
    88:     (104,  7),  # Grey Sky Airport
    89:     (105,  7),  # Grey Sky Port
    90:     (101,  7),  # Grey Sky HQ

    91:     (102,  5),  # Black Hole City
    92:     (103,  5),  # Black Hole Base
    93:     (104,  5),  # Black Hole Airport
    94:     (105,  5),  # Black Hole Port
    95:     (101,  5),  # Black Hole HQ

    96:     (102,  8),  # Brown Desert City
    97:     (103,  8),  # Brown Desert Base
    98:     (104,  8),  # Brown Desert Airport
    99:     (105,  8),  # Brown Desert Port
    100:    (101,  8),  # Brown Desert HQ

    101:    (10,   0),  # VPipe
    102:    (10,   0),  # HPipe
    103:    (10,   0),  # NEPipe
    104:    (10,   0),  # ESPipe
    105:    (10,   0),  # SWPipe
    106:    (10,   0),  # WNPipe
    107:    (10,   0),  # NPipe End
    108:    (10,   0),  # EPipe End
    109:    (10,   0),  # SPipe End
    110:    (10,   0),  # WPipe End
    111:    (13,   0),  # Missile Silo
    112:    (14,   0),  # Missile Silo Empty
    113:    (11,   0),  # HPipe Seam
    114:    (11,   0),  # VPipe Seam
    115:    (12,   0),  # HPipe Rubble
    116:    (12,   0),  # VPipe Rubble

    117:    (104,  9),  # Amber Blaze Airport
    118:    (103,  9),  # Amber Blaze Base
    119:    (102,  9),  # Amber Blaze City
    120:    (101,  9),  # Amber Blaze HQ
    121:    (105,  9),  # Amber Blaze Port

    122:    (104, 10),  # Jade Sun Airport
    123:    (103, 10),  # Jade Sun Base
    124:    (102, 10),  # Jade Sun City
    125:    (101, 10),  # Jade Sun HQ
    126:    (105, 10),  # Jade Sun Port

    127:    (106,  9),  # Amber Blaze Com Tower
    128:    (106,  5),  # Black Hole Com Tower
    129:    (106,  2),  # Blue Moon Com Tower
    130:    (106,  8),  # Brown Desert Com Tower
    131:    (106,  3),  # Green Earth Com Tower
    132:    (106, 10),  # Jade Sun Com Tower
    133:    (106,  0),  # Neutral Com Tower
    134:    (106,  1),  # Orange Star Com Tower
    135:    (106,  6),  # Red Fire Com Tower
    136:    (106,  4),  # Yellow Comet Com Tower
    137:    (106,  7),  # Grey Sky Com Tower

    138:    (107,  9),  # Amber Blaze Lab
    139:    (107,  5),  # Black Hole Lab
    140:    (107,  2),  # Blue Moon Lab
    141:    (107,  8),  # Brown Desert Lab
    142:    (107,  3),  # Green Earth Lab
    143:    (107,  7),  # Grey Sky Lab
    144:    (107, 10),  # Jade Sun Lab
    145:    (107,  0),  # Neutral Lab
    146:    (107,  1),  # Orange Star Lab
    147:    (107,  6),  # Red Fire Lab
    148:    (107,  4),  # Yellow Comet Lab

    149:    (104, 11),  # Cobalt Ice Airport
    150:    (103, 11),  # Cobalt Ice Base
    151:    (102, 11),  # Cobalt Ice City
    152:    (106, 11),  # Cobalt Ice Com Tower
    153:    (101, 11),  # Cobalt Ice HQ
    154:    (107, 11),  # Cobalt Ice Lab
    155:    (105, 11),  # Cobalt Ice Port

    156:    (104, 12),  # Pink Cosmos Airport
    157:    (103, 12),  # Pink Cosmos Base
    158:    (102, 12),  # Pink Cosmos City
    159:    (106, 12),  # Pink Cosmos Com Tower
    160:    (101, 12),  # Pink Cosmos HQ
    161:    (107, 12),  # Pink Cosmos Lab
    162:    (105, 12),  # Pink Cosmos Port

    163:    (104, 13),  # Teal Galaxy Airport
    164:    (103, 13),  # Teal Galaxy Base
    165:    (102, 13),  # Teal Galaxy City
    166:    (106, 13),  # Teal Galaxy Com Tower
    167:    (101, 13),  # Teal Galaxy HQ
    168:    (107, 13),  # Teal Galaxy Lab
    169:    (105, 13),  # Teal Galaxy Port

    170:    (104, 14),  # Purple Lightning Airport
    171:    (103, 14),  # Purple Lightning Base
    172:    (102, 14),  # Purple Lightning City
    173:    (106, 14),  # Purple Lightning Com Tower
    174:    (101, 14),  # Purple Lightning HQ
    175:    (107, 14),  # Purple Lightning Lab
    176:    (105, 14),  # Purple Lightning Port

    181:    (104, 15),  # Acid Rain Airport
    182:    (103, 15),  # Acid Rain Base
    183:    (102, 15),  # Acid Rain City
    184:    (106, 15),  # Acid Rain Com Tower
    185:    (101, 15),  # Acid Rain HQ
    186:    (107, 15),  # Acid Rain Lab
    187:    (105, 15),  # Acid Rain Port

    188:    (104, 16),  # White Nova Airport
    189:    (103, 16),  # White Nova Base
    190:    (102, 16),  # White Nova City
    191:    (106, 16),  # White Nova Com Tower
    192:    (101, 16),  # White Nova HQ
    193:    (107, 16),  # White Nova Lab
    194:    (105, 16),  # White Nova Port

    # 195:  (900,  0),  # Teleport Tile  # Top of list

    196:    (104, 17),  # Azure Asteroid Airport
    197:    (103, 17),  # Azure Asteroid Base
    198:    (102, 17),  # Azure Asteroid City
    199:    (106, 17),  # Azure Asteroid Com Tower
    200:    (101, 17),  # Azure Asteroid HQ
    201:    (107, 17),  # Azure Asteroid Lab
    202:    (105, 17),  # Azure Asteroid Port

    203:    (104, 18),  # Noir Eclipse Airport
    204:    (103, 18),  # Noir Eclipse Base
    205:    (102, 18),  # Noir Eclipse City
    206:    (106, 18),  # Noir Eclipse Com Tower
    207:    (101, 18),  # Noir Eclipse HQ
    208:    (107, 18),  # Noir Eclipse Lab
    209:    (105, 18),  # Noir Eclipse Port

    210:    (104, 19),  # Silver Claw Airport
    211:    (103, 19),  # Silver Claw Base
    212:    (102, 19),  # Silver Claw City
    213:    (106, 19),  # Silver Claw Com Tower
    214:    (101, 19),  # Silver Claw HQ
    215:    (107, 19),  # Silver Claw Lab
    216:    (105, 19),  # Silver Claw Port

    217:    (104, 20),  # Umber Wilds Airport
    218:    (103, 20),  # Umber Wilds Base
    219:    (102, 20),  # Umber Wilds City
    220:    (106, 20),  # Umber Wilds Com Tower
    221:    (101, 20),  # Umber Wilds HQ
    222:    (107, 20),  # Umber Wilds Lab
    223:    (105, 20),  # Umber Wilds Port
}

# Relate AWBW Unit IDs (keys) to Internal Unit IDs (values)
AWBW_UNIT_CODE: Dict[int, int] = {
    1:          1,      # Infantry
    2:          2,      # Mech
    3:          14,     # Md. Tank
    4:          13,     # Tank
    5:          12,     # Recon
    6:          11,     # APC
    7:          21,     # Artillery
    8:          22,     # Rockets
    9:          17,     # Anti-Air
    10:         23,     # Missiles
    11:         33,     # Fighter
    12:         34,     # Bomber
    13:         32,     # B Copter
    14:         31,     # T Copter
    15:         45,     # Battleship
    16:         43,     # Cruiser
    17:         42,     # Lander
    18:         44,     # Sub
    28:         41,     # Black Boat
    29:         46,     # Carrier
    30:         35,     # Stealth
    46:         15,     # Neotank
    960900:     24,     # Pipe Runner
    968731:     36,     # Black Bomb
    1141438:    16,     # Megatank
}

# Relating 2 character AWBW country ID (keys) to Internal country ID (values)
AWBW_COUNTRY_CODE: Dict[str, int] = {
    "os":   1,
    "bm":   2,
    "ge":   3,
    "yc":   4,
    "bh":   5,
    "rf":   6,
    "gs":   7,
    "bd":   8,
    "ab":   9,
    "js":   10,
    "ci":   11,
    "pc":   12,
    "tg":   13,
    "pl":   14,
    "ar":   15,
    "wn":   16,
    "aa":   17,
    "ne":   18,
    "sc":   19,
    "uw":   20
}

# From Internal Terrain IDs, find the offset for appropriate tile orientation based on surroundings.
AWBW_AWARENESS: Dict[Union[int, str], Union[Dict[int, int], Dict[int, List[int]]]] = {# Roads: Offset from 15
    4:      {
        0:  0,
        1:  0,
        2:  1,
        3:  4,
        4:  0,
        5:  0,
        6:  3,
        7:  7,
        8:  1,
        9:  5,
        10: 1,
        11: 8,
        12: 6,
        13: 9,
        14: 10,
        15: 2
    },
# Bridge: Offset from 26
    5:      {
        0:  0,
        1:  0,
        2:  1,
        3:  1,
        4:  0,
        5:  0,
        6:  1,
        7:  0,
        8:  1,
        9:  1,
        10: 1,
        11: 1,
        12: 1,
        13: 0,
        14: 1,
        15: 1
    },
# Shoal: Offset from 29
    7:      {
        0:  0,
        1:  3,
        2:  1,
        3:  1,
        4:  2,
        5:  2,
        6:  1,
        7:  1,
        8:  0,
        9:  0,
        10: 0,
        11: 3,
        12: 0,
        13: 0,
        14: 2,
        15: 0
    },
# River: Offset from 4
    9:      {
        0:  0,
        1:  0,
        2:  1,
        3:  4,
        4:  0,
        5:  0,
        6:  3,
        7:  7,
        8:  1,
        9:  5,
        10: 1,
        11: 8,
        12: 6,
        13: 9,
        14: 10,
        15: 2
    },
# Pipe: Offset from 101
    10:     {
        0:  0,
        1:  7,
        2:  6,
        3:  4,
        4:  9,
        5:  1,
        6:  3,
        7:  1,
        8:  8,
        9:  5,
        10: 0,
        11: 0,
        12: 2,
        13: 1,
        14: 0,
        15: 1
    },
# Pipe Seam: Offset from 113
    11:     {
        0:  0,
        1:  0,
        2:  1,
        3:  0,
        4:  0,
        5:  0,
        6:  0,
        7:  0,
        8:  1,
        9:  0,
        10: 1,
        11: 1,
        12: 0,
        13: 0,
        14: 1,
        15: 0
    },
# Destroyed Pipe Seam: Offset from 115
    12:     {
        0:  0,
        1:  0,
        2:  1,
        3:  0,
        4:  0,
        5:  0,
        6:  0,
        7:  0,
        8:  1,
        9:  0,
        10: 1,
        11: 1,
        12: 0,
        13: 0,
        14: 1,
        15: 0
    },
# Define which tile types MAIN terrain IDs should be aware of
    "aware_of": {
        4:  [4, 5, 13, 14, *MAIN_TERR_CAT["properties"]],  # Road
        5:  [7, *MAIN_TERR_CAT["land"]],  # Bridge  # TODO: Figure out why bridges are ignoring awareness
        7:  [9, *MAIN_TERR_CAT["land"]],  # Shoal
        9:  [5, 9],  # River
        10: [10, 11, 12],  # Pipe
        11: [10, 11, 12],  # Pipe Seam
        12: [10, 11, 12],  # Destroyed Pipe Seam
    }
}

def find_overrides():
    pass

def main_terr_to_awbw(terr: int = 1, ctry: int = 0) -> List[Union[str, int]]:
    default_value = [""]
    override = {
        999999:     999999,
    }
    match = list()
    for k, v in AWBW_TERR.items():
        if terr in override.keys():
            match.append(override[terr])
            break
        if (terr, ctry) == v:
            match.append(k)
    if match:
        return match
    else:
        return default_value
