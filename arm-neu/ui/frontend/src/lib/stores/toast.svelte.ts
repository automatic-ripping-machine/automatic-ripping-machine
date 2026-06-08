export type ToastTone = 'success' | 'error' | 'info';

export interface Toast {
	id: number;
	tone: ToastTone;
	title: string;
	body?: string;
}

const AUTO_DISMISS_MS = 4200;
let nextId = 1;

// Module-level rune state. `.value` is read in components for reactivity.
export const toasts = $state<{ value: Toast[] }>({ value: [] });

export function addToast(t: Omit<Toast, 'id'>): number {
	const id = nextId++;
	toasts.value = [...toasts.value, { id, ...t }];
	setTimeout(() => dismissToast(id), AUTO_DISMISS_MS);
	return id;
}

export function dismissToast(id: number): void {
	toasts.value = toasts.value.filter((t) => t.id !== id);
}
