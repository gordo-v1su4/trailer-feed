# Public catalog and Git cleanup — October 7, 2026

The public homepage was featuring `Activity replacement QA 2026-10-07`.
Its Review Room destination media could no longer load, leaving a black hero.
`Lifecycle QA 2026-10-07` was also still listed without any takes.

Both test projects were removed through the authenticated project removal API
after a SQLite online backup and a full public catalog snapshot. Removal retains
the backend's target suppression records; it does not delete Review Room originals.
Neon Afterlife and The Last Prescription were compared by SHA256 across their
run, answers, prompts, decisions and artifacts documents before and after cleanup.
Both were unchanged: seven videos/two grids and three videos/one grid respectively.

The public homepage was verified in the browser with Neon Afterlife playing:
video readyState 4, decoded width 854, paused false and advancing playback time.
The catalog now contains only those two real projects. API health reports
revision `4c41cb4`; `trailer-feed-update.timer` is active.

The primary checkout had remained on `codex/sync-reliability`, while local main
was twelve commits behind origin/main. Main was fast-forwarded to `4c41cb4`.
Every leftover local and remote branch was verified as an ancestor of main before
removal: external-review-versions, external-version-suppression,
source-deletion-refresh, sync-reliability and ui/screening-room-studio.
There is one worktree, the primary checkout, on main.

Recovery material on the Windows workstation is in
`C:\Users\Gordo\.codex\tmp\trailer-feed-tidy-20261007`:

- `all-branches.bundle`: Git history, old branches and the preserved stash.
- `catalog-before.json` and `catalog-after.json`: public catalog snapshots.
- `workspace-tmp`: moved temporary exports, build checks and logs.
- `git-status-before.txt` and `branches-before.txt`: pre-cleanup inventory.

The stash named `Preserve pre-tidy local catalog and tool state 2026-10-07`
retains the prior uncommitted files. It includes generated catalog regressions
to legacy storage URLs and an empty draft; these were not applied to main.
The SQLite backup is `/data/pre-tidy-20261007.sqlite` in the persistent
`trailer-feed-data` volume on App VM. These are recovery copies, not new active
catalogs or working checkouts.

No frontend or backend code deployment was needed to restore playback.
