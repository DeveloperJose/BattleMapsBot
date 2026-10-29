// ==UserScript==
// @name         AWBW Automatically Do Shit
// @namespace    https://awbw.amarriner.com/
// @version      1
// @description  Automatically scrolls the window to the best position and sets up a page refresh event for when the match disconnects so you don't have to manually refresh the page
// @author       doobieobliterator
// @match        https://awbw.amarriner.com/*?games_id=*
// @icon         https://awbw.amarriner.com/favicon.ico
// @license MIT
// ==/UserScript==

let needsRefresh = false
let refreshNotification = document.querySelector(".connection-display")
window.onfocus = () => {
	if(needsRefresh && refreshNotification.style.display === "block") location.reload()
}
window.onblur = () => {
	needsRefresh = true
}
setTimeout(() => window.scrollTo(0, 150), 500)