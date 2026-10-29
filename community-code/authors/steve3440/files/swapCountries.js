// ==UserScript==
// @name            AWBW Swap Sides
// @match           https://awbw.amarriner.com/moveplanner.php*
// @version         0.1
// @description     Adds a button to the moveplanner that swaps players sides, only works for 2Q rotational symmetry (most league maps)
// @author          steve
// ==/UserScript==
(function(){

const swapCountriesButton = $('<div style="width: auto; margin-left: 5px; display: flex;" class="planner-tools-btn-lg">Swap countries<span class="game-tools-btn-text small_test">Swap countries duh</span></div>').click(swapSides);
$('#countries').append(swapCountriesButton);

const buildingsById = Object.values(buildingsInfo).flatMap(o=>Object.values(o).flat()).reduce((acc, o) => {
    o.id !== undefined ?
        acc[o.id] = o : acc[o.buildings_id] = o;
    return acc;
}, {});

function swapSides() {
    if (
        window.location.pathname.indexOf('moveplanner') < 0 ||
        Object.keys(playersInfo).length > 2
    ) {
        alert("Only 2 player games in the moveplanner are supported");
        return;
    }
    const width = (map.width/16)-1,
          height = (map.height/16)-1;

    let units = document.querySelectorAll('span[id^="unit_"]');
    for (let i = 0; i < units.length; i++) {
        let unit = units[i],
            uid = unit.id.split('_')[1]|0,
            x = unitsInfo[uid].units_x,
            y = unitsInfo[uid].units_y,
            newX = width - x,
            newY = height - y;

        unitsInfo[uid].units_x = newX;
        unitsInfo[uid].units_y = newY;
        unit.style.left = newX*16 + 'px';
        unit.style.top = newY*16 + 'px';
    }

    let buildings = document.querySelectorAll('span[id^="building_"]');

    for (let i = 0; i < buildings.length; i++) {
        let building = buildings[i],
            bid = building.id.split('_')[1]|0,
            x_coord = 'x',
            y_coord = 'y';
        if (buildingsById[bid][x_coord] === undefined) {
            x_coord = 'buildings_x';
            y_coord = 'buildings_y';
        }
        let x = buildingsById[bid][x_coord],
            y = buildingsById[bid][y_coord],
            newX = width - x,
            newY = height - y,
            buildingHeight = building.children[0].height;

        buildingsById[bid][x_coord] = newX;
        buildingsById[bid][y_coord] = newY;
        //buildingsInfo[newX][newY] = buildingsById[bid];
        building.style.left = newX*16 + 1 + 'px';
        building.style.top = newY*16 - (buildingHeight-17) + 'px';
    }
}})();

