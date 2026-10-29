window.addEventListener("load", () => {
	initTeamCheckboxes()
})

let checkboxAll
let checkboxContainer
let checkboxArray
let teams

function initCheckboxArray() {
	let arr = []
	let childArray = Array.from(checkboxContainer.childNodes)
	let skippedAllCheckbox = false
	childArray.forEach((item, i) => {
	    if(item.tagName === 'INPUT') {
	    	if(skippedAllCheckbox) {
		    	let siblings = findCheckboxSiblings([...childArray].splice(i+1, i+1))
		    	arr.push({
		    		input: item,
		    		...siblings
		    	})
	    	}
	    	else {
	    		skippedAllCheckbox = true
	    	}
	    }
	})
	return arr
}

function findCheckboxSiblings(siblingsArray) {
	return {
		team: siblingsArray[4].textContent.trim().substring(1).substring(0, siblingsArray[4].length-3)
	}
}

function determineAllTeams() {
	const found = Array.from(checkboxContainer.innerText.matchAll(/Team [a-zA-Z]/g))
	const teamsUnfiltered = found.map(team => team[0])
	return teamsUnfiltered.filter((team, index) => teamsUnfiltered.indexOf(team) === index).reverse()
}

function createTeamCheckboxes() {
	teams.forEach(team => {
		const checkbox = createTeamCheckbox(team)
		
		checkboxContainer.prepend(document.createElement("br"))
		checkboxContainer.prepend(team)
		checkboxContainer.prepend(checkbox)
	})
}

function createTeamCheckbox(team) {
	const checkbox = document.createElement("input")
	checkbox.type="checkbox";
	checkbox.name=`to_${team}`
	checkbox.addEventListener("change", () => {
		checkboxArray.forEach(player => {
			if(player.team === team && player.input.disabled === false) {
				player.input.checked = checkbox.checked	
			}
		})
	})
	return checkbox
}

function initTeamCheckboxes() {
	if(location.pathname.includes("press.php")) {
		checkboxAll = document.querySelector('input[name="broadcast"]')
		checkboxContainer = checkboxAll.parentElement
		checkboxArray = initCheckboxArray()
		console.dir(checkboxArray)
		
		teams = determineAllTeams()
		createTeamCheckboxes()	
	}
}