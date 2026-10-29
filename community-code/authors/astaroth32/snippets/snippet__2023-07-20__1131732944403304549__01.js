fetchStatsInfo(currentStatsPId);
gameStatsScreen.style.display="flex";
let t=document.querySelector('.game-stats'),s=t.style;
document.querySelector('#gamemap-container').appendChild(t);
s.position='absolute';
s.left='2px';
//s.top='25%';
s.top='-2px';
s.width='200px';

let swapLeft = s.width;
//let swapLeft2 = document.getElementById("gamemap-container").clientWidth;
let swapLeft2 = document.getElementsByClassName("game-stats end-game-tab")[0].clientWidth;

let swag = document.getElementById("map-controls-container").style;

console.log("${swapLeft} = " + swapLeft );
console.log("${swapLeft2} = " + swapLeft2 );

console.log("${swag} = " + swag);

//s.left-=parseInt(s.width)*2 + "px";
//s.left-=s.width;
s.left=swapLeft2 * -1 -8 + "px";

console.log("s.left = " + s.left);
