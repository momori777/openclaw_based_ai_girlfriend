const { chromium } = require('playwright');
const path = require('path');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 800, height: 900 } });
  
  page.on('console', msg => console.log('[BROWSER]', msg.type(), msg.text()));
  page.on('pageerror', err => console.error('[PAGE ERROR]', err.message));
  
  // Use HTTP (bridge serves static files)
  await page.goto('http://localhost:19200/test_v5.html', { waitUntil: 'domcontentloaded' });
  
  console.log('Waiting for model load...');
  try {
    await page.waitForFunction(() => {
      const dot = document.getElementById('status-dot');
      return dot && dot.classList.contains('online');
    }, { timeout: 20000 });
    console.log('Model loaded!');
  } catch (e) {
    console.log('Timeout waiting for model. Checking...');
  }
  
  await page.waitForTimeout(2000);
  
  // Test expressions
  console.log('Sending expression via WS...');
  await page.evaluate(() => {
    return new Promise((resolve) => {
      const ws = new WebSocket('ws://localhost:19201');
      ws.onopen = () => {
        ws.send(JSON.stringify({ type: 'expression', name: 'happy' }));
        setTimeout(() => ws.send(JSON.stringify({ type: 'expression', name: 'surprised' })), 1500);
        setTimeout(() => ws.send(JSON.stringify({ type: 'expression', name: 'neutral' })), 3000);
        setTimeout(resolve, 4500);
      };
      ws.onerror = () => { console.log('WS failed'); resolve(); };
      setTimeout(resolve, 6000);
    });
  });
  
  await page.waitForTimeout(1000);
  
  const outPath = path.resolve(__dirname, 'media', 'live2d_v5_test.png');
  await page.screenshot({ path: outPath });
  console.log('Screenshot saved to:', outPath);
  
  await browser.close();
  console.log('Done.');
})();
