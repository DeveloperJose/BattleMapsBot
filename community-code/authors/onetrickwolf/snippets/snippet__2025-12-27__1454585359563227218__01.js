// AWBW Army Incompatibility Data
// Generated: 2025-12-27T21:17:25.810Z

const incompatiblePairs = [
  ['os', 'rf'], // Orange Star vs Red Fire
  ['os', 'bd'], // Orange Star vs Brown Desert
  ['os', 'ab'], // Orange Star vs Amber Blossom
  ['os', 'pc'], // Orange Star vs Pink Cosmos
  ['os', 'wn'], // Orange Star vs White Nova
  ['os', 'uw'], // Orange Star vs Umber Wilds
  ['bm', 'ci'], // Blue Moon vs Cobalt Ice
  ['bm', 'pc'], // Blue Moon vs Pink Cosmos
  ['bm', 'tg'], // Blue Moon vs Teal Galaxy
  ['bm', 'pl'], // Blue Moon vs Purple Lightning
  ['bm', 'aa'], // Blue Moon vs Azure Asteroid
  ['bm', 'sc'], // Blue Moon vs Silver Claw
  ['ge', 'js'], // Green Earth vs Jade Sun
  ['ge', 'tg'], // Green Earth vs Teal Galaxy
  ['ge', 'ar'], // Green Earth vs Acid Rain
  ['ge', 'aa'], // Green Earth vs Azure Asteroid
  ['ge', 'sc'], // Green Earth vs Silver Claw
  ['yc', 'bd'], // Yellow Comet vs Brown Desert
  ['yc', 'ab'], // Yellow Comet vs Amber Blossom
  ['yc', 'ar'], // Yellow Comet vs Acid Rain
  ['yc', 'wn'], // Yellow Comet vs White Nova
  ['bh', 'gs'], // Black Hole vs Grey Sky
  ['bh', 'pc'], // Black Hole vs Pink Cosmos
  ['bh', 'ne'], // Black Hole vs Noir Eclipse
  ['bh', 'sc'], // Black Hole vs Silver Claw
  ['rf', 'bd'], // Red Fire vs Brown Desert
  ['rf', 'ab'], // Red Fire vs Amber Blossom
  ['rf', 'pc'], // Red Fire vs Pink Cosmos
  ['rf', 'wn'], // Red Fire vs White Nova
  ['rf', 'ne'], // Red Fire vs Noir Eclipse
  ['rf', 'uw'], // Red Fire vs Umber Wilds
  ['gs', 'js'], // Grey Sky vs Jade Sun
  ['gs', 'ne'], // Grey Sky vs Noir Eclipse
  ['gs', 'sc'], // Grey Sky vs Silver Claw
  ['bd', 'ab'], // Brown Desert vs Amber Blossom
  ['bd', 'ar'], // Brown Desert vs Acid Rain
  ['bd', 'wn'], // Brown Desert vs White Nova
  ['bd', 'uw'], // Brown Desert vs Umber Wilds
  ['ab', 'wn'], // Amber Blossom vs White Nova
  ['ab', 'uw'], // Amber Blossom vs Umber Wilds
  ['js', 'tg'], // Jade Sun vs Teal Galaxy
  ['js', 'ar'], // Jade Sun vs Acid Rain
  ['js', 'aa'], // Jade Sun vs Azure Asteroid
  ['js', 'sc'], // Jade Sun vs Silver Claw
  ['ci', 'pl'], // Cobalt Ice vs Purple Lightning
  ['ci', 'aa'], // Cobalt Ice vs Azure Asteroid
  ['ci', 'sc'], // Cobalt Ice vs Silver Claw
  ['pc', 'pl'], // Pink Cosmos vs Purple Lightning
  ['pc', 'wn'], // Pink Cosmos vs White Nova
  ['tg', 'ar'], // Teal Galaxy vs Acid Rain
  ['tg', 'aa'], // Teal Galaxy vs Azure Asteroid
  ['tg', 'sc'], // Teal Galaxy vs Silver Claw
  ['ar', 'sc'], // Acid Rain vs Silver Claw
  ['ar', 'uw'], // Acid Rain vs Umber Wilds
  ['wn', 'uw'], // White Nova vs Umber Wilds
  ['aa', 'sc'], // Azure Asteroid vs Silver Claw
];

// Helper function to check if two armies are compatible
function areCompatible(army1Code, army2Code) {
  return !incompatiblePairs.some(([a, b]) => 
    (a === army1Code && b === army2Code) || 
    (a === army2Code && b === army1Code)
  );
}

// Find a replacement for army2 that's compatible with army1
function findReplacement(army1Code, army2Code, availableArmies) {
  if (areCompatible(army1Code, army2Code)) return null;
  
  return availableArmies.find(code => 
    code !== army1Code && 
    code !== army2Code && 
    areCompatible(army1Code, code)
  );
}

// All armies for reference
const allArmies = ["os","bm","ge","yc","bh","rf","gs","bd","ab","js","ci","pc","tg","pl","ar","wn","aa","ne","sc","uw"];

// Example usage:
// areCompatible('os', 'bm') // true or false
// findReplacement('bh', 'gs', allArmies) // returns a compatible army code
