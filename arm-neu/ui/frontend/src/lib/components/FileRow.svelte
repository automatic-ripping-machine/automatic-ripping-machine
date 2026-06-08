<script lang="ts">
	import type { FileEntry } from '$lib/types/api.gen';
	import { formatBytes, formatDateTime } from '$lib/utils/format';
	import FileIcon from './FileIcon.svelte';
	import Skeleton from './Skeleton.svelte';

	interface Props {
		entry?: FileEntry;
		currentPath?: string | null;
		selected?: boolean;
		readonly?: boolean;
		onnavigate?: (path: string) => void;
		onrename?: (path: string, name: string) => void;
		ondelete?: (path: string, name: string) => void;
		ontoggle?: (path: string) => void;
		onfixpermissions?: (path: string, name: string) => void;
	}

	let { entry, currentPath, selected = false, readonly: ro = false, onnavigate, onrename, ondelete, ontoggle, onfixpermissions }: Props = $props();

	let editing = $state(false);
	let editName = $state('');

	let fullPath = $derived((currentPath ?? '') + '/' + (entry?.name ?? ''));

	function startRename() {
		editName = entry?.name ?? '';
		editing = true;
	}

	function confirmRename() {
		if (editName && editName !== entry?.name) {
			onrename?.(fullPath, editName);
		}
		editing = false;
	}

	function cancelRename() {
		editing = false;
	}

	function handleKeydown(e: KeyboardEvent) {
		if (e.key === 'Enter') confirmRename();
		if (e.key === 'Escape') cancelRename();
	}

	function handleClick() {
		if (entry?.type === 'directory') {
			onnavigate?.(fullPath);
		}
	}
</script>

{#if !entry}
	<tr aria-busy="true">
		{#each { length: 6 } as _}
			<td class="p-2"><Skeleton variant="line" width="80%" height="1rem" /></td>
		{/each}
	</tr>
{:else}
<tr class="border-b border-gray-100 hover:bg-gray-50 dark:border-gray-700/50 dark:hover:bg-gray-800/50 {selected ? 'bg-primary/5 dark:bg-primary/10' : ''}">
	<!-- Checkbox -->
	<td class="w-10 px-3 py-2">
		<input
			type="checkbox"
			checked={selected}
			onchange={() => ontoggle?.(fullPath)}
			class="h-4 w-4 rounded border-gray-300 text-primary accent-primary dark:border-gray-600"
		/>
	</td>

	<!-- Name -->
	<td class="px-3 py-2">
		{#if editing}
			<div class="flex items-center gap-2">
				<FileIcon category={entry.category} />
				<input
					type="text"
					bind:value={editName}
					onkeydown={handleKeydown}
					class="flex-1 rounded border border-gray-300 bg-white px-2 py-1 text-sm dark:border-gray-600 dark:bg-gray-800 dark:text-white"
				/>
				<button
					type="button"
					onclick={confirmRename}
					class="rounded p-1 text-green-600 hover:bg-green-50 dark:hover:bg-green-900/20"
					title="Confirm"
				>
					<svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
					</svg>
				</button>
				<button
					type="button"
					onclick={cancelRename}
					class="rounded p-1 text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-700"
					title="Cancel"
				>
					<svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
					</svg>
				</button>
			</div>
		{:else}
			<button
				type="button"
				onclick={handleClick}
				class="flex items-center gap-2 {entry.type === 'directory' ? 'cursor-pointer hover:text-primary dark:hover:text-primary-dark' : 'cursor-default'}"
			>
				<FileIcon category={entry.category} />
				<span class="text-sm text-gray-900 dark:text-white">{entry.name}</span>
			</button>
		{/if}
	</td>

	<!-- Permissions -->
	<td class="hidden px-3 py-2 lg:table-cell">
		{#if entry.permissions}
			<code class="text-xs text-gray-400 dark:text-gray-500">{entry.owner}:{entry.group} {entry.permissions}</code>
		{/if}
	</td>

	<!-- Size -->
	<td class="px-3 py-2 text-right text-sm text-gray-500 dark:text-gray-400">
		{entry.size ? formatBytes(entry.size) : '--'}
	</td>

	<!-- Modified -->
	<td class="hidden px-3 py-2 text-sm text-gray-500 dark:text-gray-400 md:table-cell">
		{formatDateTime(entry.modified)}
	</td>

	<!-- Actions -->
	<td class="px-3 py-2 text-right">
		<div class="flex items-center justify-end gap-1">
			<!-- Fix permissions -->
			<button
				type="button"
				onclick={() => onfixpermissions?.(fullPath, entry.name)}
				disabled={ro}
				class="rounded p-1.5 text-gray-400 hover:bg-blue-50 hover:text-blue-600 dark:hover:bg-blue-900/20 dark:hover:text-blue-400 disabled:opacity-30 disabled:pointer-events-none"
				title={ro ? 'Read-only mount' : 'Fix permissions'}
			>
				<svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
				</svg>
			</button>
			<!-- Rename -->
			<button
				type="button"
				onclick={startRename}
				disabled={ro}
				class="rounded p-1.5 text-gray-400 hover:bg-gray-100 hover:text-gray-600 dark:hover:bg-gray-700 dark:hover:text-gray-300 disabled:opacity-30 disabled:pointer-events-none"
				title={ro ? 'Read-only mount' : 'Rename'}
			>
				<svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
				</svg>
			</button>
			<!-- Delete -->
			<button
				type="button"
				onclick={() => ondelete?.(fullPath, entry.name)}
				disabled={ro}
				class="rounded p-1.5 text-gray-400 hover:bg-red-50 hover:text-red-600 dark:hover:bg-red-900/20 dark:hover:text-red-400 disabled:opacity-30 disabled:pointer-events-none"
				title={ro ? 'Read-only mount' : 'Delete'}
			>
				<svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
				</svg>
			</button>
		</div>
	</td>
</tr>
{/if}
