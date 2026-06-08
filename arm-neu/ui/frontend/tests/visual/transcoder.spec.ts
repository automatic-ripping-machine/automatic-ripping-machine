import { test, expect } from '@playwright/test';

test.describe('Transcoder visual', () => {
    test('loading state', async ({ page }) => {
        let resolve: (v: unknown) => void = () => {};
        await page.route('**/api/transcoder/**', (route) => {
            new Promise(r => { resolve = r; }).then(() =>
                route.fulfill({
                    status: 200,
                    contentType: 'application/json',
                    body: JSON.stringify({ jobs: [], total: 0 })
                })
            );
        });
        await page.goto('/transcoder');
        await page.waitForSelector('[aria-busy="true"]', { timeout: 3000 });
        await expect(page).toHaveScreenshot('transcoder-loading.png', { fullPage: true });
        resolve(undefined);
    });
});
