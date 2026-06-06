/**
 * Entry for esbuild: IIFE that creates PIXI.live2d.
 * Uses esbuild resolve alias to map @pixi/core → ./pixi-proxy.js and @pixi/display → ./pixi-proxy.js
 */
import * as PLD from 'pixi-live2d-display';
import 'pixi-live2d-display/cubism4';

// Attach to global
if (typeof window !== 'undefined' && window.PIXI) {
  window.PIXI.live2d = PLD;
  console.log('[PLD] Mounted to PIXI.live2d:', Object.keys(window.PIXI.live2d).length, 'keys');
}
