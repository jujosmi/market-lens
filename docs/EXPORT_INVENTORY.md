# FULL_APP Export Inventory

P4E release package layout:

- frontend/ — React/TypeScript source, tests, public logo/assets, Supabase migration, package scripts/lockfile, and safe environment examples.
- backend/ — FastAPI source, SEC adapter, engine snapshot, tests, and pinned dependency declarations.
- docs/ — historical sprint reports, notices, source/export verification, P4E acceptance report, and staging checklist.
- scripts/ — local package start/stop helpers.
- Root README and ignore rules.

Excluded: node_modules, dist, .npm-cache, Python virtual environments, pytest/bytecode caches, temporary logs, actual .env files, and machine-specific runtime state. Production build and backend ZIP are separate in P4E_RELEASE_ARTIFACTS.

Exact package paths, sizes, and hashes are in P4E_RELEASE_MANIFEST.json and EXPORT_HASH_MANIFEST.csv.
