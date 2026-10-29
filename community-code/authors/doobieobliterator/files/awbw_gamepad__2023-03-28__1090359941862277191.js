// ==UserScript==
// @name         AWBW Gamepad Controls
// @namespace    https://awbw.amarriner.com/
// @version      0.9
// @description  Allows use of gamepad controllers on Advance Wars by Web
// @author       doobieobliterator
// @match        https://awbw.amarriner.com/*?games_id=*
// @match        https://awbw.amarriner.com/*?replays_id=*
// @match        https://awbw.amarriner.com/*editmap*
// @icon         https://awbw.amarriner.com/favicon.ico
// @license MIT
// ==/UserScript==

let gamepadIndex = null
let gamepadButtonsCustomProperties = null
let cursorSpeedSlow = null
let cursorSpeedFast = null
let currentCursorSpeed = null
let cursorPageX = null
let cursorPageY = null
let buttonHoldIterationsThreshold = null
let cursorAudioSrc = null
let selectionContextOptions = null
let selectionContext = null
let selectionContextOld = null
let endTurnOverlay = null
let endTurnButton = null
let mapBackground = null
let hoveredUnit = null
let hoveredUnitIsOwned = false
let hoveredMovementTile = null
let hoveredBuilding = null
let hoveredDamageTile = null
let hoveredDamageTileOld = null
let menuOptionHoveredClass = null
let currentOptionHovered = null
let menuMenuUnitOptions = null
let menuMenuBuildingOptions = null

window.addEventListener("gamepadconnected", e => {
    console.log("Gamepad connected!")
    gamepadIndex = e.gamepad.index
    setupGamepadButtonCustomProperties(e.gamepad.buttons)
})

window.addEventListener("gamepaddisconnected", () => {
    console.log("Gamepad disconnected!")
    gamepadIndex = null
})

initGamepadPlugin()

function initGamepadPlugin() {
	initGamepadVariableSettings()
	initGamepadPluginCustomStyles()
	initGamepadCursor()
	controlLoop()
}

function initGamepadCursor() {
	cursor.style.display = "block"
	cursor.style.left = "-6px"
	cursor.style.top = "-5px"
}

function initGamepadVariableSettings() {
	cursorSpeedSlow = 0.15
	cursorSpeedFast = 0.04
	cursorPageX = 0
	cursorPageY = 0
	buttonHoldIterationsThreshold = 1
	selectionContextOptions = {
		Map: "Map",
		MenuUnitOptions: "MenuUnitOptions",
		MenuBuildingOptions: "MenuBuildingOptions"
	}
	selectionContext = selectionContextOptions.Map
	selectionContextOld = selectionContext
	cursorAudioSrc = "https://macroland.one/game/action_cursormove.wav"
	endTurnOverlay = document.querySelector(".end-turn-screen")
	endTurnButton = document.querySelector("#end-turn")
	mapBackground = document.querySelector("#map-background")
	menuOptionHoveredClass = "controller-hovered"
	menuMenuUnitOptions = document.querySelector(".unit-options-game")
	menuMenuUnitOptions.style.display = "none"
	menuMenuBuildingOptions = document.querySelector(".build-options-game")
	menuMenuBuildingOptions.style.display = "none"
}

function initGamepadPluginCustomStyles() {
	let controllerStyles = document.createElement("style")
	controllerStyles.innerText = `
		.${menuOptionHoveredClass} {
			background-color: gold !important;
		}
		.dmg-square-hover {
			animation:
				anim-rotate 3s linear infinite,
		    	dmg-pulse 0.5s linear alternate infinite;
		}
	`
	document.head.appendChild(controllerStyles)
}

function setupGamepadButtonCustomProperties(buttons) {
	gamepadButtonsCustomProperties = []
	buttons.forEach((button, id) => {
		gamepadButtonsCustomProperties.push({
			isPressing: false,
			isPressingTimeStarted: null,
			isPressingTimeHeld: null,
			isPressingHeldIterations: 0,
			action: assignActionToButton(id)
		})
	})
}

function assignActionToButton(id) {
	switch(id) {
		case 0: return handleCancel
		case 1: return handleSelect
		case 9: return handleEndTurn
		case 12:
		case 13:
		case 14:
		case 15: return handleCursorMove
		default: return debugButtonEvent
	}
}

function handleCancel() {
	mapClick(mapBackground, mapBackground)
	selectionContext = selectionContextOptions.Map
	selectionContextOld = selectionContext
}

function handleSelect() {
	switch(selectionContext) {
		case selectionContextOptions.Map:
			handleSelectMap()
			break;
		case selectionContextOptions.MenuUnitOptions:
		case selectionContextOptions.MenuBuildingOptions:
			handleSelectMenu()
			break;
	}
}

function handleSelectMap() {
	if(hoveredDamageTile !== null)
		hoveredDamageTile.dispatchEvent(new Event("click"))
	else if(hoveredUnitIsOwned && hoveredMovementTile !== null)
		mapClick(hoveredMovementTile, hoveredMovementTile)
	else if(hoveredUnit !== null)
		mapClick(hoveredUnit, hoveredUnit)
	else if(hoveredBuilding !== null) {
		mapClick(hoveredBuilding, hoveredBuilding)
	}
	else
		handleCancel()
}

function handleSelectMenu() {
	switch (selectionContext) {
		case selectionContextOptions.MenuUnitOptions:
			menuClick({target: currentOptionHovered})
			break;
		case selectionContextOptions.MenuBuildingOptions:
			currentOptionHovered.dispatchEvent(new Event("click"))
			break;
	}
}

function handleEndTurn() {
}

function handleCursorMove(id) {
	switch(selectionContext) {
		case selectionContextOptions.Map:
			handleCursorMoveMap(id)
			break;
		case selectionContextOptions.MenuUnitOptions:
		case selectionContextOptions.MenuBuildingOptions:
			handleCursorMoveMenu(id)
			break;
	}
}

function handleCursorMoveMap(id) {
	let cursorMoveToWindowX = cursor.getBoundingClientRect().x + scrollX + ((cursor.width*scale)/2)
	let cursorMoveToWindowY = cursor.getBoundingClientRect().y + scrollY + ((cursor.height*scale)/2)

	switch(id) {
		case 12:
			cursorMoveToWindowY -= 16*scale
			break
		case 13:
			cursorMoveToWindowY += 16*scale
			break
		case 14:
			cursorMoveToWindowX -= 16*scale
			break
		case 15:
			cursorMoveToWindowX += 16*scale
			break
	}

	updateCoords({
		pageX: cursorMoveToWindowX,
		pageY: cursorMoveToWindowY,
		target: mapBackground
	})

	new Audio(cursorAudioSrc).play()

	cursorPageX = parseInt(cursor.style.left)
	cursorPageY = parseInt(cursor.style.top)

	handleCursorMoveGameCheckHoveredUnit()
	handleCursorMoveGameCheckHoveredMovementTile()
	handleCursorMoveGameCheckDamageTiles()
	handleCursorMoveMapCheckHoveredBuilding()
}

function handleCursorMoveMenu(id) {
	switch(id) {
		case 12:
		case 14:
			currentOptionHovered.classList.remove(menuOptionHoveredClass)
			if(currentOptionHovered.previousSibling !== null)
				currentOptionHovered = currentOptionHovered.previousSibling
			else
				currentOptionHovered = currentOptionHovered.parentElement.children[currentOptionHovered.parentElement.children.length-1]
			currentOptionHovered.classList.add(menuOptionHoveredClass)
			break
		case 13:
		case 15:
			currentOptionHovered.classList.remove(menuOptionHoveredClass)
			if(currentOptionHovered.nextSibling !== null)
				currentOptionHovered = currentOptionHovered.nextSibling
			else
				currentOptionHovered = currentOptionHovered.parentElement.children[0]
			currentOptionHovered.classList.add(menuOptionHoveredClass)
			break
	}
	new Audio(cursorAudioSrc).play()
}

function handleCursorMoveGameCheckHoveredUnit() {
	hoveredUnit = document.querySelector(`span[class*='game-unit'][style='left: ${cursorPageX + 6}px;top: ${cursorPageY + 5}px;']`)
	if(hoveredUnit !== null) hoveredUnitIsOwned = hoveredUnit.classList.contains("clickable")
}

function handleCursorMoveGameCheckHoveredMovementTile() {
	hoveredMovementTile = document.querySelector(`[class='movement-tile'][style*='left: ${cursorPageX + 5}px; top: ${cursorPageY + 4}px;']`)
}

function handleCursorMoveGameCheckDamageTiles() {
	hoveredDamageTile = document.querySelector(`[class*='dmg-square'][style*='left: ${cursorPageX + 5}px; top: ${cursorPageY + 4}px;']`)

	if(hoveredDamageTile !== null) {
		hoveredDamageTileOld = hoveredDamageTile
		hoveredDamageTileOld.dispatchEvent(new Event("mouseenter"))
		hoveredDamageTileOld.classList.add("dmg-square-hover")
	}
	else if(hoveredDamageTileOld !== null) {
		hoveredDamageTileOld.dispatchEvent(new Event("mouseleave"))
		hoveredDamageTileOld.classList.remove("dmg-square-hover")
	}
}

function handleCursorMoveMapCheckHoveredBuilding() {
	hoveredBuilding = document.querySelector(`span[class~='clickable'][style='left: ${cursorPageX + 6}px;top: ${cursorPageY - 4}px;']`)
	if(hoveredBuilding !== null) console.log(hoveredBuilding)
}

function debugButtonEvent(id) {
	console.log(`Button pressed: ${id}`)
}

function controlLoop(currentTime) {
	currentTime *= 0.001
	if(cursor !== null)
		if(cursor.style.display == "none")
			cursor.style.display = "block"
	if(gamepadIndex !== null) {
		const gamepad = navigator.getGamepads()[gamepadIndex]
		handleButtons(gamepad.buttons, currentTime)
	}
	checkMenus()
	requestAnimationFrame(controlLoop)
}

function handleButtons(buttons, currentTime) {
	buttons.forEach((button, id) => {
		if(button.pressed && !gamepadButtonsCustomProperties[id].isPressing)
			handleButtonPressStarted(button, id, currentTime)
		else if(button.pressed && gamepadButtonsCustomProperties[id].isPressing)
			handleButtonPressHold(button, id, currentTime)
		else if(!button.pressed && gamepadButtonsCustomProperties[id].isPressing)
			handleButtonPressCanceled(button, id, currentTime)
	})
}

function handleButtonPressStarted(button, id, currentTime) {
	gamepadButtonCustomProperties = gamepadButtonsCustomProperties[id]
	gamepadButtonCustomProperties.isPressing = true
	gamepadButtonCustomProperties.isPressingTimeStarted = currentTime
	gamepadButtonCustomProperties.action(id)
	gamepadButtonCustomProperties.isPressingHeldIterations = 0
}

function handleButtonPressHold(button, id, currentTime) {
	if(id == 12 || id == 13 || id == 14 || id == 15) {
		gamepadButtonCustomProperties = gamepadButtonsCustomProperties[id]
		gamepadButtonCustomProperties.isPressingTimeHeld = currentTime - gamepadButtonCustomProperties.isPressingTimeStarted

		if(gamepadButtonCustomProperties.isPressingHeldIterations > 1) currentCursorSpeed = cursorSpeedFast
		else currentCursorSpeed = cursorSpeedSlow

		if(gamepadButtonCustomProperties.isPressingTimeHeld >= currentCursorSpeed) {
			gamepadButtonCustomProperties.action(id)
			gamepadButtonCustomProperties.isPressingTimeStarted = currentTime
			gamepadButtonCustomProperties.isPressingHeldIterations++
		}
	}
}

function handleButtonPressCanceled(button, id) {
	gamepadButtonCustomProperties = gamepadButtonsCustomProperties[id]
	gamepadButtonCustomProperties.isPressing = false
	gamepadButtonCustomProperties.isPressingTimeStarted = null
	gamepadButtonCustomProperties.isPressingHeldIterations = 0
}

function checkMenus() {
	if(menuMenuUnitOptions.style.display !== "none" && selectionContext != selectionContextOptions.MenuUnitOptions) {
		selectionContextOld = selectionContext
		selectionContext = selectionContextOptions.MenuUnitOptions
		highlightMenuInitialOption(menuMenuUnitOptions)
	}
	else if(menuMenuUnitOptions.style.display === "none" && selectionContextOld != selectionContext && selectionContext !== selectionContextOptions.MenuBuildingOptions) {
		selectionContext = selectionContextOld
	}

	if(menuMenuBuildingOptions.style.display !== "none" && selectionContext != selectionContextOptions.MenuBuildingOptions) {
		selectionContextOld = selectionContext
		selectionContext = selectionContextOptions.MenuBuildingOptions
		highlightMenuInitialOption(menuMenuBuildingOptions)
	}
	else if(menuMenuBuildingOptions.style.display === "none" && selectionContextOld != selectionContext && selectionContext !== selectionContextOptions.MenuUnitOptions) {
		selectionContext = selectionContextOld
	}
}

function highlightMenuInitialOption(menu) {
	if(currentOptionHovered !== null) currentOptionHovered.classList.remove(menuOptionHoveredClass)
	switch(selectionContext) {
		case selectionContextOptions.MenuUnitOptions:
		case selectionContextOptions.MenuBuildingOptions:
			currentOptionHovered = menu.children[0].children[0]
			currentOptionHovered.classList.add(menuOptionHoveredClass)
			break;
	}
}