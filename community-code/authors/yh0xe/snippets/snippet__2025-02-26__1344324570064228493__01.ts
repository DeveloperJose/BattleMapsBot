/** 
 * Record<X_Index, Recrod<Y_Index, BuildingsInfo
 * 
 * If encountered `[X][Y] === undefined` then assume the tile is a terrain.
 * 
 * If encountered `[X] === []` then no terrain in that column, and every tile is a building.
 * 
 * Usage:
 * 
 * ``js disabled to stop breaking discord
 * if (buildingsInfo[x][y]) { 
 *    // A building is present on that tile
 *  }
 * `` disabled to stop breaking discord
 * */
export type BuildingsInfo = Record<number, Record<number, BuildingsInfoEntry> | BuildingsInfoEntry[]>;
