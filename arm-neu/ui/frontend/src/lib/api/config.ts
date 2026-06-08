export interface AppConfig {
	transcoder_enabled: boolean;
}

export async function fetchConfig(): Promise<AppConfig> {
	const res = await fetch('/api/config');
	if (!res.ok) throw new Error(`Config fetch failed: ${res.status}`);
	return (await res.json()) as AppConfig;
}
