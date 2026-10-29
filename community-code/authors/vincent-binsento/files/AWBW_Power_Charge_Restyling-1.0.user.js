// ==UserScript==
// @name         AWBW Power Charge Restyling
// @namespace    http://tampermonkey.net/
// @license      MIT
// @version      1.0
// @description  Intuitively changes the colour of the power charge bars
// @author       Ｖｉｎｃｅｎｔ ～ VIH & T. Didy
// @match        https://awbw.amarriner.com/game.php*
// @icon         https://www.warsworldnews.com/aw/images/icons/power.png
// @grant        none
// ==/UserScript==

(function() {
    'use strict';

document.styleSheets[0].insertRule(".anim-power-bar { animation-iteration-count: 0;}", 0);
// ???


 document.styleSheets[0].insertRule(".cop-star.anim-power-bar .power-star-percent { background: rgb(255 79 78 / 60%); border-top: 3px solid rgb(146 50 67 / 90%); border-bottom: 3px solid rgb(146 50 67 / 90%);}", 0);
// rgb(255 79 78 / 60%)  &  rgb(146 50 67 / 90%)
// https://cdn.discordapp.com/emojis/852953743343616060.webp

 document.styleSheets[0].insertRule(".scop-star.anim-power-bar .power-star-percent { background: rgb(157 175 218 / 60%); border-top: 3px solid rgb(55 104 167 / 90%); border-bottom: 3px solid rgb(55 104 167 / 90%);}", 0);
// rgb(157 175 218 / 60%)  &  rgb(55 104 167 / 90%)
// https://cdn.discordapp.com/emojis/852953758857953342.webp


})();