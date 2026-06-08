import { describe, it, expect, afterEach } from 'vitest';
import { renderComponent, screen, fireEvent, cleanup } from '$lib/test-utils';
import SchemaField from '../SchemaField.svelte';
import type { CatalogField } from '$lib/types/notifications';

function field(over: Partial<CatalogField>): CatalogField {
	return { key: 'k', label: 'Label', type: 'string', private: false, required: false, ...over };
}

describe('SchemaField', () => {
	afterEach(() => cleanup());

	it('renders a text input for string', () => {
		renderComponent(SchemaField, { props: { field: field({}), value: '' } });
		const input = screen.getByLabelText('Label') as HTMLInputElement;
		expect(input.type).toBe('text');
	});

	it('renders a password input when private', () => {
		renderComponent(SchemaField, { props: { field: field({ private: true, label: 'Secret' }), value: '' } });
		expect((screen.getByLabelText('Secret') as HTMLInputElement).type).toBe('password');
	});

	it('renders a checkbox for bool', () => {
		renderComponent(SchemaField, { props: { field: field({ type: 'bool', label: 'Flag' }), value: false } });
		expect((screen.getByLabelText('Flag') as HTMLInputElement).type).toBe('checkbox');
	});

	it('renders a select for choice with values', () => {
		renderComponent(SchemaField, { props: { field: field({ type: 'choice', label: 'Fmt', values: ['a', 'b'] }), value: 'a' } });
		const sel = screen.getByLabelText('Fmt') as HTMLSelectElement;
		expect(sel.tagName).toBe('SELECT');
		expect(sel.options.length).toBe(2);
	});

	it('renders a number input for int', () => {
		renderComponent(SchemaField, { props: { field: field({ type: 'int', label: 'Num' }), value: 0 } });
		expect((screen.getByLabelText('Num') as HTMLInputElement).type).toBe('number');
	});

	it('marks required fields', () => {
		renderComponent(SchemaField, { props: { field: field({ required: true }), value: '' } });
		expect((screen.getByLabelText('Label') as HTMLInputElement).required).toBe(true);
	});

	it('private field with <hidden> value renders empty + keep-current placeholder', () => {
		renderComponent(SchemaField, {
			props: { field: field({ key: 'tok', label: 'Token', private: true, required: true }), value: '<hidden>' }
		});
		const input = screen.getByLabelText('Token') as HTMLInputElement;
		expect(input.type).toBe('password');
		expect(input.value).toBe('');
		expect(input.placeholder).toMatch(/leave blank to keep/i);
	});

	it('private field clears <hidden> sentinel on first input', async () => {
		renderComponent(SchemaField, {
			props: { field: field({ key: 'tok', label: 'Token', private: true, required: true }), value: '<hidden>' }
		});
		const input = screen.getByLabelText('Token') as HTMLInputElement;
		await fireEvent.input(input, { target: { value: 'newval' } });
		expect(input.value).toBe('newval');
	});

	it('non-private field with <hidden> value renders the literal as-is', () => {
		renderComponent(SchemaField, {
			props: { field: field({ key: 'thread', label: 'Thread' }), value: '<hidden>' }
		});
		expect((screen.getByLabelText('Thread') as HTMLInputElement).value).toBe('<hidden>');
	});

	it('private field with normal value renders as password with that value', () => {
		renderComponent(SchemaField, {
			props: { field: field({ key: 'tok', label: 'Token', private: true }), value: 'normal-secret' }
		});
		const input = screen.getByLabelText('Token') as HTMLInputElement;
		expect(input.type).toBe('password');
		expect(input.value).toBe('normal-secret');
	});
});
