import { test, expect } from '@playwright/test';

const mockJob = {
    job_id: 42,
    title: 'Sample Movie',
    title_auto: 'Sample Movie',
    title_manual: null,
    label: 'SAMPLE_MOVIE',
    year: '2024',
    year_auto: '2024',
    year_manual: null,
    status: 'success',
    stage: null,
    arm_version: '2.0.0',
    crc_id: null,
    logfile: null,
    start_time: '2024-01-01T10:00:00',
    stop_time: '2024-01-01T11:00:00',
    job_length: '3600',
    no_of_titles: 1,
    video_type: 'movie',
    video_type_auto: 'movie',
    video_type_manual: null,
    imdb_id: null,
    imdb_id_auto: null,
    imdb_id_manual: null,
    poster_url: null,
    poster_url_auto: null,
    poster_url_manual: null,
    devpath: '/dev/sr0',
    mountpoint: '/mnt/sr0',
    hasnicetitle: true,
    errors: null,
    disctype: 'dvd',
    path: '/home/arm/media/completed/Sample_Movie_2024',
    raw_path: '/home/arm/media/raw/Sample_Movie_2024',
    transcode_path: null,
    artist: null,
    artist_auto: null,
    artist_manual: null,
    album: null,
    album_auto: null,
    album_manual: null,
    source_type: 'disc',
    tracks_total: 1,
    tracks_ripped: 1,
    season: null,
    season_auto: null,
    season_manual: null,
    multi_title: false,
    disc_number: null,
    disc_total: null,
    config: null,
    tracks: []
};

test.describe('Job detail visual', () => {
    test('loading state', async ({ page }) => {
        let resolveJob: (v: unknown) => void = () => {};
        await page.route('**/api/jobs/42', (route) => {
            new Promise(r => { resolveJob = r; }).then(() =>
                route.fulfill({
                    status: 200,
                    contentType: 'application/json',
                    body: JSON.stringify(mockJob)
                })
            );
        });
        // Stub out secondary requests so they don't interfere
        await page.route('**/api/jobs/42/naming-preview', (route) =>
            route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ tracks: [] }) })
        );
        await page.route('**/api/logs/transcoder/arm-job/42', (route) =>
            route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ found: false }) })
        );
        await page.goto('/jobs/42');
        await page.waitForSelector('[aria-busy="true"]', { timeout: 3000 });
        await expect(page).toHaveScreenshot('job-detail-loading.png', { fullPage: true });
        resolveJob(undefined);
    });
});
