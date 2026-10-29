const idealZoom = 2;

if (gamemap.style.transform == "scale(" + idealZoom + ")") {
  console.log("pixelate this");
  gamemap.style.imageRendering = "pixelated";
}
else {
  console.log("don't pixelate this");
  gamemap.style.imageRendering = "unset";
}

let newZoomInBtn = zoomInBtn.cloneNode(true);
zoomInBtn.parentNode.replaceChild(newZoomInBtn,zoomInBtn);
zoomInBtn = newZoomInBtn;

zoomInBtn.addEventListener("click", function () {
  applyScale(0.1);
  console.log(gamemap.style.transform);
  if (gamemap.style.transform == "scale(" + idealZoom + ")") {
    console.log("pixelate this");
    gamemap.style.imageRendering = "pixelated";
  }
  else {
    console.log("no pixelation");
    gamemap.style.imageRendering = "unset";
  }
});

let newZoomOutBtn = zoomOutBtn.cloneNode(true);
zoomOutBtn.parentNode.replaceChild(newZoomOutBtn,zoomOutBtn);
zoomOutBtn = newZoomOutBtn;

zoomOutBtn.addEventListener("click", function () {
  applyScale(-0.1);
  console.log(gamemap.style.transform);
  if (gamemap.style.transform == "scale(" + idealZoom + ")") {
    console.log("pixelate this");
    gamemap.style.imageRendering = "pixelated";
  }
  else {
    console.log("no pixelation");
    gamemap.style.imageRendering = "unset";
  }
});
