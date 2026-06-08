import type { DashboardResponse } from '$lib/types/api.gen';

export const emptyDashboard: DashboardResponse = {
    db_available: true,
    arm_online: true,
    active_jobs: [],
    system_info: null,
    drives_online: 0,
    drive_names: {},
    notification_count: 0,
    ripping_enabled: true,
    makemkv_key_valid: null,
    makemkv_key_checked_at: null,
    transcoder_online: true,
    transcoder_stats: null,
    transcoder_system_stats: null,
    active_transcodes: [],
    system_stats: null,
    transcoder_info: null
};

export const emptyJobs = {
    jobs: [],
    total: 0,
    page: 1,
    per_page: 25
};

export const emptyStats = {
    total: 0,
    success: 0,
    failed: 0,
    pending: 0
};
