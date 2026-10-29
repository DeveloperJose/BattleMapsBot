document.addEventListener("DOMContentLoaded", () => {
	let gamepadIndex = null
	let gamepadButtonProperties = null
	let buttonHoldDelayTime = 0.5
	let selectedUnit = null
	let selectedBuilding = null
	let selectionContext = "map"
	
	window.addEventListener("gamepadconnected", e => {
		console.log("Gamepad connected!")
		gamepadIndex = e.gamepad.index
		setupGamepadButtonProperties(e.gamepad.buttons)
		
		cursor.style.display="block"
		cursor.style.left= "-6px"
		cursor.style.top = "-5px"
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
				action: assignActionToButton(id)
			})
		})
	}
	
	function assignActionToButton(id) {
		switch(id) {
			case 1: return handleSelect
			case 12:
			case 13:
			case 14:
			case 15: return handleCursorMove
			default: return debugButtonEvent
		}
	}
	
	function handleSelect(id) {
		let cursorPageX = parseInt(cursor.style.left)
		let cursorPageY = parseInt(cursor.style.top)
		switch(selectionContext) {
			case "map":
				handleSelectMap(cursorPageX, cursorPageY)
				break
			case "unit":
				handleSelectUnit(cursorPageX, cursorPageY)
				break
		}
	}
	
	function handleSelectMap(cursorPageX, cursorPageY) {
		selectedUnit = document.querySelector(`span[style='left: ${cursorPageX + 6}px;top: ${cursorPageY + 5}px;'][class~='clickable']`)
		if(selectedUnit != null) {
			mapClick(selectedUnit, selectedUnit)
			selectionContext = "unit"
		}
		else {
			selectedBuilding = document.querySelector(`span[style='left: ${cursorPageX + 6}px;top: ${cursorPageY - 4}px;'][class~='clickable']`)
		}
	}
	
	function handleSelectUnit(cursorPageX, cursorPageY) {
		console.log("HERE")
	}
	
	function handleCursorMove(id) {
		
		let cursorMoveToPagePosition = {
			pageX: cursor.getBoundingClientRect().x + scrollX + ((cursor.width*scale)/2),
			pageY: cursor.getBoundingClientRect().y + scrollY + ((cursor.height*scale)/2),
		}
		
		switch(id) {
			case 12:
				cursorMoveToPagePosition.pageY -= 16*scale
				break;
			case 13:
				cursorMoveToPagePosition.pageY += 16*scale
				break;
			case 14:
				cursorMoveToPagePosition.pageX -= 16*scale
				break;
			case 15:
				cursorMoveToPagePosition.pageX += 16*scale
				break;
		}
		updateCoords({
			pageX: cursorMoveToPagePosition.pageX,
			pageY: cursorMoveToPagePosition.pageY,
			target: document.querySelector("#map-background")
		})
	}
	
	function debugButtonEvent(id) {
		console.log(`Button pressed: ${id}`)
	}
	
	function handleButtonPressStarted(button, id, currentTime) {
		gamepadButton = gamepadButtonProperties[id]
		gamepadButton.isPressing = true
		gamepadButton.isPressingTimeStarted = currentTime
		gamepadButton.action(id)
	}
	
	function handleButtonPressHold(button, id, currentTime) {
		gamepadButton = gamepadButtonProperties[id]
		gamepadButton.isPressingTimeHeld = currentTime - gamepadButton.isPressingTimeStarted
	}
	
	function handleButtonPressCanceled(button, id) {
		gamepadButton = gamepadButtonProperties[id]
		gamepadButton.isPressing = false
		gamepadButton.isPressingTimeStarted = null
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
				cursor.style.display = "block";
		if(gamepadIndex !== null) {
			const gamepad = navigator.getGamepads()[gamepadIndex]
			handleButtons(gamepad.buttons, currentTime)
			handleAxes(gamepad.axes)
		}
		requestAnimationFrame(controlLoop)
	}
	
	controlLoop()
})