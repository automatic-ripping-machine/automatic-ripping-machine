/** Shared factory for directory/file entry objects used across file-browser tests. */
export interface DirEntry {
	name: string;
	type: 'file' | 'directory';
	size: number;
	modified: string;
	extension: string;
	category: string;
	permissions: string;
	owner: string;
	group: string;
}

const entryDefaults: DirEntry = {
	name: 'untitled',
	type: 'file',
	size: 0,
	modified: '2025-06-15T12:00:00Z',
	extension: '',
	category: 'directory',
	permissions: 'rwxr-xr-x',
	owner: 'arm',
	group: 'arm'
};

export function createDirEntry(overrides: Partial<DirEntry> = {}): DirEntry {
	const entry = { ...entryDefaults, ...overrides };
	// Auto-set category from type if not explicitly overridden
	if (!overrides.category) {
		entry.category = entry.type === 'directory' ? 'directory' : 'video';
	}
	return entry;
}

export function createFileEntry(name: string, size: number, ext = 'mkv'): DirEntry {
	return createDirEntry({ name, type: 'file', size, extension: ext, category: 'video' });
}

export function createFolderEntry(name: string, modified?: string): DirEntry {
	return createDirEntry({ name, type: 'directory', size: 0, ...(modified ? { modified } : {}) });
}
