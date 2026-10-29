// ==UserScript==
// @name             AWBW 2 Columns Build Menu
// @match            https://awbw.amarriner.com/game.php?games_id=*
// @inject-into      page
// @version          1.2
// ==/UserScript==

const el_buildOptionsGame = document.getElementsByClassName("build-options-game")[0];
const el_ul = el_buildOptionsGame.getElementsByTagName("ul")[0];


const copyBorderColor = el_ul.style.borderColor;

el_buildOptionsGame.style.cssText +=";" + "width: fit-content;height: auto;margin: unset;padding: 4px;border: solid 2px;" + "border-color: " + copyBorderColor + ";";
el_ul.style.cssText +=";" + "column-count: 2;column-gap: 4px;border-width: 2px;border-width: 2px;padding: 1px;margin: unset;border: unset;";
//document.getElementsByClassName("build-options-game")[0].getElementsByTagName("ul")[0].getElementsByTagName("li").style.cssText +=";" + "display: inline-flex;margin: 1px 0;padding: 0px;width: 160px;break-inside: avoid;";

document.head.appendChild(document.createElement("style")).sheet.insertRule(".build-options-game > ul > li {display: inline-flex;margin: 1px 0;padding: 0px;width: 160px;break-inside: avoid;}");