// ==UserScript==
// @name         AWBW capture limit
// @version      1.00
// @description  Calculate the capture limit and show it on player elements
// @author       Truniht
// @match        https://awbw.amarriner.com/game.php?games_id=*
// @icon         https://awbw.amarriner.com/terrain/ani/neutralcity.gif
// @namespace    https://awbw.amarriner.com/
// @license MIT
// ==/UserScript==

(function() {
    'use strict';
    var cities = document.querySelectorAll('.game-building>img:first-child[src*="city"]');
    var cityIds = [];
    for(var city of cities) cityIds.push(city.parentNode.getAttribute('data-building-id') * 1);
    var captureLimit = document.querySelectorAll('#showinfo td')[22].innerText * 1;
    if (isNaN(captureLimit)) captureLimit = 0;

    if (captureLimit) {
        var playerOverviews = document.querySelectorAll('.player-overview-container');
        var playerTables = {};
        for(var playerO of playerOverviews) {
            var ul = playerO.querySelector('.player-overview-info ul');
            var li = document.createElement('li');
            li.innerText = '0/' + captureLimit;
            li.style.justifyContent = 'end';
            ul.appendChild(li);
            playerTables[playerO.id.split('player')[1]] = li;
        }

        setInterval(function() {
            var playerProperties = {};
            var b = buildingsInfo;
            for(var i in b) {
                for(var z in b[i]) {
                    var building = b[i][z];
                    if (building.buildings_players_id && cityIds.includes(building.buildings_id)) {
                        playerProperties[building.buildings_players_id] = (playerProperties[building.buildings_players_id] || 0) + 1;
                    }
                }
            }
            for(var playerID in playerTables) {
                playerTables[playerID].innerText = (playerProperties[playerID] || 0) + '/' + captureLimit;
            }
        }, 1000);
    }
})();