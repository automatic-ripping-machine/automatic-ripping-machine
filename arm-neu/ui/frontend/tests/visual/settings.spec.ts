import { test, expect } from '@playwright/test';

test.describe('Settings visual', () => {
    test('loading state', async ({ page }) => {
        let resolve: (v: unknown) => void = () => {};
        await page.route('**/api/settings', (route) => {
            new Promise(r => { resolve = r; }).then(() =>
                route.fulfill({
                    status: 200,
                    contentType: 'application/json',
                    body: JSON.stringify({
                        arm_config: {},
                        arm_metadata: null,
                        naming_variables: null,
                        transcoder_config: null,
                        transcoder_gpu_support: null,
                        transcoder_auth_status: null,
                        gpu_support: null
                    })
                })
            );
        });
        await page.goto('/settings');
        await page.waitForSelector('[aria-busy="true"]', { timeout: 3000 });
        await expect(page).toHaveScreenshot('settings-loading.png', { fullPage: true });
        resolve(undefined);
    });
});
