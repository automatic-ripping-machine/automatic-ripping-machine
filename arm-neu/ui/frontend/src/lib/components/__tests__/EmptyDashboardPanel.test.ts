import { describe, it, expect, afterEach } from 'vitest';
import { renderComponent, screen, cleanup } from '$lib/test-utils';
import EmptyDashboardPanel from '../EmptyDashboardPanel.svelte';

describe('EmptyDashboardPanel', () => {
    afterEach(() => cleanup());

    it('renders the no-rips-or-transcodes message', () => {
        renderComponent(EmptyDashboardPanel, {
            props: { drivesOnline: 1, armOnline: true, transcoderOnline: true }
        });
        expect(screen.getByText('No active rips or transcodes')).toBeInTheDocument();
    });

    it('pluralizes drive count correctly', () => {
        renderComponent(EmptyDashboardPanel, {
            props: { drivesOnline: 2, armOnline: true, transcoderOnline: true }
        });
        expect(screen.getByText(/2 drives online/)).toBeInTheDocument();
    });

    it('uses singular for one drive', () => {
        renderComponent(EmptyDashboardPanel, {
            props: { drivesOnline: 1, armOnline: true, transcoderOnline: true }
        });
        expect(screen.getByText(/1 drive online/)).toBeInTheDocument();
    });

    it('surfaces ARM offline state', () => {
        renderComponent(EmptyDashboardPanel, {
            props: { drivesOnline: 1, armOnline: false, transcoderOnline: true }
        });
        expect(screen.getByText(/ARM offline/)).toBeInTheDocument();
    });

    it('surfaces transcoder offline state', () => {
        renderComponent(EmptyDashboardPanel, {
            props: { drivesOnline: 1, armOnline: true, transcoderOnline: false }
        });
        expect(screen.getByText(/transcoder offline/)).toBeInTheDocument();
    });
});
