const { chromium } = require('playwright');
const path = require('path');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 800, height: 900 } });
  
  // Capture ALL errors with stack trace
  page.on('pageerror', err => {
    console.error('[PAGE ERROR]', err.message);
    if (err.stack) console.error('  Stack:', err.stack.split('\n').slice(0, 5).join('\n  '));
  });
  
  page.on('console', msg => {
    if (msg.type() === 'error') {
      console.log('[CONSOLE ERROR]', msg.text().substring(0, 300));
    }
  });
  
  await page.goto('http://localhost:19200/test_v5.html', { waitUntil: 'domcontentloaded' });
  
  try {
    await page.waitForFunction(() => {
      const dot = document.getElementById('status-dot');
      return dot && dot.classList.contains('online');
    }, { timeout: 30000 });
  } catch (e) {
    console.log('Model load timeout');
  }
  
  // Wait more to capture any delayed errors
  await page.waitForTimeout(3000);
  
  console.log('\nDone.');
  await browser.close();
})();
