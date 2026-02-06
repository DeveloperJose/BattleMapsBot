"""Terrain ID to sprite name mappings for AW2 tileset.

Ported from AWBW site's tilesets.js TS_terrainIdToName.
Uses base sprite names (without gs_ prefix).
"""

# Terrain ID to sprite name mapping
# Note: ID 28 (sea) is missing from the site mapping - we use "sea" as default
TERRAIN_ID_TO_SPRITE = {
    # Basic Terrain
    1: "plain",
    2: "mountain",
    3: "wood",
    # Rivers
    4: "hriver",
    5: "vriver",
    6: "criver",
    7: "esriver",
    8: "swriver",
    9: "wnriver",
    10: "neriver",
    11: "eswriver",
    12: "swnriver",
    13: "wneriver",
    14: "nesriver",
    # Roads
    15: "hroad",
    16: "vroad",
    17: "croad",
    18: "esroad",
    19: "swroad",
    20: "wnroad",
    21: "neroad",
    22: "eswroad",
    23: "swnroad",
    24: "wneroad",
    25: "nesroad",
    # Bridges
    26: "hbridge",
    27: "vbridge",
    # Shoals (ID 28 is sea, but missing from site mapping)
    28: "sea",
    29: "hshoal",
    30: "hshoaln",
    31: "vshoal",
    32: "vshoale",
    33: "reef",
    # Neutral Buildings
    34: "neutralcity",
    35: "neutralbase",
    36: "neutralairport",
    37: "neutralport",
    # Orange Star Buildings
    38: "orangestarcity",
    39: "orangestarbase",
    40: "orangestarairport",
    41: "orangestarport",
    42: "orangestarhq",
    # Blue Moon Buildings
    43: "bluemooncity",
    44: "bluemoonbase",
    45: "bluemoonairport",
    46: "bluemoonport",
    47: "bluemoonhq",
    # Green Earth Buildings
    48: "greenearthcity",
    49: "greenearthbase",
    50: "greenearthairport",
    51: "greenearthport",
    52: "greenearthhq",
    # Yellow Comet Buildings
    53: "yellowcometcity",
    54: "yellowcometbase",
    55: "yellowcometairport",
    56: "yellowcometport",
    57: "yellowcomethq",
    # Red Fire Buildings
    81: "redfirecity",
    82: "redfirebase",
    83: "redfireairport",
    84: "redfireport",
    85: "redfirehq",
    # Grey Sky Buildings
    86: "greyskycity",
    87: "greyskybase",
    88: "greyskyairport",
    89: "greyskyport",
    90: "greyskyhq",
    # Black Hole Buildings
    91: "blackholecity",
    92: "blackholebase",
    93: "blackholeairport",
    94: "blackholeport",
    95: "blackholehq",
    # Brown Desert Buildings
    96: "browndesertcity",
    97: "browndesertbase",
    98: "browndesertairport",
    99: "browndesertport",
    100: "browndeserthq",
    # Pipes
    101: "vpipe",
    102: "hpipe",
    103: "nepipe",
    104: "espipe",
    105: "swpipe",
    106: "wnpipe",
    107: "npipeend",
    108: "epipeend",
    109: "spipeend",
    110: "wpipeend",
    # Missile Silos
    111: "missilesilo",
    112: "missilesiloempty",
    # Pipe Seams and Rubble
    113: "hpipeseam",
    114: "vpipeseam",
    115: "hpiperubble",
    116: "vpiperubble",
    # Amber Blossom Buildings
    117: "amberblossomairport",
    118: "amberblossombase",
    119: "amberblossomcity",
    120: "amberblossomhq",
    121: "amberblossomport",
    # Jade Sun Buildings
    122: "jadesunairport",
    123: "jadesunbase",
    124: "jadesuncity",
    125: "jadesunhq",
    126: "jadesunport",
    # Command Towers
    127: "amberblossomcomtower",
    128: "blackholecomtower",
    129: "bluemooncomtower",
    130: "browndesertcomtower",
    131: "greenearthcomtower",
    132: "jadesuncomtower",
    133: "neutralcomtower",
    134: "orangestarcomtower",
    135: "redfirecomtower",
    136: "yellowcometcomtower",
    137: "greyskycomtower",
    # Labs
    138: "amberblossomlab",
    139: "blackholelab",
    140: "bluemoonlab",
    141: "browndesertlab",
    142: "greenearthlab",
    143: "greyskylab",
    144: "jadesunlab",
    145: "neutrallab",
    146: "orangestarlab",
    147: "redfirelab",
    148: "yellowcometlab",
    # Cobalt Ice Buildings
    149: "cobalticeairport",
    150: "cobalticebase",
    151: "cobalticecity",
    152: "cobalticecomtower",
    153: "cobalticehq",
    154: "cobalticelab",
    155: "cobalticeport",
    # Pink Cosmos Buildings
    156: "pinkcosmosairport",
    157: "pinkcosmosbase",
    158: "pinkcosmoscity",
    159: "pinkcosmoscomtower",
    160: "pinkcosmoshq",
    161: "pinkcosmoslab",
    162: "pinkcosmosport",
    # Teal Galaxy Buildings
    163: "tealgalaxyairport",
    164: "tealgalaxybase",
    165: "tealgalaxycity",
    166: "tealgalaxycomtower",
    167: "tealgalaxyhq",
    168: "tealgalaxylab",
    169: "tealgalaxyport",
    # Purple Lightning Buildings
    170: "purplelightningairport",
    171: "purplelightningbase",
    172: "purplelightningcity",
    173: "purplelightningcomtower",
    174: "purplelightninghq",
    175: "purplelightninglab",
    176: "purplelightningport",
    # Acid Rain Buildings
    181: "acidrainairport",
    182: "acidrainbase",
    183: "acidraincity",
    184: "acidraincomtower",
    185: "acidrainhq",
    186: "acidrainlab",
    187: "acidrainport",
    # White Nova Buildings
    188: "whitenovaairport",
    189: "whitenovabase",
    190: "whitenovacity",
    191: "whitenovacomtower",
    192: "whitenovahq",
    193: "whitenovalab",
    194: "whitenovaport",
    # Special
    195: "teleporter",
    # Azure Asteroid Buildings
    196: "azureasteroidairport",
    197: "azureasteroidbase",
    198: "azureasteroidcity",
    199: "azureasteroidcomtower",
    200: "azureasteroidhq",
    201: "azureasteroidlab",
    202: "azureasteroidport",
    # Noir Eclipse Buildings
    203: "noireclipseairport",
    204: "noireclipsebase",
    205: "noireclipsecity",
    206: "noireclipsecomtower",
    207: "noireclipsehq",
    208: "noireclipselab",
    209: "noireclipseport",
    # Silver Claw Buildings
    210: "silverclawairport",
    211: "silverclawbase",
    212: "silverclawcity",
    213: "silverclawcomtower",
    214: "silverclawhq",
    215: "silverclawlab",
    216: "silverclawport",
    # Umber Wilds Buildings
    217: "umberwildsairport",
    218: "umberwildsbase",
    219: "umberwildscity",
    220: "umberwildscomtower",
    221: "umberwildshq",
    222: "umberwildslab",
    223: "umberwildsport",
}

# Country ID to sprite prefix mapping
COUNTRY_ID_TO_PREFIX = {
    1: "os",  # Orange Star
    2: "bm",  # Blue Moon
    3: "ge",  # Green Earth
    4: "yc",  # Yellow Comet
    5: "bh",  # Black Hole
    6: "rf",  # Red Fire
    7: "gs",  # Grey Sky
    8: "bd",  # Brown Desert
    9: "ab",  # Amber Blaze
    10: "js",  # Jade Sun
    11: "ci",  # Cobalt Ice
    12: "pc",  # Pink Cosmos
    13: "tg",  # Teal Galaxy
    14: "pl",  # Purple Lightning
    15: "ar",  # Acid Rain
    16: "wn",  # White Nova
    17: "aa",  # Azure Asteroid
    18: "ne",  # Noir Eclipse
    19: "sc",  # Silver Claw
    20: "uw",  # Umber Wilds
}

# Unit ID to sprite name suffix mapping
UNIT_ID_TO_SPRITE_NAME = {
    1: "infantry",
    2: "mech",
    11: "apc",
    12: "recon",
    13: "tank",
    14: "md.tank",
    15: "neotank",
    16: "megatank",
    17: "anti-air",
    21: "artillery",
    22: "rocket",
    23: "missile",
    24: "piperunner",
    31: "t-copter",
    32: "b-copter",
    33: "fighter",
    34: "bomber",
    35: "stealth",
    36: "blackbomb",
    41: "blackboat",
    42: "lander",
    43: "cruiser",
    44: "sub",
    45: "battleship",
    46: "carrier",
}

# Maximum terrain ID
MAX_TERRAIN_ID = max(TERRAIN_ID_TO_SPRITE.keys())
