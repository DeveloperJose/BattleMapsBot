(async function() {
const canvas = document.createElement('canvas'),
      ctx = canvas.getContext('2d'),
      mapImg = document.getElementById('map-background');

document.getElementById('water-canvas')?.remove();
canvas.id = 'water-canvas';
canvas.style.zIndex = 100;

mapImg.insertAdjacentElement('afterend', canvas);

canvas.width = maxX * 16;
canvas.height = maxY * 16;

const naval_tiles = [28, 29, 30, 31, 32, 33],
      mask = {};
for (let x = 0; x < maxX; x++) {
    mask[x] = {};
    for (let y = 0; y < maxY; y++) {
        const tile = terrainInfo[x][y]?.terrain_id;
        if (!tile) continue;
        if (naval_tiles.includes(tile)) {
            mask[x][y] = true;
        }
    }
}
function render () {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    for (let x = 0; x < maxX; x++) {
        for (let y = 0; y < maxY; y++) {
            if (!mask[x][y]) continue;
            ctx.fillStyle = 'rgba(0, 0, 255, 0.5)';
            ctx.fillRect(x * 16, y * 16, 16, 16);
        }
    }
}
requestAnimationFrame(render);
})();
