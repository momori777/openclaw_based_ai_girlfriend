const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 400, height: 300 } });
  
  await page.setContent(`
    <html><body>
    <script src="https://cdn.jsdelivr.net/npm/pixi.js@7.4.2/dist/pixi.min.js"></script>
    <script>
      document.body.textContent = JSON.stringify({
        PIXI_exists: typeof PIXI !== 'undefined',
        PIXI_core_exists: typeof PIXI.core !== 'undefined',
        PIXI_display_exists: typeof PIXI.display !== 'undefined',
        PIXI_keys: Object.keys(PIXI).slice(0, 15),
      });
    </script>
    </body></html>
  `);
  const text = await page.evaluate(() => document.body.textContent);
  console.log(text);
  await browser.close();
})();
