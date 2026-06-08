<script lang="ts">
	interface Props {
		statusFilter: string;
		videoTypeFilter: string;
		disctypeFilter: string;
		daysFilter: number | undefined;
		onstatusfilter: (value: string) => void;
		onvideotypefilter: (value: string) => void;
		ondisctypefilter: (value: string) => void;
		ondaysfilter: (value: number | undefined) => void;
		onsearch: (e: Event) => void;
	}

	let {
		statusFilter,
		videoTypeFilter,
		disctypeFilter,
		daysFilter,
		onstatusfilter,
		onvideotypefilter,
		ondisctypefilter,
		ondaysfilter,
		onsearch
	}: Props = $props();

	const selectClasses = 'rounded-lg border border-primary/25 bg-primary/5 px-3 py-2 text-sm dark:border-primary/30 dark:bg-primary/10 dark:text-white';
</script>

<div class="flex flex-wrap items-center gap-3">
	<input
		type="text"
		placeholder="Search titles..."
		oninput={onsearch}
		class="lcars-input w-64 rounded-lg border border-primary/25 bg-primary/5 px-3 py-2 text-sm dark:border-primary/30 dark:bg-primary/10 dark:text-white"
	/>

	<div class="h-6 w-px bg-primary/20 dark:bg-primary/20"></div>

	<select
		value={statusFilter}
		onchange={(e) => onstatusfilter((e.target as HTMLSelectElement).value)}
		class={selectClasses}
	>
		<option value="">All Status</option>
		<option value="active">Active</option>
		<option value="success">Success</option>
		<option value="fail">Failed</option>
		<option value="waiting">Waiting</option>
	</select>

	<select
		value={videoTypeFilter}
		onchange={(e) => onvideotypefilter((e.target as HTMLSelectElement).value)}
		class={selectClasses}
	>
		<option value="">All Types</option>
		<option value="movie">Movie</option>
		<option value="series">Series</option>
		<option value="music">Music</option>
	</select>

	<select
		value={disctypeFilter}
		onchange={(e) => ondisctypefilter((e.target as HTMLSelectElement).value)}
		class={selectClasses}
	>
		<option value="">All Discs</option>
		<option value="bluray">Blu-ray</option>
		<option value="dvd">DVD</option>
		<option value="music">CD</option>
		<option value="data">Data</option>
	</select>

	<select
		value={daysFilter ?? ''}
		onchange={(e) => {
			const val = (e.target as HTMLSelectElement).value;
			ondaysfilter(val ? Number(val) : undefined);
		}}
		class={selectClasses}
	>
		<option value="">All Time</option>
		<option value="7">7 days</option>
		<option value="30">30 days</option>
		<option value="90">90 days</option>
	</select>
</div>
