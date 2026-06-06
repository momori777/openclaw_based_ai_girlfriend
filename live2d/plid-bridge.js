/**
 * Bridge shim: wraps pixi-live2d-display v0.5.0-beta for global PIXI context.
 * 
 * Problem: PLD v0.5 UMD expects `@pixi/core` and `@pixi/display` as AMD/CommonJS modules.
 * On CDN PixiJS v7, these submodules don't exist as separate globals.
 * 
 * Solution: Before loading PLD, create stubs so it finds what it needs from window.PIXI.
 */

// Step 1: Make window.PIXI.core and window.PIXI.display available
// PixiJS v7 CDN bundle exposes everything on PIXI directly.
// We create synthetic module-like objects that PLD can consume.
(function() {
  if (typeof window === 'undefined' || !window.PIXI) return;
  
  var P = window.PIXI;
  
  // PLD uses @pixi/core for: Matrix, Texture, Renderer, Shader, etc.
  // All of these exist directly on PIXI in the CDN bundle.
  // PLD uses @pixi/display for: Container, DisplayObject, etc.
  
  // Create stub module objects that reference PIXI globals
  P.core = P.core || {};
  P.display = P.display || {};
  
  // Common imports from @pixi/core that PLD needs:
  var coreExports = [
    'Matrix', 'Texture', 'BaseTexture', 'Resource', 'TextureSource',
    'RenderTexture', 'Rectangle', 'Point', 'ObservablePoint',
    'Shader', 'Program', 'Geometry', 'Buffer', 'State',
    'Renderer', 'AbstractRenderer', 'GLProgram', 'UniformGroup',
    'Filter', 'MaskData', 'MaskSystem',
    'settings', 'utils', 'Ticker',
    'DRAW_MODES', 'FORMATS', 'TYPES', 'SCALE_MODES', 'WRAP_MODES',
    'MIPMAP_MODES', 'GC_MODES', 'PRECISION', 'ENV', 'RENDERER_TYPE',
    'BUFFER_TYPE', 'BUFFER_BITS', 'BLEND_MODES', 'CLEAR_MODES',
    'MSAA_QUALITY',
  ];
  var displayExports = [
    'Container', 'DisplayObject', 'Bounds', 'Transform',
    'TemporaryDisplayObject',
  ];
  
  coreExports.forEach(function(k) {
    if (P[k] !== undefined && !(k in P.core)) P.core[k] = P[k];
  });
  displayExports.forEach(function(k) {
    if (P[k] !== undefined && !(k in P.display)) P.display[k] = P[k];
  });
  
  console.log('[bridge] PIXI.core stubs created:', Object.keys(P.core).length, 'keys');
  console.log('[bridge] PIXI.display stubs created:', Object.keys(P.display).length, 'keys');
})();
