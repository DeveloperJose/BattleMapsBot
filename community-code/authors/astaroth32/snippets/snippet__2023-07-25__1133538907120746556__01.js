// ==UserScript==
// @name             AWBW Stats Mover ChatGPT
// @match            https://awbw.amarriner.com/2030.php*
// @run-at           document-end
// @grant            none
// @version          1.0
// ==/UserScript==


//class="end-game-screen confirmation-screen" //whole opup (including X button etc.)
//class="end-game-overview end-game-tab" //only the stats window
//class="end-game-nav" //X button, Overview, and Stats navigation-bar

// Your CSS as text
const styles = `.game-stats-units-list li {
  display: unset;
}
`;

const styleSheet = document.createElement("style");
styleSheet.innerText = styles;
document.head.appendChild(styleSheet);

fetchStatsInfo(currentStatsPId);
const statsWindow = document.getElementsByClassName("game-stats end-game-tab")[0];

document.getElementById('gamemap-container').appendChild(statsWindow);

statsWindow.style.width="200px";
statsWindow.style.top="-2px";

statsWindow.style.display="flex";
statsWindow.style.position="absolute";

let statsWindowWidth = statsWindow.clientWidth;

statsWindow.style.left=statsWindowWidth * -1 -8 + "px";
