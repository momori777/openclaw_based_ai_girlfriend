const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ 
    headless: false,
    args: ['--disable-gpu', '--no-sandbox', '--enable-webgl', '--use-gl=swiftshader']
  });
  const page = await browser.newPage({ viewport: { width: 1280, height: 720 } });

  page.on('console', msg => {
    console.log(`[${msg.type()}] ${msg.text()}`);
  });
  page.on('pageerror', err => {
    console.error(`[PAGE ERROR] ${err.message}`);
  });

  await page.goto('http://localhost:8080/live2d/index.html', { waitUntil: 'networkidle', timeout: 30000 });

  await page.waitForTimeout(8000);

  await page.screenshot({ path: 'D:\\AI_Girlfriend\\index_test.png', fullPage: true });
  console.log('Screenshot saved');

  const canvasCount = await page.locator('canvas').count();
  console.log(`Canvas count: ${canvasCount}`);
  if (canvasCount > 0) {
    const bbox = await page.locator('canvas').first().boundingBox();
    console.log(`Canvas size: ${JSON.stringify(bbox)}`);
  }

  await browser.close();
})();
