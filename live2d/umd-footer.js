// Re-attach PIXI.live2d from the IIFE global to window.PIXI.live2d
(function() {
  var PLD = window.PIXI_live2d;
  delete window.PIXI_live2d;
  if (PLD && window.PIXI) {
    // Merge into PIXI.live2d
    for (var key in PLD) {
      if (PLD.hasOwnProperty(key)) {
        window.PIXI.live2d[key] = PLD[key];
      }
    }
  }
})();
