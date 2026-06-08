import { test, expect } from '@playwright/test';

test.describe('Files visual', () => {
    test('loading state', async ({ page }) => {
        // Provide roots immediately so the page sets currentPath and starts navigating
        await page.route('**/api/files/roots', (route) => {
            route.fulfill({
                status: 200,
                contentType: 'application/json',
                body: JSON.stringify([
                    { key: 'raw', label: 'Raw', path: '/home/arm/media/raw' }
                ])
            });
        });

        // Stall the directory listing so the skeleton is visible
        let resolveList: (v: unknown) => void = () => {};
        await page.route('**/api/files/list**', (route) => {
            new Promise(r => { resolveList = r; }).then(() =>
                route.fulfill({
                    status: 200,
                    contentType: 'application/json',
                    body: JSON.stringify({
                        path: '/home/arm/media/raw',
                        parent: null,
                        readonly: false,
                        entries: []
                    })
                })
            );
        });

        await page.goto('/files');
        await page.waitForSelector('[aria-busy="true"]', { timeout: 3000 });
        await expect(page).toHaveScreenshot('files-loading.png', { fullPage: true });
        resolveList(undefined);
    });
});
