// ==UserScript==
// @name         AWBW Pre-Follow Games
// @namespace    http://tampermonkey.net/
// @version      0.1
// @description  Adds a button to pre-follow games that haven't started yet.
// @author       TheGamerASD
// @match        https://awbw.amarriner.com/gameswait.php?games_id=*
// @match        https://awbw.amarriner.com/join.php?games_id=*
// @icon         https://awbw.amarriner.com/terrain/favemaps.gif
// @grant        none
// ==/UserScript==

(function () {
    "use strict";

    function getCookie(name) {
        const value = `; ${document.cookie}`;
        const parts = value.split(`; ${name}=`);
        if (parts.length === 2) return parts.pop().split(';').shift();
    }

    let extStorage = JSON.parse(localStorage.getItem("awbw-ext-pfg") || "{}");
    let username = getCookie("awbw_username");

    if(!extStorage.hasOwnProperty(username))
    {
        extStorage[username] = {};
        extStorage[username].games = [];
    }

    let gameID = window.location.href.split("=")[1].replace("#", "");
    let gameFollowed = extStorage[username].games.includes(gameID);
    let clickID = "";

    if(window.location.href.includes("gameswait.php"))
    {
        let doGameRowContainer = document.getElementById("do-game-row-container");
        let div = document.createElement("div");

        div.setAttribute("class", "game-tools-btn");
        div.setAttribute("style", "width: 205px; height: 24px; margin-left: 5px; border: none;");

        div.innerHTML = `<div class=\"game-tools-bg\">
<a class=\"norm2\" id=\"pre-follow-button\" href=\"#\" style=\"height: 100%; display:block;\">
<img style=\"margin-top: 3px; vertical-align: top;\" src=\"terrain/favemaps.gif\">
<span class=\"small_text\" style=\"display: inline-block; margin-top: 3px; vertical-align: top;\"><b id=\"pre-follow-text\">${(gameFollowed ? "Unfollow Game" : "Pre-Follow Game")}</b>             </span>
</a>
</div>`;

        doGameRowContainer.appendChild(div);
        clickID = "pre-follow-button";
    }
    else
    {
        let linkSpan = document.getElementById("join_game").getElementsByTagName("span")[0];
        let a = document.createElement("a");
        a.setAttribute("class", "bordertitle");
        a.setAttribute("href", "#");
        a.setAttribute("id", "pre-follow-text");
        a.textContent = gameFollowed ? "[Unfollow Game] " : "[Pre-Follow Game] ";
        linkSpan.insertBefore(a, linkSpan.children[0]);
        clickID = "pre-follow-text";
    }
    let preFollowText = document.getElementById("pre-follow-text");

    let setText;

    if(window.location.href.includes("gameswait.php"))
    {
        setText = (text) => {
            preFollowText.textContent = text;
        }
    }
    else
    {
        setText = (text) => {
            preFollowText.textContent = "[" + text + "] ";
        }
    }


    document.getElementById(clickID).onclick = async function () {
        let result = await $.post("check_following.php", "games_id=" + gameID);

        if(gameFollowed)
        {
            setText("Pre-Follow Game");
            extStorage[username].games.pop(gameID);
        }
        else
        {
            setText("Unfollow Game");
            extStorage[username].games.push(gameID);
        }

        gameFollowed = !gameFollowed;
        localStorage.setItem("awbw-ext-pfg", JSON.stringify(extStorage));
    }
})();