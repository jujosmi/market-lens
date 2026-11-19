# Source Hash Comparison

All included frontend and backend files were compared with the authoritative project trees using SHA-256.

- Frontend source files: 69; mismatches: 0.
- Backend source files: 35; mismatches: 0.
- Sanitized omissions: build output, package installs, virtual environments, caches, bytecode, runtime logs, actual local environment files, and the root historical P2A report copy.
- The historical P2A report remains preserved under docs/history.
- Export-only reports, prior sprint documentation, launch scripts, and package docs are marked EXPORT_ONLY in EXPORT_HASH_MANIFEST.csv.

The deterministic release ID and complete inventory are in docs/P4E_RELEASE_MANIFEST.json; the JSON manifest is not included in its own hash list.
