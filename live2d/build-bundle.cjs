const esbuild = require('esbuild');

esbuild.build({
  entryPoints: ['umd-entry.mjs'],
  bundle: true,
  format: 'iife',
  globalName: '__PLD_BUNDLE__',
  outfile: 'plid-v5-bundle.js',
  // Map @pixi/* imports to our proxy
  alias: {
    '@pixi/core': './pixi-proxy.js',
    '@pixi/display': './pixi-proxy.js',
  },
  external: ['pixi.js'],
}).catch(() => process.exit(1));
