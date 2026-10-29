function getMovementTiles(maxX, maxY, mType, mp, startTile, unitTeam, player) {
  var xv = [-1, 1, 0, 0];
  var yv = [0, 0, -1, 1];
  var nNodes = maxX * maxY;
  var visited = [];
  var dist = [];
  var previous = [];
  var mCost = [];

  for (var i = 0; i < nNodes; i++) {
    visited.push(false);
    dist.push(Infinity);
    previous.push(null);
    mCost.push(null);
  }

  var startNode = startTile.y * maxX + startTile.x;
  dist[startNode] = 0;
  var queue = new TinyQueue([], function (a, b) {
    return a.dist - b.dist;
  }); //Verification object to not include a tile twice

  var verif = {};
  var initial = {
    index: startNode,
    dist: 0,
    x: startTile.x,
    y: startTile.y
  };
  queue.push(initial);
  var tilesToDraw = [initial];
  verif[startNode] = 0;

  while (queue.length != 0) {
    var current = queue.pop();
    var index = current.index;
    var minValue = current.dist;
    var x = current.x;
    var y = current.y;
    visited[index] = true;
    delete verif[index];
    if (dist[index] < minValue) continue;

    for (var _i = 0; _i < 4; _i++) {
      var ax = x + xv[_i];
      var ay = y + yv[_i];
      var terrainCost = findTerrainCost(mType, ax, ay, unitTeam, player);
      var isBlackTile = checkBlackTile(ax, ay);
      if (ax < 0 || ay < 0 || ax >= maxX || ay >= maxY || !terrainCost && !isBlackTile) continue;
      var nextNodeIndex = ay * maxX + ax;
      mCost[nextNodeIndex] = terrainCost;
      if (visited[nextNodeIndex]) continue;

      if (terrainCost === "A" && !verif[nextNodeIndex]) {
        //Mark previous tile and skip to next iteration if attack is possible
        previous[nextNodeIndex] = index;
        verif[nextNodeIndex] = "A";
        continue;
      }

      var newDist = minValue + terrainCost;

      if (newDist < dist[nextNodeIndex] && newDist <= mp) {
        previous[nextNodeIndex] = index;
        dist[nextNodeIndex] = newDist;

        if (!verif[nextNodeIndex]) {
          queue.push({
            index: nextNodeIndex,
            dist: newDist,
            x: ax,
            y: ay
          });
          verif[nextNodeIndex] = newDist;
          tilesToDraw.push({
            index: nextNodeIndex,
            x: ax,
            y: ay
          });
        } else {
          for (var node in queue) {
            if (queue[node].index == nextNodeIndex) queue[node].dist = newDist;
          }
        }
      }
    }
  }

  var movementInfo = {
    dist: dist,
    previous: previous,
    mCost: mCost,
    mp: mp
  };
  var unitsInRange = []; //Object to prevent duplicates

  var unitsInRangeVerif = {};
  var minRange;
  var unitX;
  var unitY;

  if (currentClick) {
    minRange = currentClick.info.units_short_range;
    unitX = currentClick.info.units_x;
    unitY = currentClick.info.units_y;
  }

  tilesToDraw.forEach(function (tile) {
    var borderWidth = findBorders(tile.index, dist);
    drawMovementTile(tile.x, tile.y, borderWidth);
    if (borderWidth === "0 0 0 0 ") return;
    var newInRange = []; //Find units in range of attacker's extremities movement tiles

    if (minRange <= 1) {
      newInRange = findUnitsInRangeOf(tile.x, tile.y, currentClick.info);
    }

    if (newInRange.length !== 0) {
      newInRange.forEach(loopUnitsInRange);
    }
  });

  if (minRange > 1) {
    unitsInRange = findUnitsInRangeOf(unitX, unitY, currentClick.info);
  }

  if (unitsInRange.length !== 0) {
    createDamageSquares(currentClick.info, unitsInRange, movementInfo, true);
  }

  return movementInfo; //Check for duplicates

  function loopUnitsInRange(unit) {
    var unitId = unit.units_id;

    if (!unitsInRangeVerif[unitId]) {
      unitsInRange.push(unit);
      unitsInRangeVerif[unitId] = true;
    }
  }
} //look up terrain cost


function findTerrainCost(mType, x, y, unitTeam, player) {
  var _unitMap$x, _unitMap$x$y, _terrainInfo$x, _terrainInfo$x$y, _buildingsInfo$x, _buildingsInfo$x$y, _moveCosts$terrainId, _moveCosts$terrainId$;

  var coName = player.co_name;
  var power = player.players_co_power_on;
  var tempWCode = gameWeather.code;

  if (x > maxX - 1 || x < 0 || y < 0 || y > maxY - 1) {
    return null;
  } //Mark tile as A for tiles where there is an attackable unit


  var squareTeam = (_unitMap$x = unitMap[x]) === null || _unitMap$x === void 0 ? void 0 : (_unitMap$x$y = _unitMap$x[y]) === null || _unitMap$x$y === void 0 ? void 0 : _unitMap$x$y.team;

  if (squareTeam && squareTeam != unitTeam) {
    return "A";
  } //No penalty for Olaf in snow


  if (coName === "Olaf" && tempWCode === "S") {
    tempWCode = "C";
  } //Penalty for Olaf in rain 


  if (coName === "Olaf" && tempWCode === "R") {
    tempWCode = "S";
  } //No Penalty for Drake in rain


  if (coName === "Drake" && tempWCode === "R") {
    tempWCode = "C";
  }

  var terrainId = ((_terrainInfo$x = terrainInfo[x]) === null || _terrainInfo$x === void 0 ? void 0 : (_terrainInfo$x$y = _terrainInfo$x[y]) === null || _terrainInfo$x$y === void 0 ? void 0 : _terrainInfo$x$y.terrain_id) || ((_buildingsInfo$x = buildingsInfo[x]) === null || _buildingsInfo$x === void 0 ? void 0 : (_buildingsInfo$x$y = _buildingsInfo$x[y]) === null || _buildingsInfo$x$y === void 0 ? void 0 : _buildingsInfo$x$y.terrain_id);
  var mCost = (_moveCosts$terrainId = moveCosts[terrainId]) === null || _moveCosts$terrainId === void 0 ? void 0 : (_moveCosts$terrainId$ = _moveCosts$terrainId[tempWCode]) === null || _moveCosts$terrainId$ === void 0 ? void 0 : _moveCosts$terrainId$[mType]; //Black tile for no terrain id

  if (mCost === undefined) {
    return 0;
  }

  mCost = parseInt(mCost);

  if (mCost && tempWCode !== "S") {
    if (coName === "Sturm" || coName === "Lash" && power !== "N") {
      mCost = 1;
    }
  }

  return mCost;
} //If the tile is in neither terrainInfo or buildingsInfo, it's missing completely therefore is a black tile


function checkBlackTile(x, y) {
  var _terrainInfo$x2, _buildingsInfo$x2;

  var tileExists = ((_terrainInfo$x2 = terrainInfo[x]) === null || _terrainInfo$x2 === void 0 ? void 0 : _terrainInfo$x2[y]) || ((_buildingsInfo$x2 = buildingsInfo[x]) === null || _buildingsInfo$x2 === void 0 ? void 0 : _buildingsInfo$x2[y]);
  if (tileExists) return;
  return true;
}

function drawMovementTile(x, y, borderWidth) {
  var movementTile = document.createElement("span");
  movementTile.className = "movement-tile";
  applyCSS(movementTile, {
    borderStyle: function () {
      if (borderWidth !== "0 0 0 0 ") {
        return "solid";
      }
    }(),
    borderWidth: borderWidth,
    left: x * 16 + -1 + "px",
    top: y * 16 + -1 + "px"
  }); //use fragment

  gamemap.appendChild(movementTile);
}

function drawPathTiles(movementInfo, x, y) {
  var newPath = arguments.length > 3 && arguments[3] !== undefined ? arguments[3] : [];
  //Reset path
  var pathTiles = [].slice.call(document.querySelectorAll("span[class^='path-tile']"));
  pathTiles.forEach(function (tile) {
    tile.parentElement.removeChild(tile);
  });
  var targetNode = y * maxX + x;
  var tileCount = newPath.length;
  var prevNode = newPath[tileCount - 1];
  var prevX = prevNode % maxX;
  var prevY = (prevNode - prevX) / maxX; //Distance between the last 2 tiles

  var distance = Math.abs(y - prevY) + Math.abs(x - prevX);
  var nodeIndex = newPath.indexOf(targetNode);
  var movementDist = movementInfo.dist;
  var movementCosts = movementInfo.mCost;
  var mp = movementInfo.mp;
  var targetDist = movementDist[targetNode];
  var totalDistance = 0; //Calculate total distance of given path and add cost of target tile

  newPath.forEach(function (tile, i) {
    //Skip initial tile
    if (i === 0) return;
    totalDistance += movementCosts[tile];
  });
  totalDistance += movementCosts[targetNode];

  if (distance === 1 && !newPath.includes(targetNode) && targetDist !== Infinity && totalDistance <= mp) {
    //Cursor is adjacent to another path tile and total distance is less than mp
    newPath.push(targetNode);
  } else if (newPath.includes(targetNode)) {
    //Case for backtracking
    if (nodeIndex === -1) nodeIndex = 0;
    newPath.splice(nodeIndex + 1);
  } else if (distance !== 1 && targetDist === Infinity || targetDist !== Infinity) {
    //Cursor is not adjacent to another path tile
    newPath = findShortestPath(movementInfo, targetNode);
  }

  newPath.forEach(drawPath);
  return newPath;

  function drawPath(tile, i) {
    if (i === 0) return;
    var pathTile = document.createElement("span");
    pathTile.className = "path-tile";
    var prevTile = newPath[i - 1];
    var nextTile = newPath[i + 1];
    var arrow = findArrowDirection(prevTile, tile, nextTile);
    var tileX = tile % maxX;
    var tileY = (tile - tileX) / maxX;
    applyCSS(pathTile, {
      background: "url('terrain/arrow_" + arrow.arrow + ".gif')",
      left: tileX * 16 + "px",
      top: tileY * 16 + "px",
      transform: "rotate(" + arrow.rotation + "deg)"
    });
    gamemap.appendChild(pathTile);
  }
}

function findShortestPath(solved, end) {
  var dist = solved.dist,
      previous = solved.previous;
  var path = []; //Case where target tile is an enemy unit

  if (dist[end] === Infinity && previous[end]) end = previous[end];
  if (dist[end] === Infinity) return path;

  for (var i = end; i !== null; i = previous[i]) {
    path.push(i);
  }

  return path.reverse();
}

function findBorders(node, dist) {
  var borderWidth = "";
  borderWidth += dist[node - maxX] != Infinity ? "0 " : "1px ";
  borderWidth += dist[node + 1] != Infinity ? "0 " : "1px ";
  borderWidth += dist[node + maxX] != Infinity ? "0 " : "1px ";
  borderWidth += dist[node - 1] != Infinity ? "0 " : "1px ";
  return borderWidth;
}

function findArrowDirection(prevNode, targetNode, nextNode) {
  var rotations = {
    left: {
      up: 0,
      down: 270
    },
    up: {
      left: 0,
      right: 90
    },
    right: {
      up: 90,
      down: 180
    },
    down: {
      right: 180,
      left: 270
    }
  };
  var tipRotations = {
    right: 90,
    down: 180,
    left: 270,
    up: 0
  };
  var prevDiff = targetNode - prevNode; // 1

  var absPrevDiff = Math.abs(prevDiff);
  var nextDiff;
  var absNextDiff;

  if (nextNode !== undefined) {
    nextDiff = targetNode - nextNode; // -19

    absNextDiff = Math.abs(nextDiff);
  } else {
    //End of path
    var tipDirection = findDirection(prevDiff);
    return {
      arrow: "tip",
      rotation: tipRotations[tipDirection]
    };
  }

  if (absNextDiff !== absPrevDiff && prevNode !== undefined) {
    //Arrow turns
    var prevDirection = findDirection(prevDiff);
    var nextDirection = findDirection(nextDiff);
    var arrowRotation = rotations[prevDirection][nextDirection];
    return {
      arrow: "curve",
      rotation: arrowRotation
    };
  } //Straight arrow


  var arrow = {
    arrow: "line",
    rotation: 0
  };

  if (absPrevDiff === 1) {
    arrow.rotation = 90;
  }

  return arrow;
} //Find direction for unit/arrow tip


function findDirection(diff) {
  if (diff > 1) return "up";else if (diff === -1) return "right";else if (diff === 1) return "left";else return "down";
}