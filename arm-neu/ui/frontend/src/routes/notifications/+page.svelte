<script lang="ts">
	import { onMount } from 'svelte';
	import { fetchNotifications, dismissNotification } from '$lib/api/notifications';
	import { purgeNotifications } from '$lib/api/maintenance';
	import type { NotificationSchema as Notification } from '$lib/types/api.gen';
	import { formatDateTime, timeAgo } from '$lib/utils/format';
	import ConfirmDialog from '$lib/components/ConfirmDialog.svelte';
	import LoadState from '$lib/components/LoadState.svelte';
	import SkeletonCard from '$lib/components/SkeletonCard.svelte';

	let notifications = $state<Notification[]>([]);
	let notifsLoading = $state(true);
	let notifsError = $state<Error | null>(null);
	let dismissing = $state<Set<number>>(new Set());
	let showCleared = $state(false);
	let purging = $state(false);
	let purgeConfirmOpen = $state(false);
	let feedback = $state<{ type: 'success' | 'error'; message: string } | null>(null);

	let filtered = $derived(
		showCleared ? notifications : notifications.filter((n) => !n.seen)
	);

	async function load() {
		notifsLoading = true;
		notifsError = null;
		try {
			notifications = await fetchNotifications();
		} catch (e) {
			notifsError = e instanceof Error ? e : new Error('Failed to load notifications');
		} finally {
			notifsLoading = false;
		}
	}

	async function dismiss(id: number) {
		dismissing = new Set([...dismissing, id]);
		try {
			await dismissNotification(id);
			notifications = notifications.map((n) =>
				n.id === id ? { ...n, seen: true } : n
			);
		} catch {
			// next refresh will reconcile
		} finally {
			const next = new Set(dismissing);
			next.delete(id);
			dismissing = next;
		}
	}

	async function dismissAll() {
		const unseen = notifications.filter((n) => !n.seen);
		if (unseen.length === 0) return;
		const ids = unseen.map((n) => n.id);
		dismissing = new Set(ids);
		await Promise.allSettled(ids.map((id) => dismissNotification(id)));
		notifications = notifications.map((n) => ({ ...n, seen: true }));
		dismissing = new Set();
	}

	let unseenCount = $derived(notifications.filter((n) => !n.seen).length);
	let clearedCount = $derived(notifications.filter((n) => n.seen).length);

	async function handlePurge() {
		purging = true;
		purgeConfirmOpen = false;
		try {
			const result = await purgeNotifications();
			feedback = { type: 'success', message: `Purged ${result.count} cleared notification${result.count !== 1 ? 's' : ''}` };
			await load();
		} catch (e) {
			feedback = { type: 'error', message: e instanceof Error ? e.message : 'Purge failed' };
		}
		purging = false;
	}

	onMount(() => {
		load();
	});
</script>

<svelte:head>
	<title>ARM - Notifications</title>
</svelte:head>

<div class="space-y-6">
	{#if feedback}
		<div class="rounded-lg px-4 py-2.5 text-sm {feedback.type === 'success'
			? 'bg-green-500/10 text-green-700 dark:text-green-400'
			: 'bg-red-500/10 text-red-700 dark:text-red-400'}">
			{feedback.message}
			<button onclick={() => { feedback = null; }} class="ml-2 opacity-60 hover:opacity-100">&times;</button>
		</div>
	{/if}

	<div class="flex items-center justify-between">
		<div class="flex items-center gap-3">
			<h1 class="text-2xl font-bold text-gray-900 dark:text-white">Notifications</h1>
			{#if unseenCount > 0}
				<span class="rounded-full bg-amber-500 px-2.5 py-0.5 text-xs font-medium text-white">{unseenCount} new</span>
			{/if}
		</div>
		<div class="flex items-center gap-3">
			<label class="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400">
				<input
					type="checkbox"
					bind:checked={showCleared}
					class="h-4 w-4 rounded-sm border-primary/25 text-primary focus:ring-primary dark:border-primary/30 dark:bg-primary/10"
				/>
				Show dismissed
			</label>
			{#if clearedCount > 0}
				<button
					type="button"
					onclick={() => (purgeConfirmOpen = true)}
					disabled={purging}
					class="rounded-lg px-3 py-1.5 text-sm font-medium text-red-600 hover:bg-red-500/10 disabled:opacity-50 dark:text-red-400 dark:hover:bg-red-500/15 transition-colors"
				>
					{purging ? 'Purging...' : 'Purge Cleared'}
				</button>
			{/if}
			{#if unseenCount > 0}
				<button
					onclick={dismissAll}
					class="rounded-lg px-3 py-1.5 text-sm font-medium bg-primary/5 text-gray-700 ring-1 ring-primary/25 hover:bg-primary/10 dark:bg-primary/10 dark:text-gray-200 dark:ring-primary/30 dark:hover:bg-primary/15 transition-colors"
				>
					Dismiss All
				</button>
			{/if}
		</div>
	</div>

	<LoadState
		data={notifications}
		loading={notifsLoading}
		error={notifsError}
		isEmpty={() => false}
		transitionKey="notifications-list"
	>
		{#snippet loadingSlot()}
			<div class="space-y-3">
				{#each Array(4) as _}
					<SkeletonCard lines={3} />
				{/each}
			</div>
		{/snippet}
		{#snippet ready(items)}
			{#if filtered.length === 0}
				<div class="rounded-lg border border-primary/20 bg-surface p-6 text-center shadow-xs dark:border-primary/20 dark:bg-surface-dark">
					<svg class="mx-auto h-12 w-12 text-gray-300 dark:text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24" stroke-width="1.5">
						<path stroke-linecap="round" stroke-linejoin="round" d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
					</svg>
					<p class="mt-3 text-sm font-medium text-gray-500 dark:text-gray-400">
						{showCleared ? 'No notifications' : 'No new notifications'}
					</p>
				</div>
			{:else}
				<div class="space-y-3">
					{#each filtered as notif (notif.id)}
						<div class="rounded-lg border border-primary/20 bg-surface p-4 shadow-xs dark:border-primary/20 dark:bg-surface-dark {notif.seen ? 'opacity-60' : ''}">
							<div class="flex items-start justify-between gap-4">
								<div class="min-w-0 flex-1">
									<div class="flex items-center gap-2">
										{#if !notif.seen}
											<div class="h-2 w-2 shrink-0 rounded-full bg-amber-500"></div>
										{/if}
										<h3 class="font-medium text-gray-900 dark:text-white">{notif.title ?? 'Notification'}</h3>
									</div>
									{#if notif.message}
										<p class="mt-1 text-sm text-gray-600 dark:text-gray-400">{notif.message}</p>
									{/if}
									{#if notif.trigger_time}
										<p class="mt-1.5 text-xs text-gray-400 dark:text-gray-500" title={formatDateTime(notif.trigger_time)}>
											{timeAgo(notif.trigger_time)}
										</p>
									{/if}
								</div>
								{#if !notif.seen}
									<button
										onclick={() => dismiss(notif.id)}
										disabled={dismissing.has(notif.id)}
										class="shrink-0 rounded-lg px-3 py-1.5 text-xs font-medium bg-primary/5 text-gray-600 ring-1 ring-primary/25 hover:bg-primary/10 dark:bg-primary/10 dark:text-gray-300 dark:ring-primary/30 dark:hover:bg-primary/15 disabled:opacity-50 transition-colors"
									>
										{dismissing.has(notif.id) ? '...' : 'Dismiss'}
									</button>
								{/if}
							</div>
						</div>
					{/each}
				</div>
			{/if}
		{/snippet}
		{#snippet empty()}
			<p class="py-8 text-center text-sm text-gray-500 dark:text-gray-400">No notifications.</p>
		{/snippet}
	</LoadState>
</div>

<ConfirmDialog
	open={purgeConfirmOpen}
	title="Purge Notifications"
	message="Permanently delete all cleared notifications from the database? This cannot be undone."
	confirmLabel="Purge"
	variant="danger"
	onconfirm={handlePurge}
	oncancel={() => (purgeConfirmOpen = false)}
/>
