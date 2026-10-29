// ==UserScript==
// @name             2 Column Build Menu (JS)
// @match            https://awbw.amarriner.com/game.php?games_id=*
// @inject-into      page
// @version          1.1
// ==/UserScript==

document.getElementsByClassName("build-options-game")[0].style.cssText +=";" + "width: fit-content;height: auto;margin: unset;padding: 4px;border: solid 2px;";
document.getElementsByClassName("build-options-game")[0].getElementsByTagName("ul")[0].style.cssText +=";" + "column-count: 2;column-gap: 4px;border-width: 2px;border-width: 2px;padding: 1px;margin: unset;border: unset;";
document.head.appendChild(document.createElement("style")).sheet.insertRule(".build-options-game > ul > li {display: inline-flex;margin: 1px 0;padding: 0px;width: 160px;break-inside: avoid;}");
