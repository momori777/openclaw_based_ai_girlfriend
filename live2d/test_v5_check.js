const { chromium } = require('playwright');
const path = require('path');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 800, height: 900 } });
  
  page.on('console', msg => {
    if (msg.type() === 'error' || msg.type() === 'warning') {
      console.log('[BROWSER]', msg.type(), msg.text().substring(0, 200));
    }
  });
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
  
  // Check drawable visibility via the model's internal renderer
  const drawableCheck = await page.evaluate(() => {
    if (!window.__model) return 'No model ref';
    
    const im = window.__model.internalModel;
    if (!im) return 'No internalModel';
    
    const drawables = im.drawables;
    if (!drawables) return 'No drawables';
    
    const ids = drawables.getSize ? drawables.getSize() : 'unknown size';
    return { drawablesCount: ids };
  });
  console.log('Drawable check:', drawableCheck);
  
  // Get pixel colors at specific screen positions  
  // Nose would be around center of face (probably 400, 300 in canvas)
  const pixelInfo = await page.evaluate(() => {
    const canvas = document.getElementById('live2d-canvas');
    if (!canvas) return 'No canvas';
    // Can't read pixels from WebGL without preserveDrawingBuffer
    return 'WebGL canvas';
  });
  
  // Since we can't easily check pixels from WebGL, let's just save the screenshot
  const outPath = path.resolve(__dirname, 'media', 'live2d_v5_test2.png');
  await page.screenshot({ path: outPath });
  console.log('Screenshot saved:', outPath);
  
  // Try expressions and capture after each
  const ws = await page.evaluate(() => {
    return new Promise((resolve) => {
      const sock = new WebSocket('ws://localhost:19201');
      const results = [];
      sock.onopen = () => {
        // Cycle through expressions, capture a state after
        const exps = ['exp_03', 'exp_02', 'exp_05', 'exp_04', 'exp_01']; // sad, happy, surprised, angry, neutral
        let i = 0;
        const next = () => {
          if (i >= exps.length) { sock.close(); resolve(results); return; }
          sock.send(JSON.stringify({ type: 'expression', name: exps[i] }));
          results.push({ exp: exps[i], time: Date.now() });
          i++;
          setTimeout(next, 600);
        };
        next();
      };
      sock.onerror = () => resolve('ws error');
      setTimeout(() => resolve('timeout'), 8000);
    });
  });
  console.log('Expression cycle result:', ws);
  
  await page.waitForTimeout(500);
  
  const outPath2 = path.resolve(__dirname, 'media', 'live2d_v5_expressions.png');
  await page.screenshot({ path: outPath2 });
  console.log('Expression screenshot saved:', outPath2);
  
  await browser.close();
  console.log('Done.');
})();
