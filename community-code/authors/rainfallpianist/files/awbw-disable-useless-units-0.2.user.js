// ==UserScript==
// @name         AWBW Disable useless units
// @namespace    awbw
// @match        https://awbw.amarriner.com/game.php*
// @icon         https://awbw.amarriner.com/terrain/aw2/osmissile.gif
// @version      0.2
// @description  Never build useless units again! Except naval units, you can still accidentally build those.
// @author       steve, DevJ
// @license      MIT
// @grant        none
// @inject-into  page
// ==/UserScript==
(function () {
const hidden_units = ['Piperunner','Missile'];

let showBuildOptionsOld = showBuildOptions;
showBuildOptions = function(x, y) {
    showBuildOptionsOld(x, y);
    document.querySelectorAll('.build-options-game li').forEach(li => {
        let unitName = li.textContent;
        if(hidden_units.some(u => unitName.includes(u))) {
            li.remove();
        }
    });
}
})();