const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 800, height: 900 } });
  
  page.on('pageerror', err => console.error('[PAGE ERROR]', err.message));
  
  await page.goto('http://localhost:19200/test_v5.html', { waitUntil: 'domcontentloaded' });
  
  try {
    await page.waitForFunction(() => {
      const dot = document.getElementById('status-dot');
      return dot && dot.classList.contains('online');
    }, { timeout: 30000 });
  } catch (e) {
    console.log('Model load timeout');
  }
  
  await page.waitForTimeout(1000);
  
  // Check clipping/mask status
  const maskInfo = await page.evaluate(() => {
    const m = window.__model;
    if (!m) return 'No model';
    const im = m.internalModel;
    if (!im || !im.renderer) return 'No renderer';
    
    const cm = im.renderer._clippingManager;
    if (!cm) return 'No clipping manager';
    
    try {
      const clipCount = cm._clippingMaskCount;
      const clipContexts = cm._clippingContextListForMask;
      return {
        clippingMaskCount: clipCount,
        hasClippingContexts: !!clipContexts,
        useHighPrecision: im.renderer._useHighPrecisionMask,
      };
    } catch(e) {
      return 'Error: ' + e.message;
    }
  });
  console.log('Mask info:', maskInfo);
  
  // Take screenshot at full size with preserveDrawingBuffer
  // Actually the canvas already has rendering, take screenshot
  const outPath = path.resolve(__dirname, 'media', 'live2d_v5_final.png');
  await page.screenshot({ path: outPath, fullPage: false });
  console.log('Screenshot saved:', outPath);
  console.log('Size:', fs.statSync(outPath).size, 'bytes');
  
  // Also capture the WebGL canvas content via toDataURL
  const canvasContent = await page.evaluate(() => {
    const canvas = document.getElementById('live2d-canvas');
    if (!canvas) return 'No canvas';
    // WebGL canvas with preserveDrawingBuffer: false won't work with toDataURL
    // But we can check if it has content by looking at the renderer
    return 'canvas present: ' + (canvas.width + 'x' + canvas.height);
  });
  console.log('Canvas:', canvasContent);
  
  await browser.close();
  console.log('\n=== MANUAL VERIFICATION NEEDED ===');
  console.log('Open http://localhost:19200/test_v5.html in a browser');
  console.log('Check if nose, mouth, eyes are visible');
  console.log('Compare with http://localhost:19200/index.html (old v0.3)');
})();
