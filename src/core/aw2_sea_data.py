"""Bitmask constants for sea rendering."""

# Bit values for 8 neighbors (matching JS order: top-left, top, top-right, right, bottom-right, bottom, bottom-left, left)
NW = 1
N = 2
NE = 4
E = 8
SE = 16
S = 32
SW = 64
W = 128

# River connection bits (matching JS: 0x05, 0x14, 0x50, 0x41)
RIVER_CONNECT_N = 0x05
RIVER_CONNECT_W = 0x14
RIVER_CONNECT_S = 0x50
RIVER_CONNECT_E = 0x41

# Terrain IDs that count as water for sea tile detection
SEA_WATER_IDS = {28, 33}  # sea, reef

# This mapping defines which seashore sprite to use based on the surrounding
# land tiles, represented by a bitmask. The key is the sum of the bit values
# for each neighboring land tile.
# Neighbor order: NW(1), N(2), NE(4), E(8), SE(16), S(32), SW(64), W(128)
# Only includes combinations that have sprites in the aw2 atlas.
SEA_MASK_TO_SPRITE = {
    # No land neighbors - pure sea
    0: "sea",
    # Single straight shores
    S: "seashoren",   # land to south -> north shore
    N: "seashores",   # land to north -> south shore
    W: "seashoree",   # land to west -> east shore
    E: "seashorew",   # land to east -> west shore
    # Corners - use existing corner sprites
    # SE corner (land S, SW, W)
    S | SW | W: "seashorene",
    S | W: "seashorene",
    # SW corner (land S, SE, E) - use seashoresw
    S | SE | E: "seashoresw",
    S | E: "seashoresw",
    # SW corner (land N, NW, W)
    N | NW | W: "seashoresw",
    N | W: "seashoresw",
    # SE corner (land N, NE, E) - use seashoresecorner
    N | NE | E: "seashoresecorner",
    N | E: "seashoresecorner",
    # Diagonal only - map to nearest corner
    SW: "seashorene",   # SE diagonal -> SE corner
    SE: "seashoresw",   # SW diagonal -> SW corner
    NW: "seashoresecorner",  # NE diagonal -> SE corner
    NE: "seashorenecorner",  # NE diagonal -> NE corner
    # More complex combinations - fall back to nearest shore sprite
    N | S | W: "seashoree",
    N | S | E: "seashorew",
    N | E | W: "seashores",
    S | E | W: "seashoren",
    # Two adjacent (no diagonal)
    N | S: "seashoreall",
    E | W: "seashoreall",
    # All sides land
    N | S | E | W | NE | SE | SW | NW: "seashoreall",
}
