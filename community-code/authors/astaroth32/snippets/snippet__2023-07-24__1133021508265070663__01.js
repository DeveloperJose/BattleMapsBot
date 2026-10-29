  function swapStats(store, storeValue) {
    var statCountSpans = document.querySelectorAll(".game-stats-unit-count");
    var unitLi = document.querySelectorAll(".game-stats-units-list li");
    var storeKeys = Object.keys(store);
    gameStatsKillDeathValue.textContent = storeValue + " G.";

    for (var i = 0; i < statCountSpans.length; i++) {
      var _unitCount3 = store[storeKeys[i]];
      statCountSpans[i].textContent = "x " + _unitCount3;
      unitLi[i].style.display = _unitCount3 !== 0 ? "flex" : "none";
    }
  }