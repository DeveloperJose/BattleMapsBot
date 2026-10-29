function waitUnit(unitId) {
  var unit = unitsInfo[unitId];
  if (!unit) return;
  var unitName = unit.units_name;
  var countryCode = unit.countries_code;

  if (viewerColors) {
    countryCode = viewerColors[unit.units_players_id];
  }

  var unitSpan = document.querySelector("span[data-unit-id='" + unitId + "']");
  if (!unitSpan) return;
  var unitSprite = unitSpan.children[0];
  var cargo1 = unit.units_cargo1_units_id;
  var cargo2 = unit.units_cargo2_units_id; //For transport units, don't darken it until every carried unit is unloaded

  if (!cargo1 && !cargo2) {
    unitSprite.src = TP + "gs_" + countryCode + unitName.replace(" ", "").toLowerCase() + ".gif";
  }

  unit.units_moved = 1;
}
