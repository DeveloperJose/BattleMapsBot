// ==UserScript==
// @name         AWBW Gamepad Controls
// @namespace    https://awbw.amarriner.com/
// @version      0.9.2
// @description  Allows use of gamepad controllers on Advance Wars by Web
// @author       doobieobliterator
// @match        https://awbw.amarriner.com/*
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
let cursorX = null
let cursorY = null
let buttonHoldIterationsThreshold = null
let cursorAudioSrc = null
let selectionContextOptions = null
let selectionContext = null
let selectionContextOld = null
let mapBackground = null
let hoveredUnit = null
let selectedUnit = null
let hoveredMovementTile = null
let hoveredBuilding = null
let hoveredDamageTile = null
let hoveredDamageTileOld = null
let menuOptionHoveredClass = null
let currentOptionHovered = null
let menuUnitOptions = null
let menuBuildingOptions = null
let menuEndTurnConfirmation = null
let endTurnButton = null
let cancleEndTurnButton = null
let COPButton = null
let SCOPButton = null
let leftAxesHorizontalHeldIterations = null
let leftAxesVerticalHeldIterations = null
let leftAxesHorizontalHeldTimeStarted = null
let leftAxesVerticalHeldTimeStarted = null
let viewerPlayersAutoSelectionActions = null
let currentViewerPlayerUnitAutoSelect = null

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
	cursorX = 0
	cursorY = 0
	buttonHoldIterationsThreshold = 1
	selectionContextOptions = {
		Map: "Map",
		MenuUnitOptions: "MenuUnitOptions",
		MenuBuildingOptions: "MenuBuildingOptions",
		MenuEndTurnConfirmation: "MenuEndTurnConfirmation"
	}
	selectionContext = selectionContextOptions.Map
	selectionContextOld = selectionContext
	cursorAudioSrc = "https://macroland.one/game/action_cursormove.wav"
	mapBackground = document.querySelector("#map-background")
	menuOptionHoveredClass = "controller-hovered"
	menuUnitOptions = document.querySelector(".unit-options-game")
	menuUnitOptions.style.display = "none"
	menuBuildingOptions = document.querySelector(".build-options-game")
	menuBuildingOptions.style.display = "none"
	menuEndTurnConfirmation = document.querySelector(".end-turn-screen")
	menuEndTurnConfirmation.style.display = "none"
	endTurnButton = document.querySelector("#end-turn")
	cancleEndTurnButton = document.querySelector(".end-turn-cancel-btn")
	COPButton = document.querySelector(".cop-button")
	SCOPButton = document.querySelector(".scop-button")
	leftAxisHorizontalHeldIterations = 0
	leftAxisVerticalHeldIterations = 0
	currentViewerPlayerAutoSelectActionIndex = -1
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
		@keyframes cursorAnimation {
			0% {transform: scale(1)}
			50% {transform: scale(0.9)}
			100% {transform: scale(1)}
		}
		#cursor {
			animation: cursorAnimation 1s infinite step-end;
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
		case 3: return handleEndTurn
		case 6:
		case 7: return handleAutoSelectAction
		case 8: return handleActivatePower
		case 9: return handleActivateSuperPower
		case 12:
		case 13:
		case 14:
		case 15: return handleCursorMove
		default: return debugButtonEvent
	}
}

function handleCancel() {
	mapClick(mapBackground, mapBackground)
	if(selectionContext === selectionContextOptions.MenuEndTurnConfirmation)
		toggleConfMenu(endTurnConfScreen)
	selectionContext = selectionContextOptions.Map
	selectionContextOld = selectionContext
}

function handleSelect() {
	switch(selectionContext) {
		case selectionContextOptions.Map:
			handleSelectMap()
			break
		case selectionContextOptions.MenuUnitOptions:
		case selectionContextOptions.MenuBuildingOptions:
		case selectionContextOptions.MenuEndTurnConfirmation:
			handleSelectMenu()
			break
	}
}

function handleSelectMap() {
	handleCursorMoveGameCheckHoveredUnit()
	handleCursorMoveGameCheckHoveredMovementTile()
	handleCursorMoveMapCheckHoveredBuilding()
	if(hoveredDamageTile !== null)
		hoveredDamageTile.dispatchEvent(new Event("click"))
	else if(selectedUnit !== null && selectedUnit.classList.contains("clickable") && hoveredMovementTile !== null) {
		mapClick(hoveredMovementTile, hoveredMovementTile)
		selectedUnit = null
	}
	else if(hoveredUnit !== null) {
		selectedUnit = hoveredUnit
		mapClick(hoveredUnit, hoveredUnit)
		handleCursorMoveGameCheckHoveredMovementTile()
	}
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
			break
		case selectionContextOptions.MenuBuildingOptions:
		case selectionContextOptions.MenuEndTurnConfirmation:
			currentOptionHovered.dispatchEvent(new Event("click"))
			break
	}
}

function handleEndTurn() {
	if(endTurnButton.style.display !== "none") {
		endTurnButton.dispatchEvent(new Event("click"))
		selectionContext = selectionContextOptions.Map
	}
}

function handleAutoSelectAction(id) {
	let currAutoSelectAction
	let currAutoSelectActionEl
	checkViewerPlayersAutoSelectionActions()
	if(viewerPlayersAutoSelectionActions.length > 0) {
		switch(id) {
			case 6:
				if(currentViewerPlayerAutoSelectActionIndex > 0)
					currentViewerPlayerAutoSelectActionIndex -= 1
				else
					currentViewerPlayerAutoSelectActionIndex = viewerPlayersAutoSelectionActions.length-1
				break;
			case 7:
				if(currentViewerPlayerAutoSelectActionIndex < viewerPlayersAutoSelectionActions.length - 1)
					currentViewerPlayerAutoSelectActionIndex += 1
				else
					currentViewerPlayerAutoSelectActionIndex = 0
				break;
		}
		if(currentViewerPlayerAutoSelectActionIndex > viewerPlayersAutoSelectionActions.length - 1)
			currentViewerPlayerAutoSelectActionIndex = 0
		currAutoSelectAction = viewerPlayersAutoSelectionActions[currentViewerPlayerAutoSelectActionIndex]
		currAutoSelectActionEl
		handleCancel()
		if(currAutoSelectAction.type === "unit") {
			currAutoSelectActionEl = document.querySelector(`span[data-unit-id="${currAutoSelectAction.units_id}"]`)
			moveCursorToAutoSelectedAction(parseInt(currAutoSelectActionEl.style.left), parseInt(currAutoSelectActionEl.style.top))
		}
		else {
			currAutoSelectActionEl = document.querySelector(`span[data-building-id="${currAutoSelectAction.buildings_id}"]`)
			moveCursorToAutoSelectedAction(parseInt(currAutoSelectActionEl.style.left), parseInt(currAutoSelectActionEl.style.top))
		}
		handleCursorMoveMap(0)
		handleSelect()
	}
}

function checkViewerPlayersAutoSelectionActions() {
	viewerPlayersUnits = []
	viewerPlayersUnitsMoved = []
	viewerPlayersBuildings = []

	for(unit in unitsInfo) {
	    let currUnit = unitsInfo[unit]
	    if(currUnit.units_players_id === viewerPId) {
	    	if(currUnit.units_moved === 0) {
	    		currUnit.type = "unit"
	    		viewerPlayersUnits.push(currUnit)
	    	}
	    	else
	    		viewerPlayersUnitsMoved.push(currUnit)
	    }
	}
	
	for(buildingSomething in buildingsInfo) {
		for(building in buildingsInfo[buildingSomething]) {
			let currBuilding = buildingsInfo[buildingSomething][building]
			if(currBuilding.buildings_players_id === viewerPId
				&& (currBuilding.terrain_name.includes("Base") || currBuilding.terrain_name.includes("Airport") || currBuilding.terrain_name.includes("Port"))) {
				let unitAtPosition = viewerPlayersUnits.concat(viewerPlayersUnitsMoved).find(unit => unit.units_x === currBuilding.buildings_x && unit.units_y === currBuilding.buildings_y)
				if(unitAtPosition === null || unitAtPosition === undefined){
					currBuilding.type = "building"
					viewerPlayersBuildings.push(currBuilding)
				}
			}
		}
	}
	
	viewerPlayersUnits.sort((a,b) => (a.units_x + a.units_y) >= (b.units_x + b.units_y) ? 1 : -1)
	viewerPlayersBuildings.sort((a,b) => (a.buildings_x + a.buildings_y) >= (b.buildings_x + b.buildings_y) ? 1 : -1)
	viewerPlayersAutoSelectionActions = viewerPlayersUnits.concat(viewerPlayersBuildings)
}

function moveCursorToAutoSelectedAction(left, top) {
	cursor.style.left = left + "px"
	cursor.style.top = top + "px"
}

function handleActivatePower() {
	if(COPButton.style.display !== "none") COPButton.dispatchEvent(new Event("click"))
}

function handleActivateSuperPower() {
	if(SCOPButton.style.display !== "none") SCOPButton.dispatchEvent(new Event("click"))
}

function handleCursorMove(id) {
	switch(selectionContext) {
		case selectionContextOptions.Map:
			handleCursorMoveMap(id)
			break
		case selectionContextOptions.MenuUnitOptions:
		case selectionContextOptions.MenuBuildingOptions:
		case selectionContextOptions.MenuEndTurnConfirmation:
			handleCursorMoveMenu(id)
			break
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
		default:
			break;
	}

	updateCoords({
		pageX: cursorMoveToWindowX,
		pageY: cursorMoveToWindowY,
		target: mapBackground
	})

	new Audio(cursorAudioSrc).play()

	cursorPageX = parseInt(cursor.style.left)
	cursorPageY = parseInt(cursor.style.top)
	cursorX = parseInt(coordsDisplay.innerText.substr(0, coordsDisplay.innerText.length - 1).substr(1).split(",")[0])
	cursorY = parseInt(coordsDisplay.innerText.substr(0, coordsDisplay.innerText.length - 1).substr(1).split(",")[1])

	handleCursorMoveGameCheckDamageTiles()
}

function handleCursorMoveMenu(id) {
	switch(id) {
		case 12:
		case 14:
			currentOptionHovered.classList.remove(menuOptionHoveredClass)
			if(currentOptionHovered.previousElementSibling !== null)
				currentOptionHovered = currentOptionHovered.previousElementSibling
			else
				currentOptionHovered = currentOptionHovered.parentElement.children[currentOptionHovered.parentElement.children.length-1]
			currentOptionHovered.classList.add(menuOptionHoveredClass)
			break
		case 13:
		case 15:
			currentOptionHovered.classList.remove(menuOptionHoveredClass)
			if(currentOptionHovered.nextElementSibling !== null)
				currentOptionHovered = currentOptionHovered.nextElementSibling
			else
				currentOptionHovered = currentOptionHovered.parentElement.children[0]
			currentOptionHovered.classList.add(menuOptionHoveredClass)
			break
	}
	new Audio(cursorAudioSrc).play()
}

function handleCursorMoveGameCheckHoveredUnit() {
	for(unit in unitsInfo) {
		let currUnit = unitsInfo[unit]
		if(currUnit.units_x === cursorX && currUnit.units_y === cursorY) {
			hoveredUnit = document.querySelector(`span[data-unit-id="${currUnit.units_id}"]`)
			break
		}
		else hoveredUnit = null
	}
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
	for(buildingSomething in buildingsInfo) {
		for(building in buildingsInfo[buildingSomething]) {
			let currBuilding = buildingsInfo[buildingSomething][building]
			if(currBuilding.buildings_x === cursorX && currBuilding.buildings_y === cursorY) {
				hoveredBuilding = document.querySelector(`span[data-building-id="${currBuilding.buildings_id}"]`)
				break
			}
		}
	}
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

		if(gamepadButtonCustomProperties.isPressingHeldIterations > buttonHoldIterationsThreshold) currentCursorSpeed = cursorSpeedFast
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
	if(menuUnitOptions.style.display !== "none" && selectionContext != selectionContextOptions.MenuUnitOptions) {
		selectionContextOld = selectionContext
		selectionContext = selectionContextOptions.MenuUnitOptions
		highlightMenuInitialOption(menuUnitOptions)
	}
	else if(
		menuUnitOptions.style.display === "none"
		&& selectionContextOld != selectionContext
		&& selectionContext !== selectionContextOptions.MenuBuildingOptions
		&& selectionContext !== selectionContextOptions.MenuEndTurnConfirmation) {
		selectionContext = selectionContextOld
	}

	if(menuBuildingOptions.style.display !== "none" && selectionContext != selectionContextOptions.MenuBuildingOptions) {
		selectionContextOld = selectionContext
		selectionContext = selectionContextOptions.MenuBuildingOptions
		highlightMenuInitialOption(menuBuildingOptions)
	}
	else if(
		menuBuildingOptions.style.display === "none"
		&& selectionContextOld != selectionContext
		&& selectionContext !== selectionContextOptions.MenuUnitOptions
		&& selectionContext !== selectionContextOptions.MenuEndTurnConfirmation) {
		selectionContext = selectionContextOld
	}

	if(menuEndTurnConfirmation.style.display !== "none" && selectionContext != selectionContextOptions.MenuEndTurnConfirmation) {
		selectionContextOld = selectionContext
		selectionContext = selectionContextOptions.MenuEndTurnConfirmation
		highlightMenuInitialOption(menuEndTurnConfirmation)
	}
	else if(
		menuEndTurnConfirmation.style.display === "none"
		&& selectionContextOld != selectionContext
		&& selectionContext !== selectionContextOptions.MenuUnitOptions
		&& selectionContext !== selectionContextOptions.MenuBuildingOptions) {
		selectionContext = selectionContextOptions.Map
	}
}

function highlightMenuInitialOption(menu) {
	if(currentOptionHovered !== null) currentOptionHovered.classList.remove(menuOptionHoveredClass)
	switch(selectionContext) {
		case selectionContextOptions.MenuUnitOptions:
		case selectionContextOptions.MenuBuildingOptions:
			currentOptionHovered = menu.children[0].children[0]
			break
		case selectionContextOptions.MenuEndTurnConfirmation:
			currentOptionHovered = menu.children[0].children[2].children[0]
			break
	}
	currentOptionHovered.classList.add(menuOptionHoveredClass)
}