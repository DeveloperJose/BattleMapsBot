// ==UserScript==
// @name         AWBW Change army direction
// @namespace    https://awbw.amarriner.com/
// @version      1.02
// @description  Swap the direction of a player's army by double clicking the army header.
// @author       Truniht
// @match        https://awbw.amarriner.com/*?games_id=*
// @match        https://awbw.amarriner.com/*?replays_id=*
// @icon         https://awbw.amarriner.com/favicon.ico
// @grant        GM_setValue
// @grant        GM_getValue
// @license      MIT
// ==/UserScript==

(function() {
    //Fetch settings
    var gameID = window.location.href.match(/_id=([0-9]+)/)[1];
    var settings = GM_getValue('AWBWMirrorSettings' + gameID) || {};

    //Have to use a function to get the local variable as it can't be accessed directly
    unsafeWindow.AWBWMirrorReturnPlayers = function () {return playersUnits;}

    function saveSettings() {
        GM_setValue('AWBWMirrorSettings' + gameID, settings);
    }

    function createSwapFunction(playerID) {
        return function() {
            tap(undefined, function() {
            if (settings[playerID]) delete settings[playerID];
            else settings[playerID] = 1;
            saveSettings();
            swapColours(true, playerID);
            });
        }
    }

    var doubletapDeltaTime_ = 700;
    var doubletap1Function_ = null;
    var doubletap2Function_ = null;
    var doubletapTimer_ = null;

    function tap(singleTapFunc, doubleTapFunc) {
        if (doubletapTimer_==null) {
            // First tap, we wait X ms to the second tap
            doubletapTimer_ = setTimeout(doubletapTimeout_, doubletapDeltaTime_);
            doubletap1Function_ = singleTapFunc;
            doubletap2Function_ = doubleTapFunc;
        } else {
            // Second tap
            clearTimeout(doubletapTimer_);
            doubletapTimer_ = null;
            doubletap2Function_();
        }
    }

    function doubletapTimeout_() {
        // Wait for second tap timeout
        if (doubletap1Function_) {
            doubletap1Function_();
            doubletapTimer_ = null;
        }
    }

    var swapInProgress = false;
    function swapColours(force, removeID) {
        if (swapInProgress && !force) return;
        swapInProgress = true;
        try {
            var playersUnits = unsafeWindow.AWBWMirrorReturnPlayers();
            var playerID;
            for(playerID in playersUnits) {
                if (document.getElementById('player'+playerID)) {
                    //Update the header colour
                    var playerHeader = document.getElementById('player'+playerID).querySelector('header');
                    if (playerHeader && !playerHeader.dataApplied) {
                        playerHeader.onclick = createSwapFunction(playerID);
                        playerHeader.dataApplied = true;
                    }
                }

                if (settings[playerID] || removeID) {
                    for(var unitID in playersUnits[playerID]) {
                        var unitImage = document.querySelector('span[data-unit-id="' + unitID + '"] .sprite');
                        unitImage.style.transform = settings[playerID] ? 'scaleX(-1)' : '';
                    }
                }
            }
        } catch (e) {}
        swapInProgress = false;
    }

    const observer = new MutationObserver(function() {swapColours();});
    observer.observe(document, { childList: true, subtree: true, attributes: true });

    window.addEventListener('load', function() {swapColours(true);});
})();