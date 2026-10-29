function applyCSS(el, styles) {
  for (var prop in styles) {
    el.style[prop] = styles[prop];
  }
}
