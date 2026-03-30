const { chromium } = require('playwright');

(async () => {
    const browser = await chromium.launch();
    const page = await browser.newPage();

    page.on('console', msg => {
        if (msg.type() === 'error') {
            console.log(`PAGE ERROR: ${msg.text()}`);
        } else {
            console.log(`PAGE LOG: ${msg.text()}`);
        }
    });

    page.on('pageerror', error => {
        console.log(`UNCAUGHT EXCEPTION: ${error.message}`);
    });

    try {
        await page.goto('http://localhost:8099/coop', { waitUntil: 'networkidle' });
    } catch (e) {
        console.log("Error loading page:", e);
    }

    await page.waitForTimeout(3000);
    await browser.close();
})();
