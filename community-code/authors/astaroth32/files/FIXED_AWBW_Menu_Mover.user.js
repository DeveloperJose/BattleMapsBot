// ==UserScript==
// @name             FIXED AWBW Menu Mover
// @match            https://awbw.amarriner.com/2030.php*
// @match            https://awbw.amarriner.com/moveplanner.php*
// @version          1.2
// ==/UserScript==

function applyCSS(el, styles) {
  for (var prop in styles) {
    el.style[prop] = styles[prop];
  }
}

console.log("What is the URL?");

//const sentence = 'https://awbw.amarriner.com/moveplanner.php?games_id=975234';
const pageUrl = String(document.location);
console.log("The URL is: " + pageUrl);
const word = 'moveplanner.php?';
const word2 = '2030.php?games_id';

console.log(`The word "${word}" ${pageUrl.includes(word) ? 'is' : 'is not'} in the sentence`);
console.log(`The word "${word2}" ${pageUrl.includes(word2) ? 'is' : 'is not'} in the sentence`);

//const bannerheight = 0;
//how much extra space (height) gets taken up by AWBW banner, gamename, timer, etc. above game map (word2 == real game, not move planner)
let bannerheight = 0;
if (pageUrl.includes(word2)) {
  console.log("HELLOOO");
  bannerheight = 225; //245 px
}

let mouse_Y = 0;
//ScreenAvailHeight - itemCount * itemSize > GetMouseY
addEventListener("mousemove", (event) => {
  mouse_Y = event.clientY;
  //console.log("mouse_Y: " + String(mouse_Y));
  //console.log("mouse_Y: " + String(mouse_Y) + " -> " + String(mouse_Y - (mouse_Y % 32)) );
  //console.log("mouse_Y: " + String(mouse_Y) + " -> " + String(mouse_Y - (mouse_Y % 16*scaleZoom)) );
});

// Select the node that will be observed for mutations
//const buildMenu = document.getElementById("build-menu"); //Move PLanner
//const optionsMenu = document.getElementById("options-menu"); //Move Planner Only

//const unitOptionsMenu = document.getElementsByClassName("unit-options-game")[0]; //Move/Attack/Capture menu for unit in active game

// Options for the observer (which mutations to observe)
const config = { attributes: true, childList: false, subtree: false };

// variable how scaled the map size is
let scaleZoom = 1;


//menuScaling: whether the build/options menus scale with the AWBW zoom function (only Move Planner does for some reason)
//function observerCreation(optionsMenu, pxMove) {
function observerCreation(optionsMenu, menuScaling) {
  // Callback function to execute when mutations are observed
  const callback = (mutationList, observer) => {
    for (const mutation of mutationList) {
      if (mutation.type === "attributes") {
        console.log(`The ${mutation.attributeName} attribute was modified.`);
        observer.disconnect();
        if (optionsMenu.style.getPropertyValue("display") !== ("block"))
        //if (optionsMenu.getAttribute("style").slice(0,15) !== "display: block;") //previous way
          {console.log("Not blocked");
           observer.observe(optionsMenu, config);
           break;
          }
        else {
          //check current scale up the map size is
          //scaleZoom = parseInt(document.getElementById("gamemap").style.getPropertyValue("transform").getPropertyValue("scale"));
          scaleZoom = Number(document.getElementById("gamemap").style.getPropertyValue("transform").slice(6,-1));
          console.log("scaleZoom = " + scaleZoom);
          if (scaleZoom !== isNaN) {
            console.log("why??? scaling is bugged");
          }
          else {
            console.log("scaling working");
          }

          //how far down the page scrolled compared to how big the screen is
          //let coord_y1 = ((window.screen.availHeight + window.scrollY) / window.screen.availHeight);
          let scroll_y = parseInt(window.scrollY);

          console.log("scroll_y = " + String(scroll_y));
          console.log("bannerheight = " + String(bannerheight));
          if (bannerheight - scroll_y > 0) {
            console.log("Banner is wasting " + String(bannerheight - scroll_y) + "px");
            bannerheight = bannerheight - scroll_y;
          }
          else {
            console.log("Scrolled down enough for banner to not be seen");
            bannerheight = 0;
          }
          console.log("bannerheight is now = " + String(bannerheight));

          console.log(optionsMenu.getAttribute("style").slice(0,15));
          console.log("map position = " + parseInt(optionsMenu.style.top));
          console.log("map position (non-scaled) = " + parseInt(optionsMenu.style.top)/scaleZoom);

          console.log("screen.availHeight: " + String(window.screen.availHeight));
          console.log("Height: " + String(window.screen.height));
          console.log("window.innerHeight: " + String(window.innerHeight));
          console.log("scrollY: " + String(window.scrollY));
          console.log("sceenY: " + String(window.screenY));

          //how many items there are in the menu (number of units in build menu or actions in unit options. div > ul > li li li li etc.)
          //let countItems = optionsMenu.ul[0].childElementCount;
          let countItems = optionsMenu.firstElementChild.childElementCount;
          console.log("There are " + parseInt(countItems) + " children (number of li elements aka. items)");

          console.log("position (top): " + parseInt(optionsMenu.style.top));

          //Slightly scuffed because of extra distance from top of screen
          //mouse_Y - topOfScren_to_GameContainer
          console.log("mouse_Y: " + String(mouse_Y) + " -> " + String(mouse_Y - (mouse_Y % (16*scaleZoom) )) );
          //new_mouse_Y = mouse_Y + topOfScren_to_GameContainer

          //omfg I should obviously be using screen available height to decide... later...
          //or ideally if I could figure out where on the screen the cursor is located...
          //console.log("Build/Move Menu height (pxMove * countItems): " + String(pxMove * countItems) );
          //console.log("Where on screen: " + String(window.innerHeight - (pxMove * countItems)) );

          //uhh why do I not just check the height of the build/options menu...
          console.log("Build/Options menu height (offsetHeight): " + String(optionsMenu.offsetHeight));
          console.log("Build/Options menu height (offsetHeight), with scaling: " + String(optionsMenu.offsetHeight * scaleZoom));

          let menuScalingScaler = 1;

          //When to make the build/unit options menu go upwards instead of downwards:
          if (menuScaling) { //menuScaling === true -> it's move planner (use scaleZoom)
            console.log("menuScaling = " + String(menuScaling) + "(should say true -> move planner)");
            menuScalingScaler = scaleZoom;
          }
          else {
            console.log("menuScaling = " + String(menuScaling) + "(should say false -> real game, not move planner)");
          }
          if ( (mouse_Y - ((mouse_Y - bannerheight) % 16*scaleZoom)) + (optionsMenu.offsetHeight/2)*menuScalingScaler <= window.innerHeight && ( (mouse_Y - ((mouse_Y - bannerheight) % 16*menuScalingScaler)) + optionsMenu.offsetHeight*menuScalingScaler > window.innerHeight ) ) {
            applyCSS(optionsMenu, {
              //display: "block",
              //left: parseInt(menu.style.left) + 0 + "px",
              top: parseInt(optionsMenu.style.top) + 16 - (optionsMenu.offsetHeight/2) + "px" //This moves the menus up halfway
              });
            console.log("Middle of screen");
          }
          else if ( (mouse_Y - ((mouse_Y - bannerheight) % 16*menuScalingScaler)) + optionsMenu.offsetHeight*menuScalingScaler > window.innerHeight && window.screen.availHeight - (mouse_Y - ((mouse_Y - bannerheight) % 16*menuScalingScaler)) < optionsMenu.offsetHeight*menuScalingScaler ) {
            applyCSS(optionsMenu, {
            //display: "block",
            //left: parseInt(menu.style.left) + 0 + "px",
            top: parseInt(optionsMenu.style.top) + 16 - optionsMenu.offsetHeight + "px" //This moves the menus up completely
            });
            console.log("Low down on screen (Move Up)");
            console.log("availHeight = " + window.screen.availHeight);
            //console.log("mouseY = " + (mouse_Y - ((mouse_Y - bannerheight) % 16*menuScalingScaler)) > optionsMenu.offsetHeight*menuScalingScaler)
          }
          else {
            console.log("High up on screen (do nothing -> default drop down)");
          }
        }
        observer.observe(optionsMenu, config);
        break;
      }
    }
  };

  // Create an observer instance linked to the callback function
  const observer = new MutationObserver(callback);

  // Start observing the target node for configured mutations
  observer.observe(optionsMenu, config);
  console.log(optionsMenu); //I actually never see this
}

document.getElementById("fixed-header-wrapper").style.zIndex=500;

//Move Planner Only //for some reason if both game and move planner mutation observers are on at the same time then script doesn't work
if (pageUrl.includes(word)) {
  observerCreation(document.getElementById("build-menu"), true); //menuScaling = true is because only Move Planner has menu sizes that scale with AWBW zoom function
  observerCreation(document.getElementById("options-menu"), true);
  console.log("It's asdas: " + pageUrl);
  //increasing z-index for ppl without css changes
  document.getElementById("build-menu").style.zIndex=1500;
  document.getElementById("build-options-game").style.zIndex=1500;
}
//optionsMenu (unit-options-game, build-options-game. unit-options-menu, build-menu), pxMove (how many pixels to move the Menu), boolMidpoint (if there's an extra step mid-screen with pxMove/2)
else if (pageUrl.includes(word2)) {
  observerCreation(document.getElementsByClassName("unit-options-game")[0], false);
  observerCreation(document.getElementsByClassName("build-options-game")[0], false);
  console.log("pageUrl: " + pageUrl);
  document.getElementsByClassName("unit-options-game")[0].style.zIndex=1500;
  document.getElementsByClassName("build-options-game")[0].style.zIndex=1500;
}