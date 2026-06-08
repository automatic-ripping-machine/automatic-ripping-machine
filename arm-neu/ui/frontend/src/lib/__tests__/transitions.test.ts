import { describe, it, expect, vi, beforeEach } from 'vitest';

describe('transitions', () => {
    beforeEach(() => {
        vi.resetModules();
    });

    it('exports send and receive from crossfade', async () => {
        const mod = await import('../transitions');
        expect(typeof mod.send).toBe('function');
        expect(typeof mod.receive).toBe('function');
    });

    it('fadeIn has duration 150 when reduced-motion is not set', async () => {
        vi.stubGlobal('matchMedia', vi.fn().mockReturnValue({ matches: false }));
        const mod = await import('../transitions');
        expect(mod.fadeIn.duration).toBe(150);
    });

    it('fadeIn has duration 0 when reduced-motion is preferred', async () => {
        vi.stubGlobal('matchMedia', vi.fn().mockReturnValue({ matches: true }));
        const mod = await import('../transitions');
        expect(mod.fadeIn.duration).toBe(0);
    });

    it('fadeOut mirrors fadeIn duration', async () => {
        vi.stubGlobal('matchMedia', vi.fn().mockReturnValue({ matches: false }));
        const mod = await import('../transitions');
        expect(mod.fadeOut.duration).toBe(mod.fadeIn.duration);
    });
});
