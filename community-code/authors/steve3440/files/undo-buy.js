// ==UserScript==
// @name         AWBW Undo Buy
// @namespace    awbw
// @match        https://awbw.amarriner.com/game.php*
// @icon         https://awbw.amarriner.com/terrain/coin.gif
// @version      0.2
// @description  Click units to undo buy. End turn and Eagle SCOP buys all pending units
// @author       steve
// @license      MIT
// @grant        none
// @inject-into  page
// ==/UserScript==

// TODO BUGS
// - colin and hachi powers glitches funds?

(function () {
const hidden_units = ['Piperunner','Missile'],
      buyback_time = 10000; // ms

let units_to_buy = {},
    fake_units_id = 0;
/*
units_to_buy<buildingId, {buildData, newUnit, costMultiplier}> =
{
  buildingId:
  {
    buildData: {
      action: "Build",
      playerID: viewerPId,
      unitID: unitId,
      buildingID: buildingId
    },
    newUnit: {
      buildUnit format unit object
    },
    costMultiplier: Number,
  },
  buildingId:
  ...
}
*/

let socketOnMessageOld = webSocket.onmessage;
webSocket.onmessage = function (jsonData) {
  json = JSON.parse(jsonData.data);
  if (json.Build && json.Build.action === "Build") {
    let newUnit = json.Build.newUnit;
    if (newUnit && newUnit.units_players_id === viewerPId) {
      let buildingId = buildingsInfo[newUnit.units_x][newUnit.units_y].buildings_id,
          u = units_to_buy[buildingId];
      if (u && u.newUnit.units_x === newUnit.units_x &&
               u.newUnit.units_y === newUnit.units_y) {
        undoBuy(buildingId, false);
      }
    }
  }
  socketOnMessageOld(jsonData);
}

let joinUnitsOld = joinUnits;
joinUnits = function (joinData) {
  joinUnitsOld(joinData);
  if (joinData.playerId == viewerPId) {
    fixFunds();
  }
}
actionHandlers.Join = joinUnits;

let repairUnitOld = repairUnit;
repairUnit = function (repairData) {
  repairUnitOld(repairData);
  if (playersUnits[viewerPId][repairData.unitId]) {
    fixFunds();
  }
}
actionHandlers.Repair = repairUnit;

function fixFunds () {
  Object.values(units_to_buy).forEach(u => {
    let cost = u.newUnit.units_cost * u.costMultiplier;
    playersInfo[viewerPId].players_funds -= cost;
    //playersUnitCount[viewerPId].value += cost;
  });

  updatePlayerRow(viewerPId, {
    "player-funds": playersInfo[viewerPId].players_funds,
    //"unit-value": playersUnitCount[viewerPId].value
  });
}

function buyUnits () {
  return new Promise(function (resolve, reject = () => {handleClientError(new Error(`Couldn't buy units ¯\\_(ツ)_/¯`));}) {
    let next_attempt_delay = 200,
        prev_remaining_length = 0;
    (function tryBuyUnits() {
      let remaining = Object.values(units_to_buy),
          buy_delay = 0;
      if (remaining.length > 0) {
        if (remaining.length !== prev_remaining_length) {
          prev_remaining_length = remaining.length;

          remaining.forEach(function (u) {
            setTimeout(() => emitData(webSocket, u.buildData), buy_delay);
            buy_delay += 40;
          });
        }
        if (next_attempt_delay > 1000) {
          reject();
          return;
        }
        setTimeout(tryBuyUnits, next_attempt_delay + buy_delay);
        next_attempt_delay += 200;
        return;
      }
      units_to_buy = {};

      resolve();
    })();
  });
}

if (scopButton && playersInfo[viewerPId].co_name === 'Eagle') {
  //getEventListeners(scopButton).click?.forEach(e => scopButton.removeEventListener('click',e.listener))
  let newScopButton = document.createElement('img');
  newScopButton.src="terrain/aw2/bluestar.gif";
  newScopButton.alt="SCOP Button";
  newScopButton.classList.add("scop-button");
  newScopButton.style.display=scopButton.style.display;

  newScopButton.addEventListener("click", function () {
    if (freezeGame) return;

    buyUnits().then(() => {
      emitData(webSocket, {
        action: "Power",
        coPower: "S",
        coName: playersInfo[viewerPId].co_name,
        playerID: viewerPId
      });
    }).catch(() => {
      handleClientError(new Error(`SCOP failed: unable to buy units, try again.`));
    });
  });

  scopButton.replaceWith(newScopButton);
  scopButton = newScopButton;
}

endTurn = function(action) {
  buyUnits().then(() => {
    var endTurnData = {
      action: action,
      playerID: viewerPId
    };
    emitData(webSocket, endTurnData);
  }).catch(() => {
    handleClientError(new Error(`Couldn't buy units ¯\\_(ツ)_/¯`));
  });
};

function undoBuy (buildingId, updateUi = false) {
  let buyInfo = units_to_buy[buildingId],
      unit = buyInfo.newUnit,
      uid = unit.units_id,
      cost = unit.units_cost * buyInfo.costMultiplier;
  playersInfo[viewerPId].players_funds += cost;
  playersUnitCount[viewerPId].value -= cost;

  if(updateUi) {
    updatePlayerRow(viewerPId, {
      "player-funds": playersInfo[viewerPId].players_funds,
      "unit-value": playersUnitCount[viewerPId].value
    });
  }

  deleteUnitInfo(unitsInfo[uid]);
  deleteUnitSpan(uid);
  delete units_to_buy[buildingId];
}

/*
let showBuildOptionsOld = showBuildOptions;
showBuildOptions = function(x, y) {
    showBuildOptionsOld(x, y);
    buildOptionsContent.querySelectorAll('li').forEach(li => {
        let unitName = li.textContent;
        console.log(unitName);
        if(hidden_units.some(u => unitName.includes(u))) {
            li.remove();
        }
    });
}
*/

showBuildOptions = function(x, y) {
  var building = buildingsInfo[x][y];
  var buildingId = building.buildings_id;
  var buildingName = building.terrain_name;
  var coName = playersInfo[viewerPId].co_name;
  var coPower = playersInfo[viewerPId].players_co_power_on;
  var playerFunds = playersInfo[viewerPId].players_funds;
  var mTypes; //Get what units can be built

  if (/Base/.test(buildingName) || /City/.test(buildingName) && coName === "Hachi" && coPower === "S") {
    mTypes = ["F", "B", "T", "W", "P"];
  } else if (/Airport/.test(buildingName)) {
    mTypes = ["A"];
  } else if (/Port/.test(buildingName)) {
    mTypes = ["L", "S"];
  }

  if (!mTypes) return;
  var buildOptions = [];
  var hasLabs = playersInfo[viewerPId].labs !== 0;

  for (var unit in genericUnits) {
    //Skip banned units
    if (banUnits && banUnits[unit]) continue; //Skip lab units

    if (labUnits && labUnits[unit] && !hasLabs) continue;

    if (hidden_units.includes(unit)) continue; // XXX

    var mType = genericUnits[unit].units_movement_type;

    if (mTypes.includes(mType)) {
      buildOptions.push(genericUnits[unit]);
    }
  }

  var sortedOptions = buildOptions.sort(function (a, b) {
    return a.units_cost - b.units_cost;
  });
  var f = document.createDocumentFragment(); //Clear current menu

  var currentOptions = document.querySelector(".build-options-game ul");
  currentOptions.innerHTML = "";
  var playerCountry = playersInfo[viewerPId].countries_code;
  var costMultiplier = findCostMultiplier(viewerPId); //Create new option

  sortedOptions.forEach(function (unit) {
    var canBuy = playerFunds >= unit.units_cost * costMultiplier;
    var unitId = unit.units_id;
    var unitName = unit.units_name;
    var unitSpan = createUnitSpan(unit, (!canBuy ? "gs_" : "") + playerCountry);
    var li = createOption(unitName, unitSpan);
    var costSpan = document.createElement("span");
    costSpan.classList.add("unit-cost");
    costSpan.textContent = unit.units_cost * costMultiplier;
    li.setAttribute("data-build-unit", unitId);
    li.appendChild(costSpan); //Strike unit if can't buy
    //Will need visuals for lab units that aren't buyable in the menu

    if (!canBuy || labUnits && labUnits[unitName] && !hasLabs) li.classList.add("forbidden");else {
      li.classList.add("hover-lower-bright");

      li.onclick = function () {
        li.onclick = null;
        if (units_to_buy[buildingId]) {
          return;
        }
        let buildData = {
          action: "Build",
          playerID: viewerPId,
          unitID: unitId,
          buildingID: buildingId
        };

        let buyTime = buyback_time;
        if (remainingTurnTime < 10) {
          emitData(webSocket, buildData);
          return;
        } else if (remainingTurnTime < 20) {
          buyTime = 4000;
        }

        let new_unit_id = (fake_units_id++)+'fake',
          newUnit = {
            ...genericUnits[unitName],
            //"0": 143489623,
            "units_id": new_unit_id,
            "units_games_id": gameId,
            "units_players_id": viewerPId,
            "units_x": x,
            "units_y": y,
            "units_moved": 1,
            "units_capture": 0,
            "units_fired": 1,
            "countries_code": playersInfo[viewerPId].countries_code
          };

        units_to_buy[buildingId] = {buildData, newUnit, costMultiplier};

        buildUnit({
            action: "Build",
            discovered: null,
            newUnit
        });
        let unitEl = document.querySelector(`[data-unit-id="${newUnit.units_id}"]`);
        unitEl.onmousedown = function(e) {
          unitEl.onmousedown = null;
          e.stopPropagation();

          undoBuy(buildingId, true);
        };
        let coinImg = document.createElement('img');
        coinImg.style = 'position:absolute; top:9px; left:-3px; transform: scale(0.75);'
        coinImg.src = 'terrain/coin.gif';
        unitEl.appendChild(coinImg);

        setTimeout(function () {
          let u = units_to_buy[buildingId];
          //console.log(u)
          if(u && u.newUnit.units_id === new_unit_id) {
            emitData(webSocket, buildData);
          }
        }, buyTime);

        closeMenu();
      };
    }
    f.appendChild(li);
  });
  buildOptionsContent.appendChild(f);
  openMenu(buildOptionsMenu, x, y);
}

createNewUnit = function (unit, pId) {
  var countryCode = unit.countries_code;
  var movedState = unit.units_moved;
  var playerId = unit.units_players_id || pId;

  if (viewerColors) {
    countryCode = viewerColors[playerId];
  }

  var player = playersInfo[playerId];
  var newUnitId = unit.units_id;
  var unitSpan = createUnitSpan(unit, (movedState === 1 ? "gs_" : "") + countryCode);
  var x = unit.units_x;
  var y = unit.units_y;
  var unitClasses = ["game-unit", "clickable"];

  if (gameAnims || !gameAnims && playerId !== viewerPId) {
    unitClasses.push("game-unit-anim");
  }

  setElementAttributes(unitSpan, unitClasses, "data-unit-id", newUnitId, x, y);
  updateUnitMap(newUnitId, player.players_team, x, y);
  var playerUnits = playersUnits[playerId];

  if (!playerUnits || Array.isArray(playerUnits)) {
    playersUnits[playerId] = {};
  }

  playersUnits[playerId][newUnitId] = newUnitId;

  unitsInfo[newUnitId] = unit;
  checkLowProp(newUnitId, unitSpan, "units_ammo", "aniammo");
  checkLowProp(newUnitId, unitSpan, "units_fuel", "anifuel");
  gamemap.appendChild(unitSpan);
  //closeMenu();
  return unitSpan;
}

})();
