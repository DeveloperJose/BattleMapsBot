// ==UserScript==
// @name         AWBW Acid Rain Brighter Sprites
// @description  Changes the Acid Rain sprites from Advance Wars by Web to be easier to recognize
// @namespace    .xyz.ishygddt
// @author       squeegily
// @version      0.1
// @icon         https://awbw.amarriner.com/terrain/aw1/arinfantry.gif
// @grant        GM.addStyle
// @match        https://awbw.amarriner.com/*?games_id=*
// @match        https://awbw.amarriner.com/*?replays_id=*
// @require      https://greasemonkey.github.io/gm4-polyfill/gm4-polyfill.js
// @run-at       document-start
// ==/UserScript==

GM.addStyle(`
img[src*="/acidrain"] {
    filter: saturate(1.5);
}
img[src*="/ar"] {
    filter: brightness(1.125) saturate(1.25);
}
`);
