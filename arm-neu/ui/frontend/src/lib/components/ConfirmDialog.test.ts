import { describe, it, expect, vi, afterEach } from 'vitest';
import { renderComponent, screen, fireEvent, cleanup } from '$lib/test-utils';
import ConfirmDialog from './ConfirmDialog.svelte';

const defaultProps = {
	open: true,
	title: 'Delete Item',
	message: 'Are you sure you want to delete this?',
	onconfirm: vi.fn(),
	oncancel: vi.fn()
};

function renderDialog(overrides: Record<string, unknown> = {}) {
	return renderComponent(ConfirmDialog, {
		props: { ...defaultProps, ...overrides }
	});
}

describe('ConfirmDialog', () => {
	afterEach(() => cleanup());

	describe('rendering', () => {
		it('does not render when open is false', () => {
			renderDialog({ open: false });
			expect(screen.queryByText('Delete Item')).not.toBeInTheDocument();
		});

		it('renders title and message when open', () => {
			renderDialog();
			expect(screen.getByText('Delete Item')).toBeInTheDocument();
			expect(screen.getByText('Are you sure you want to delete this?')).toBeInTheDocument();
		});
	});

	describe('props', () => {
		it('shows default confirm label', () => {
			renderDialog();
			expect(screen.getByText('Confirm')).toBeInTheDocument();
		});

		it('shows custom confirm label', () => {
			renderDialog({ confirmLabel: 'Delete' });
			expect(screen.getByText('Delete')).toBeInTheDocument();
		});

		it('applies danger variant class to confirm button', () => {
			renderDialog({ variant: 'danger' });
			const confirmBtn = screen.getByText('Confirm');
			expect(confirmBtn).toHaveClass('confirm-btn-danger');
		});

		it('applies primary variant class to confirm button by default', () => {
			renderDialog();
			const confirmBtn = screen.getByText('Confirm');
			expect(confirmBtn).toHaveClass('confirm-btn-primary');
		});
	});

	describe('interactions', () => {
		it('calls onconfirm when confirm button is clicked', async () => {
			const onconfirm = vi.fn();
			renderDialog({ onconfirm });
			await fireEvent.click(screen.getByText('Confirm'));
			expect(onconfirm).toHaveBeenCalledOnce();
		});

		it('calls oncancel when cancel button is clicked', async () => {
			const oncancel = vi.fn();
			renderDialog({ oncancel });
			await fireEvent.click(screen.getByText('Cancel'));
			expect(oncancel).toHaveBeenCalledOnce();
		});

		it('calls oncancel when backdrop is clicked', async () => {
			const oncancel = vi.fn();
			renderDialog({ oncancel });
			await fireEvent.click(screen.getByLabelText('Close dialog'));
			expect(oncancel).toHaveBeenCalledOnce();
		});

		it('calls oncancel when Escape is pressed', async () => {
			const oncancel = vi.fn();
			renderDialog({ oncancel });
			await fireEvent.keyDown(window, { key: 'Escape' });
			expect(oncancel).toHaveBeenCalledOnce();
		});
	});
});
