import { test, expect } from '@playwright/test';
import { emptyDashboard, emptyJobs, emptyStats } from '../fixtures/dashboard';

test.describe('Dashboard visual regression', () => {
    test('empty state', async ({ page }) => {
        await page.route('**/api/dashboard', (route) =>
            route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(emptyDashboard) })
        );
        await page.route(/\/api\/jobs($|\?)/, (route) =>
            route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(emptyJobs) })
        );
        await page.route('**/api/jobs/stats', (route) =>
            route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(emptyStats) })
        );

        await page.goto('/');
        await page.waitForLoadState('networkidle');
        await expect(page).toHaveScreenshot('dashboard-empty.png', { fullPage: true });
    });
});
