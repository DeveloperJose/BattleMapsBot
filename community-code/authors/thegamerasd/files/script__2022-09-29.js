// ==UserScript==
// @name         Redirect To Game
// @namespace    http://tampermonkey.net/
// @version      0.1
// @description
// @author       TheGamerASD
// @match        https://awbw.amarriner.com/*
// @icon         https://www.google.com/s2/favicons?sz=64&domain=awbw.amarriner.com
// @grant        none
// ==/UserScript==

(function () {
  "use strict";

  if (window.location.href.startsWith("https://awbw.amarriner.com/gameswait.php?games_id=") && document.getElementById("main").children[0].textContent.includes("Invalid game ID! You will be")) {
    let id = window.location.href.split("=")[1];
    window.location.href = "https://awbw.amarriner.com/2030.php?games_id=" + id;
  }
})();