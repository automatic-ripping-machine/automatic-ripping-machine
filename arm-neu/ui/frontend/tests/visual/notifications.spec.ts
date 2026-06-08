import { test, expect } from '@playwright/test';

test.describe('Notifications visual', () => {
    test('loading state', async ({ page }) => {
        let resolve: (v: unknown) => void = () => {};
        await page.route('**/api/notifications', (route) => {
            new Promise(r => { resolve = r; }).then(() =>
                route.fulfill({ status: 200, contentType: 'application/json', body: '[]' })
            );
        });
        await page.goto('/notifications');
        await page.waitForSelector('[aria-busy="true"]', { timeout: 3000 });
        await expect(page).toHaveScreenshot('notifications-loading.png', { fullPage: true });
        resolve(undefined);
    });
});
