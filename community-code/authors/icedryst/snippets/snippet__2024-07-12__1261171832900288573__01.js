
// ==UserScript==
// @name         AWBW Fighting Potato
// @namespace    http://tampermonkey.net/
// @version      2024-07-12
// @description  Take away your opponent's Conqueror Haki
// @author       IceDryst
// @match        https://awbw.amarriner.com/game.php?*
// @icon         https://www.google.com/s2/favicons?sz=64&domain=amarriner.com
// @grant        none
// ==/UserScript==

(function() {
    'use strict';
    const your_name = document.getElementById("profile-menu").children[0].innerText;
    const username_nodes = Array.from(document.querySelectorAll("[class*=player-username"));
    const enemies_text_nodes = username_nodes.map((x) => {return x.childNodes[1];}).filter((x)=>{return !x.text.includes(your_name);})

    if (username_nodes.length == 2 && username_nodes.length != enemies_text_nodes.length){
        const enemy_node = enemies_text_nodes[0];
        enemy_node.text = "Potato" + Math.floor(Math.random()*100);
        console.log(enemy_node);
    }
    // Your code here...
})();
