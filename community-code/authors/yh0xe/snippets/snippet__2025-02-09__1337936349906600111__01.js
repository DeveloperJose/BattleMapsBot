const obsvBuildAndOptionsMenus = new MutationObserver((_mutations) => {
    //Make sure target damage preview does not exit the top of the screen
    const optionsMenu = document.getElementById('options-menu');
    const buildMenu = document.getElementById('build-menu');
    for (const e of [optionsMenu, buildMenu]) {
        if (settings.active && parseFloat(e.style.top) && parseFloat(e.style.top) > 150) e.style.top = "150px";
    }
});
function maximise() {
...
  const optionsMenu = document.getElementById('options-menu');
  const buildMenu = document.getElementById('build-menu');
  
  if (isMovePlanner) {
      obsvBuildAndOptionsMenus.observe(optionsMenu, { attributes: true });
      obsvBuildAndOptionsMenus.observe(buildMenu, { attributes: true });
  }
...
    }

function reset() {
  obsvBuildAndOptionsMenus.disconnect();
