const puppeteer = require('puppeteer');

(async () => {
  const browser = await puppeteer.launch({ headless: "new" });
  const page = await browser.newPage();
  
  page.on('console', msg => console.log('PAGE LOG:', msg.text()));
  page.on('pageerror', err => console.log('PAGE ERROR:', err.toString()));
  page.on('requestfailed', request => console.log('REQUEST FAILED:', request.url(), request.failure().errorText));

  try {
    await page.goto('http://127.0.0.1:8099/research', { waitUntil: 'networkidle0' });
    await page.waitForTimeout(2000);
  } catch(e) {
    console.log("Nav Error", e);
  }
  
  await browser.close();
})();
