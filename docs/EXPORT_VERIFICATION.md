# FULL_APP Export Verification

## P4E release-candidate verification

- Built from the authoritative frontend and backend project trees.
- The previous pre-P4E FULL_APP remains preserved as the sibling directory FULL_APP_PRE_P4E_20261118, with its original 115-file contents hash-verified.
- Frontend and backend source files are compared by relative path and SHA-256 in EXPORT_HASH_MANIFEST.csv.
- Safe .env.example and .env.production.example are included; actual .env* files are excluded.
- Virtual environments, dependency directories, build output, caches, temporary logs, runtime state, and workstation-specific paths in current setup instructions are excluded or generalized.
- Exact candidate contents, bytes, and hashes are in P4E_RELEASE_MANIFEST.json. That manifest excludes its own file hash from the canonical release ID; its own SHA-256 is recorded in the completion report.
- This documentation does not claim a Git history or deployment.

See P4E_STAGING_CHECKLIST.md for required owner confirmations and staging steps.
