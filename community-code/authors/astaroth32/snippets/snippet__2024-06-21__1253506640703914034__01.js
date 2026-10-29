const gameUnits = document.querySelectorAll('span[id^="unit_"]>img[src*="terrain/ani/"]:not([id^="unit_"])');
//gameUnits.forEach((element) => console.log(element));
const matchingElements = [];

let deleteCountry = "pl"; //which country's units should be deleted

gameUnits.forEach((element) => {
  let src = element.src;
  //let src = element.getAttribute('src');
  console.log(src);

  let matchResult = src.match(/([a-z]{2})(?:infantry|tank|mech|b-copter|recon|artillery|cruiser)/);
  let countryName = matchResult && matchResult[1];
  if (countryName !== null) {
    console.log(countryName);
  } else {
    console.log("null");
  }
  if (countryName === deleteCountry) {
    matchingElements.push(element);
  }
});

console.log(matchingElements); // array of elements that match the criteria
matchingElements.forEach(element => {
  let pElement = element.parentElement;
  console.log(pElement);
  pElement.remove();
});
