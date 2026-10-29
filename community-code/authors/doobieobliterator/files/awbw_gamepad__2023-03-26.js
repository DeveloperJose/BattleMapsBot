document.addEventListener("DOMContentLoaded", () => {
	let gamepadIndex = null
	let gamepadButtonProperties = null
	let buttonHoldDelayTime = 0.15
	let buttonHoldDelayTime2 = 0.05
	let selectedUnit = null
	let selectedMovementTile = null
	let selectedBuilding = null
	let selectionContext = "map"
	let cursorAudio
	
	cursor.style.display = "block"
	cursor.style.left = "-6px"
	cursor.style.top = "-5px"
	
	window.addEventListener("gamepadconnected", e => {
		console.log("Gamepad connected!")
		gamepadIndex = e.gamepad.index
		setupGamepadButtonProperties(e.gamepad.buttons)

		let controllerStyles = document.createElement("style")
		controllerStyles.innerHTML = ".controller-hovered {background-color: gold !important;}"
		document.head.appendChild(controllerStyles)
		
		cursorAudio = new Audio("https://macroland.one/game/action_cursormove.wav")
	})
	
	window.addEventListener("gamepaddisconnected", () => {
		console.log("Gamepad disconnected!")
		gamepadIndex = null
	})
	
	function setupGamepadButtonProperties(buttons) {
		gamepadButtonProperties = []
		buttons.forEach((button, id) => {
			gamepadButtonProperties.push({
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
			case 12:
			case 13:
			case 14:
			case 15: return handleCursorMove
			default: return debugButtonEvent
		}
	}
	
	function handleCancel(id) {
		switch(selectionContext) {
			case "movement-tile":
			case "unit-options-game":
			case "select-enemy-unit-fire-on":
				handleCancelToMap()
				break
		}
	}
	
	function handleCancelToMap() {
		console.log("cancel")
		mapClick(document.querySelector("#map-background"), document.querySelector("#map-background"))
		selectedUnit = null
		selectedBuilding = null
		selectionContext = "map"
	}
	
	function handleSelect(id) {
		let cursorPageX = parseInt(cursor.style.left)
		let cursorPageY = parseInt(cursor.style.top)
		switch(selectionContext) {
			case "map":
				handleSelectMap(cursorPageX, cursorPageY)
				break
			case "movement-tile":
				handleSelectUnit(cursorPageX, cursorPageY)
				break
			case "unit-options-game":
				handleSelectUnitOptions()
				break
			case "select-enemy-unit-fire-on":
				handleSelectEnemyUnitToFireOn(cursorPageX, cursorPageY)
				break
			case "building-options-game":
				handleSelectUnitToBuildOptions()
				break;
		}
	}
	
	function handleSelectMap(cursorPageX, cursorPageY) {
		selectedUnit = document.querySelector(`span[class~='clickable'][style='left: ${cursorPageX + 6}px;top: ${cursorPageY + 5}px;']`)
		if(selectedUnit !== null) {
			mapClick(selectedUnit, selectedUnit)
			selectionContext = "movement-tile"
		}
		else {
			selectedBuilding = document.querySelector(`span[class~='clickable'][style='left: ${cursorPageX + 6}px;top: ${cursorPageY - 4}px;']`)
			mapClick(selectedBuilding, selectedBuilding)
			let curr = document.querySelector(".controller-hovered")
			if(curr !== null) curr.classList.remove("controller-hovered")
			buildOptionsContent.children[0].classList.add("controller-hovered")
			selectionContext="building-options-game"
		}
	}
	
	function handleSelectUnit(cursorPageX, cursorPageY) {
		selectedMovementTile = document.querySelector(`[class='movement-tile'][style*='left: ${cursorPageX + 5}px; top: ${cursorPageY + 4}px;']`)
		if(selectedMovementTile !== null) {
			mapClick(selectedMovementTile, selectedMovementTile)
			let curr = document.querySelector(".controller-hovered")
			if(curr !== null) curr.classList.remove("controller-hovered")
			unitOptionsMenu.children[0].children[0].classList.add("controller-hovered")
			selectionContext = "unit-options-game"	
		}
		else {
			handleCancelToMap()
		}
	}
	
	function handleSelectUnitOptions() {
		let option = document.querySelector(".controller-hovered")
		let optionValue = option.innerText
		menuClick({target: option})
		switch(optionValue) {
			case "Wait":
				handleCancelToMap()
				break
			case "Fire":
				selectionContext = "select-enemy-unit-fire-on"
				break;
		}
	}
	
	function handleSelectEnemyUnitToFireOn(cursorPageX, cursorPageY) {
		console.log("fire on")
	}
	
	function handleSelectUnitToBuildOptions() {
		let option = document.querySelector(".controller-hovered")
		menuClick({target: option})
	}
	
	function handleCursorMove(id) {
		switch(selectionContext) {
			case "map":
			case "movement-tile":
			case "select-enemy-unit-fire-on":
				handleCursorMoveMap(id)
				break
			case "unit-options-game":
			case "building-options-game":
				handleCursorMoveMenu(id)
				break;
		}
	}
	
	function handleCursorMoveMap(id) {
		let cursorMoveToPagePosition = {
			pageX: cursor.getBoundingClientRect().x + scrollX + ((cursor.width*scale)/2),
			pageY: cursor.getBoundingClientRect().y + scrollY + ((cursor.height*scale)/2),
		}
		switch(id) {
			case 12:
				cursorMoveToPagePosition.pageY -= 16*scale
				break
			case 13:
				cursorMoveToPagePosition.pageY += 16*scale
				break
			case 14:
				cursorMoveToPagePosition.pageX -= 16*scale
				break
			case 15:
				cursorMoveToPagePosition.pageX += 16*scale
				break
		}
		cursorAudio.play()
		updateCoords({
			pageX: cursorMoveToPagePosition.pageX,
			pageY: cursorMoveToPagePosition.pageY,
			target: document.querySelector("#map-background")
		})
	}
	
	function handleCursorMoveMenu(id) {
		let currentControllerHovered = document.querySelector(".controller-hovered")
		switch(id) {
			case 12:
			case 14:
				if(currentControllerHovered.previousSibling !== null) {
					currentControllerHovered.classList.remove("controller-hovered")
					currentControllerHovered.previousSibling.classList.add("controller-hovered")
				}
				break
			case 13:
			case 15:
				if(currentControllerHovered.nextSibling !== null) {
					currentControllerHovered.classList.remove("controller-hovered")
					currentControllerHovered.nextSibling.classList.add("controller-hovered")
				}
				break
		}
	}
	
	function debugButtonEvent(id) {
		console.log(`Button pressed: ${id}`)
	}
	
	function handleButtonPressStarted(button, id, currentTime) {
		gamepadButton = gamepadButtonProperties[id]
		gamepadButton.isPressing = true
		gamepadButton.isPressingTimeStarted = currentTime
		gamepadButton.action(id)
		gamepadButton.isPressingHeldIterations = 0
	}
	
	function handleButtonPressHold(button, id, currentTime) {
		gamepadButton = gamepadButtonProperties[id]
		gamepadButton.isPressingTimeHeld = currentTime - gamepadButton.isPressingTimeStarted
		
		let speed = buttonHoldDelayTime
		if(gamepadButton.isPressingHeldIterations > 2) speed = buttonHoldDelayTime2
		
		if(gamepadButton.isPressingTimeHeld >= speed) {
			gamepadButton.action(id)
			gamepadButton.isPressingTimeStarted = currentTime
			gamepadButton.isPressingHeldIterations++
		}
	}
	
	function handleButtonPressCanceled(button, id) {
		gamepadButton = gamepadButtonProperties[id]
		gamepadButton.isPressing = false
		gamepadButton.isPressingTimeStarted = null
		gamepadButton.isPressingHeldIterations = 0
	}
	
	function handleButtons(buttons, currentTime) {
		buttons.forEach((button, id) => {
			if(button.pressed && !gamepadButtonProperties[id].isPressing)
				handleButtonPressStarted(button, id, currentTime)
			else if(button.pressed && gamepadButtonProperties[id].isPressing && (id == 12 || id == 13 || id == 14 || id == 15))
				handleButtonPressHold(button, id, currentTime)
			else if(!button.pressed && gamepadButtonProperties[id].isPressing)
				handleButtonPressCanceled(button, id, currentTime)
		})
	}
	
	function handleAxes(axes) {
		//console.log(axes[0])
		//console.log(axes[1])
	}
	
	function controlLoop(currentTime) {
		currentTime *= 0.001
		if(cursor !== null)
			if(cursor.style.display == "none")
				cursor.style.display = "block"
		if(gamepadIndex !== null) {
			const gamepad = navigator.getGamepads()[gamepadIndex]
			handleButtons(gamepad.buttons, currentTime)
			handleAxes(gamepad.axes)
		}
		requestAnimationFrame(controlLoop)
	}
	
	controlLoop()
})