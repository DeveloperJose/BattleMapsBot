// ==UserScript==
// @name        AWBW Tag Colors
// @version     1.0.0
// @icon        https://awbw.amarriner.com/terrain/aw1/osinfantry.gif
// @author      TheGamerASD
// @description Adds colors for tags on AWBW.
// @match       https://awbw.amarriner.com/*
// @grant       none
// ==/UserScript==

(function() {
    'use strict';

    function colorTags()
    {
        function setColor(category, color)
        {
            categories.filter(c => c.textContent === category).forEach(c => c.style.color = color);
        }

        var categories = Object.values(document.querySelectorAll("a")).filter(a => a.href.includes("categories"));

        setColor("S-Rank", "green");
        setColor("A-Rank", "goldenrod");
        setColor("B-Rank", "#1083bb");
        setColor("C-Rank", "salmon");
        setColor("New", "cornflowerblue");

        setColor("Global League", "darkorchid");
        setColor("Hall of Fame", "red");
        setColor("Historical/Geographical", "sandybrown");
        setColor("Joke", "skyblue");
        setColor("Sprite", "royalblue");
        setColor("Toy-Box", "lawngreen");
        setColor("Under Review", "#FF8000");

        setColor("Base Light", "gray");
        setColor("FFA Multiplay", "gray");
        setColor("Fog of War", "gray");
        setColor("Standard", "gray");
        setColor("Heavy Naval", "gray");
        setColor("High Funds", "gray");
        setColor("Gimmick", "gray");
        setColor("Live Play", "gray");
        setColor("Mixed Base", "gray");
        setColor("Team Play", "gray");
        setColor("Teleport Tile", "gray");
    }

    window.colorTags = colorTags;
    window.colorTags();
})();