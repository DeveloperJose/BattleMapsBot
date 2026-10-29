
old_link = "terrain/ani/neutralcity.gif";
new_link = "terrain/ani/missilesiloempty.gif";

buildings_id = Array.from(document.querySelectorAll("[id*='building_']"));
buildings_class = Array.from(document.querySelectorAll("[class~=s]"));
buildings = buildings_id.concat(buildings_class);
filtered_buildings = buildings.filter((x) => {return x.children[0].getAttribute('src') == old_link;});
filtered_buildings.forEach(
    (x) => {
        x.children[0].setAttribute("src", new_link);
    }
)


