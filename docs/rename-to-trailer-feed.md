# Trailer Feed rename

Verified 2026-10-03. Display name: **Trailer Feed**. Technical slug: `trailer-feed`.

- GitHub: `gordo-v1su4/trailer-feed`, public, default branch `main`.
- Frontend: `https://trailer-feed.vercel.app`; the existing Vercel project and Git connection were renamed without replacing them.
- Catalog: `https://media.v1su4.dev/trailer-feed`, Docker `trailer-feed-api`, loopback port 18100, runtime `/opt/trailer-feed`, updater `trailer-feed-update.timer`.
- Database: `trailer-feed-data:/data/trailer-feed.sqlite`. Migration preserved 25 document rows (5 projects), 14 upload rows, 2 session rows and 1 deleted-run tombstone. SQLite integrity and session/tombstone equality passed before verification logins.
- Storage: `trailer-feed`, 1010 objects / 311055416 bytes. Every copied object matched its original SHA-256. Public-read policy, CORS, keys and object metadata were preserved. Stored catalog URLs now use the new bucket.
- Shared BWS credentials retain their existing names and values. A successful live lookup found no app-specific record to rename.
- Obsidian: both Trailer Feed folders, their plan notes and 7 other referring notes were updated locally through Syncthing. Three corresponding ChatGPT to-do Page blocks were updated and read back.
- Homelab and Super Seed2 documentation references were committed separately. Only naming changes were staged in the latter, preserving unrelated creative work.
- Raycast bridge module paths, internal names, commands and project references were renamed. The remote naming commit excludes three pre-existing unpublished local feature commits. Both remote Linux validation and the local Windows suite passed.

## Compatibility and recovery

The old `directors-cut` RustFS bucket and Docker data volume remain intact as rollback copies. The old website address and `/directors-cut/` API ingress now return 308 redirects to the Trailer Feed addresses. The active backend uses only `TRAILER_FEED_OWNER_PASSWORD` and `trailer-feed.sqlite`. Browser session and screening preferences migrate their old keys on the existing origin. Browser storage belongs to each origin; the new website origin uses its own session storage.

Trailer Feed is now a portfolio for importing finished videos and reviewing their versions. Its Raycast bridge client, generation controls, job polling, local bridge settings and active bridge capture skill were removed on 2026-10-05. Earlier setup documents are retained under `docs/history` as historical material. The Raycast bridge remains a separate project for other consumers; Creative Studio Pro is unrelated and was not modified. Historical provenance labels remain preserved. Shared credentials and unrelated imported creative skill names are unchanged. Original data, runtime and configuration backups were retained outside tracked source. The old updater units were disabled and archived; the stopped old API container was removed without removing its data volume.

The Windows workspace is available at `C:\Users\Gordo\Documents\Github\trailer-feed` through a directory junction. Windows refused the physical folder move because an active process holds the existing checkout. Codex overwrote the direct saved-state naming edit, and its live project list still reports the old name/path. The physical folder and Codex sidebar changes remain pending until the active checkout can be released and the app's project settings updated. Both paths currently reach the same preserved checkout; project IDs and chat memberships were retained.

The M3 was offline in Tailscale and unreachable over SSH. Its installed Raycast shortcuts and local checkout still need the published rename applied when it is available. Do not replace its private environment with a reconstructed file or overwrite unpublished work.

## Validation

The production build passed using a clean archive of committed source, keeping local catalog edits out of generated deployment assets. Svelte check reported zero errors/warnings. The 22 backend tests and 7 upload/catalog tests passed. Autofixer diagnostics on touched Svelte files were reviewed; existing unrelated suggestions were left unchanged.

The live website showed all 5 projects and nine loaded video elements at readyState 4, including playing video from the new bucket. Live login and new-origin CORS passed; unauthenticated uploads and an untrusted origin were rejected with 401. Authenticated invalid input and the gateway's invalid deletion-prefix request returned 400. No destructive production test was performed.

Frontend-only commits use the existing deployment policy: Vercel deploys them while the backend updater skips a rebuild when `backend/` and `deploy/` have not changed. Backend health therefore reports its last backend release rather than each frontend-only commit.
