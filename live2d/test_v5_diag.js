const { chromium } = require('playwright');
const path = require('path');

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
  
  // Check all drawable-related properties
  const info = await page.evaluate(() => {
    const m = window.__model;
    if (!m) return 'No model';
    const im = m.internalModel;
    if (!im) return 'No internalModel';
    
    const result = {};
    result.imKeys = Object.keys(im);
    
    // Check renderer for drawable info
    if (im.renderer) {
      result.rendererKeys = Object.keys(im.renderer);
      // Check clipping manager 
      if (im.renderer._clippingManager) {
        result.clippingManager = 'exists';
      }
    }
    
    // Check if model has getDrawableCount / getDrawableIds
    if (im.coreModel) {
      const cm = im.coreModel;
      result.coreModelType = cm.constructor.name;
      try { result.drawableCount = cm.getDrawableCount(); } catch(e) { result.drawableCountErr = e.message; }
      try { result.drawableIds = cm.getDrawableIds(); } catch(e) { result.drawableIdsErr = e.message; }
    }
    
    return result;
  });
  console.log('Model info:', JSON.stringify(info, null, 2));
  
  // Take screenshot with neutral expression
  const outPath = path.resolve(__dirname, 'media', 'live2d_v5_neutral.png');
  await page.screenshot({ path: outPath });
  console.log('Screenshot saved:', outPath);
  console.log('File size:', require('fs').statSync(outPath).size, 'bytes');
  
  await browser.close();
  console.log('Done.');
})();
