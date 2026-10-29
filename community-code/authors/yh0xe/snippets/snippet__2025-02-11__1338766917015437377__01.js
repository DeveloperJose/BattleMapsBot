// ==UserScript==
// @name         AWBW Better Menu's Pos
// @namespace    https://awbw.amarriner.com/
// @version      2025-02-11
// @description  No more scrolling down!
// @author       yhaidar
// @match        https://awbw.amarriner.com/game.php?games_id=*
// @match        https://awbw.amarriner.com/moveplanner.php?*
// @icon         https://awbw.amarriner.com/favicon.ico
// @grant        unsafeWindow
// @run-at document-idle
// @license MIT
// ==/UserScript==

(function() {
    'use strict';
    var isReplay = unsafeWindow.location.toString().indexOf('&ndx=') > 0;
    var isMovePlanner = unsafeWindow.location.toString().indexOf('moveplanner') > 0;
    const optionsMenu = document.getElementById('options-menu');
    const buildMenu = document.getElementById('build-menu');
    const canvas = document.getElementById('map-background');

    const obsvBuildAndOptionsMenus = new MutationObserver((_mutations) => {
        //Make sure target damage preview does not exit the top of the screen
        const optionsMenu = document.getElementById('options-menu');
        const buildMenu = document.getElementById('build-menu');
        for (const e of [optionsMenu, buildMenu]) {
            if (parseFloat(e.style.top)) {
                const e_height = e.clientHeight; // + Math.floor(e.clientHeight * 0.3); // The scale is needed because Maximize script
                const e_bottom = e_height + parseFloat(e.style.top);
                if (e_bottom > canvas.height) {
                    let new_top = Math.floor(e.clientHeight * 0.3)+canvas.height-e.clientHeight;
                    if (e == optionsMenu) new_top -= 32 * 0.7; // Always account for city capture options
                    e.style.top = `${new_top}px`;
                }
            }
        }
    });
    if (isMovePlanner) {
        obsvBuildAndOptionsMenus.observe(optionsMenu, { attributes: true });
        obsvBuildAndOptionsMenus.observe(buildMenu, { attributes: true });
    }
})();
