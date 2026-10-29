// ==UserScript==
// @name             AWBW Menu Mover
// @match            https://awbw.amarriner.com/moveplanner.php*
// @version          1.0
// ==/UserScript==


// Select the node that will be observed for mutations
//const targetNode = document.getElementById("build-menu");
const targetNode = document.getElementById("options-menu");

// Options for the observer (which mutations to observe)
const config = { attributes: true, childList: false, subtree: false };

// Callback function to execute when mutations are observed
const callback = (mutationList, observer) => {
  for (const mutation of mutationList) {
    if (mutation.type === "attributes") {
      console.log(`The ${mutation.attributeName} attribute was modified.`);
      observer.disconnect();
      if (targetNode.getAttribute("style").slice(0,15) !== "display: block;")
        {console.log("Not blocked");
         observer.observe(targetNode, config);
         break;
        }
      else {
        let coord_y1 = ((window.screen.availHeight + window.scrollY) / window.screen.availHeight);
        console.log(targetNode.getAttribute("style").slice(0,15));
        console.log(parseInt(menu.style.top));
        //console.log(parseInt("build-menu".style.top));
        if (parseInt(menu.style.top) < 150 * coord_y1) {
          console.log("position = " + String(coord_y1));
          applyCSS(menu, {
          //display: "block",
          //left: parseInt(menu.style.left) + 0 + "px",
          top: parseInt(menu.style.top) + 66 + "px"
        });
        }
        else {console.log("Too close to the bottom of the screen! (" + String(coord_y1) + ")");}
        applyCSS(menu, {
          //display: "block",
          //left: parseInt(menu.style.left) + 0 + "px",
          top: parseInt(menu.style.top) - 66 + "px"
        }); }
      observer.observe(targetNode, config);
      break;
    }
  }
};

// Create an observer instance linked to the callback function
const observer = new MutationObserver(callback);

// Start observing the target node for configured mutations
observer.observe(targetNode, config);
