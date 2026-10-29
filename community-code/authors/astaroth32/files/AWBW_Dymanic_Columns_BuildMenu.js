// ==UserScript==
// @name             AWBW Dynamic 2 Columns Build Menu
// @match            https://awbw.amarriner.com/game.php?games_id=*
// @version          2.0
// ==/UserScript==

const el_buildOptionsGame = document.getElementsByClassName("build-options-game")[0];
const el_ul = el_buildOptionsGame.getElementsByTagName("ul")[0];

let liElements = el_ul.getElementsByTagName("li");

const copyBorderColor = el_ul.style.borderColor;

el_buildOptionsGame.style.cssText +=";" + "width: fit-content;height: auto;margin: unset;padding: 4px;border: solid 2px;" + "border-color: " + copyBorderColor + ";";
el_ul.style.cssText +=";" + "column-count: 2;column-gap: 4px;border-width: 2px;border-width: 2px;padding: 1px;margin: unset;border: unset;";
//document.getElementsByClassName("build-options-game")[0].getElementsByTagName("ul")[0].getElementsByTagName("li").style.cssText +=";" + "display: inline-flex;margin: 1px 0;padding: 0px;width: 160px;break-inside: avoid;";

document.head.appendChild(document.createElement("style")).sheet.insertRule(".build-options-game > ul > li {display: inline-flex;margin: 1px 0;padding: 0px;width: 160px;break-inside: avoid;}");



// Options for the observer (which mutations to observe)
const config = { attributes: true, childList: false, subtree: false };

// Callback function to execute when mutations are observed
const callback = (mutationList, observer) => {
  for (const mutation of mutationList) {
    if (mutation.type === "attributes") {
      console.log(`The ${mutation.attributeName} attribute was modified.`);
      observer.disconnect();
      if (el_buildOptionsGame.style.getPropertyValue("display") !== ("block"))
      //if (optionsMenu.getAttribute("style").slice(0,15) !== "display: block;") //previous way
        {console.log("Not blocked");
         observer.observe(el_buildOptionsGame, config);
         break;
        }
      else {
        console.log(el_buildOptionsGame.getAttribute("style").slice(0,15));

        //update nodelist (find out how many li elements there are, i.e. units in build menu)
        liElements = el_ul.getElementsByTagName("li");
        if (liElements.length > 7) {
          //el_ul.style.columnCount = 2;
          el_ul.style.display = "block";
        }
        else {
          //el_ul.style.columnCount = 1;
          el_ul.style.display = "Flex";
          el_ul.style.flexDirection = "column";
        }
        console.log(el_ul.style.columnCount);
      }
      observer.observe(el_buildOptionsGame, config);
      break;
    }
  }
};

// Create an observer instance linked to the callback function
const observer = new MutationObserver(callback);

// Start observing the target node for configured mutations
observer.observe(el_buildOptionsGame, config);
console.log(el_buildOptionsGame);