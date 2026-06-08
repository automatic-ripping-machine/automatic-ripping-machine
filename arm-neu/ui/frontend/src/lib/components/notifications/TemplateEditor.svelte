<script lang="ts">
	import { tick } from 'svelte';
	import { EVENT_VARIABLES, EVENT_LABELS, EVENT_DEFAULT_TEMPLATES, type EventKey, FIELD_INPUT_CLASS } from '$lib/types/notifications';
	import type { ChannelTemplate } from '$lib/types/notifications';

	let {
		subscribedEvents,
		templates = $bindable()
	}: { subscribedEvents: string[]; templates: Record<string, ChannelTemplate> } = $props();

	type FieldName = 'title' | 'body';
	type FocusTarget = {
		key: string;
		field: FieldName;
		el: HTMLInputElement | HTMLTextAreaElement;
		start: number;
		end: number;
	};

	// The most recently focused template field + its caret/selection, so a
	// variable-chip click knows where to insert. Captured per event row.
	let active: FocusTarget | null = $state(null);

	function ensure(key: string): ChannelTemplate {
		if (!templates[key]) templates[key] = { title: null, body: null };
		return templates[key];
	}

	function varsFor(key: string): string[] {
		return EVENT_VARIABLES[key as EventKey] ?? [];
	}

	function defaultsFor(key: string): { title: string; body: string } {
		return EVENT_DEFAULT_TEMPLATES[key as EventKey] ?? { title: '', body: '' };
	}

	// Remember the focused field and current caret so a later chip click can
	// insert there even though clicking the chip moves DOM focus.
	function rememberCaret(key: string, field: FieldName, el: HTMLInputElement | HTMLTextAreaElement) {
		active = {
			key,
			field,
			el,
			start: el.selectionStart ?? el.value.length,
			end: el.selectionEnd ?? el.value.length
		};
	}

	// Insert `{varName}` into the last-focused field for `key` at the caret.
	// If no field for this row is focused, append to the title.
	async function insertVariable(key: string, varName: string) {
		const token = `{${varName}}`;
		const tmpl: ChannelTemplate = templates[key] ?? { title: null, body: null };
		const target =
			active && active.key === key
				? active
				: { key, field: 'title' as FieldName, el: null, start: (tmpl.title ?? '').length, end: (tmpl.title ?? '').length };

		const current = (target.field === 'title' ? tmpl.title : tmpl.body) ?? '';
		const start = Math.min(target.start, current.length);
		const end = Math.min(target.end, current.length);
		const next = current.slice(0, start) + token + current.slice(end);

		// Reassign through the bindable so both new keys and nested-field
		// updates trigger reactivity reliably.
		templates = {
			...templates,
			[key]: {
				title: target.field === 'title' ? next || null : tmpl.title ?? null,
				body: target.field === 'body' ? next || null : tmpl.body ?? null
			}
		};

		// Restore focus + place the caret right after the inserted token,
		// once Svelte has flushed the new value to the DOM.
		const caret = start + token.length;
		await tick();
		if (target.el) {
			target.el.focus();
			target.el.setSelectionRange(caret, caret);
			active = { ...target, start: caret, end: caret };
		}
	}
</script>

<div class="space-y-4">
	{#if subscribedEvents.length === 0}
		<p class="text-sm text-gray-500 dark:text-gray-400">Subscribe to an event to customize its template.</p>
	{/if}
	{#each subscribedEvents as key}
		<div class="space-y-2 rounded-md border border-primary/15 bg-page p-3 dark:border-primary/20 dark:bg-primary/5">
			<h4 class="text-sm font-semibold text-gray-700 dark:text-gray-300">{EVENT_LABELS[key as EventKey] ?? key}</h4>
			<label class="flex flex-col gap-1">
				<span class="text-xs font-medium text-gray-600 dark:text-gray-400">Title</span>
				<input
					aria-label={`${key} title`}
					placeholder={defaultsFor(key).title}
					value={templates[key]?.title ?? ''}
					oninput={(e) => {
						ensure(key).title = (e.currentTarget as HTMLInputElement).value || null;
						rememberCaret(key, 'title', e.currentTarget as HTMLInputElement);
					}}
					onfocus={(e) => rememberCaret(key, 'title', e.currentTarget as HTMLInputElement)}
					onkeyup={(e) => rememberCaret(key, 'title', e.currentTarget as HTMLInputElement)}
					onclick={(e) => rememberCaret(key, 'title', e.currentTarget as HTMLInputElement)}
					class={FIELD_INPUT_CLASS}
				/>
			</label>
			<label class="flex flex-col gap-1">
				<span class="text-xs font-medium text-gray-600 dark:text-gray-400">Body</span>
				<textarea
					aria-label={`${key} body`}
					rows="2"
					placeholder={defaultsFor(key).body}
					value={templates[key]?.body ?? ''}
					oninput={(e) => {
						ensure(key).body = (e.currentTarget as HTMLTextAreaElement).value || null;
						rememberCaret(key, 'body', e.currentTarget as HTMLTextAreaElement);
					}}
					onfocus={(e) => rememberCaret(key, 'body', e.currentTarget as HTMLTextAreaElement)}
					onkeyup={(e) => rememberCaret(key, 'body', e.currentTarget as HTMLTextAreaElement)}
					onclick={(e) => rememberCaret(key, 'body', e.currentTarget as HTMLTextAreaElement)}
					class={FIELD_INPUT_CLASS}
				></textarea>
			</label>
			<p class="text-xs text-gray-500 dark:text-gray-400">
				Leave blank to send the default shown above.
			</p>
			<p class="text-xs text-gray-500 dark:text-gray-400">
				Click a variable to insert it{active?.key === key ? ` into the ${active.field}` : ''}:
			</p>
			<div class="flex flex-wrap gap-1">
				{#each varsFor(key) as v}
					<button
						type="button"
						aria-label={`Insert {${v}}`}
						onclick={() => insertVariable(key, v)}
						class="rounded bg-primary/10 px-1.5 py-0.5 text-xs text-primary hover:bg-primary/20 dark:bg-primary/15 dark:hover:bg-primary/25"
					><code>{`{${v}}`}</code></button>
				{/each}
			</div>
		</div>
	{/each}
</div>
