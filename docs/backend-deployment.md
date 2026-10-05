# Trailer Feed backend

The public Svelte app on Vercel reads the live Robyn catalog at
`https://media.v1su4.dev/trailer-feed`. Robyn runs in `trailer-feed-api` on
app-vm (VM100), with loopback port 18100 and the Docker volume
`trailer-feed-data`. SQLite holds text, URLs, version numbers, upload states,
and hashed owner sessions. Videos and thumbnails stay in bucket `trailer-feed`.

## Upload flow

Sign in as `gordo` using the shared operator app password, then drop a video
onto the selected project. Public uploads accept up to 95 MB per file (500 MB
per batch), below the edge proxy request limit. Larger uploads need chunking
or a direct multipart storage path. The browser uploads directly to Robyn, avoiding
Vercel's request-body path. Robyn uses the private RustFS gateway `/upload`,
then `/video/jobs`. The existing Stack Structure worker handles the job without
Trigger.dev. Its first scene thumbnail becomes the version preview. The
original video remains the playback source; choose browser-compatible MP4/H.264
for widest playback support. MOV/WebM acceptance does not promise codec conversion.

A version appears after processing completes. SQLite persists upload status and
SHA256 deduplication. Processing failure has a retry button. A gateway restart
can lose its in-memory job; Trailer Feed retains the source and allows retry.
No paid generation is submitted by this backend.

## Creating projects from uploads

Create has two tabs: **Write a prompt** and **Upload videos**. Upload projects
need an owner session but no prompt, writer capture, or generation bridge.
`POST /runs` accepts a title, optional logline, format and tags, plus a
32-character lowercase hex `request_id`. The resulting `upload-<request_id>`
record and its four empty document lists are created in one transaction.
Replaying the same request returns that project; conflicting details return 409.
New titles must be unique by the short name shown in Projects: case,
parentheticals, and subtitles after a spaced dash do not distinguish projects.
The same check applies when renaming. Existing duplicate records are left for
the owner to review and remove.

The browser validates the selected files before creating the project and sends
them through the existing `/versions` flow. Each becomes a separate take.
Optional per-video model and prompt details are saved after processing.
Retries retain the project and upload IDs, skip completed videos, and can resume
processing or metadata saves without duplicating successful takes. The first
processed video moves an upload project from draft to ready for review.

Deploy the backend's `POST /runs` route before enabling the new frontend in
production. Local development continues to use the live catalog, so the new
project flow also requires that backend deployment when testing on port 5191.

## Renaming projects

`POST /runs/:run_id` with `{"title": "..."}` (and optionally `"logline"`)
updates the stored project record. It requires the same owner session as
uploads. Titles are 1–120 characters, loglines up to 600. The UI shows a short
display name (subtitle and parentheticals dropped, all-caps titles set in title
case) but saves exactly what the owner types.

## Removing projects

The Projects page offers **Remove project** with exact title confirmation and
owner sign-in. `POST /runs/:run_id/delete` also requires `confirm_run_id` in
the request body. The backend asks the RustFS media gateway to delete all
objects under the project's dated upload and `version-assets` prefixes, then
removes its SQLite documents and upload records. Derived worker artifacts under
the source object's `.analysis/` path are included. If storage cleanup fails,
the project stays listed for a retry. Deleted seeded projects are tombstoned so
a backend restart does not import them again. Deploy the media gateway's
`/trailer-feed/delete-run-objects` route before this backend version.

## Project thumbnails

The **Thumbnail** tab in Projects sets a cover for that page's main project
strip only. Version posters, playback, and Home keep their take-derived images.
The owner can upload a PNG, JPEG, or WebP file up to 5 MB through
`POST /runs/:run_id/thumbnail`. Robyn checks the image signature, stores it
under `version-assets/<run_id>/project-covers/`, and writes the URL and object
key to the run record. Replacements use content-addressed URLs so browser
caches cannot show the previous image. **Use automatic thumbnail** calls
`POST /runs/:run_id/thumbnail/remove`, deletes the exact stored object via the
private gateway, and clears the run override. Project removal includes the
same storage prefix. Both routes require the owner session.

## Configuration

Runtime `/opt/trailer-feed/runtime.env` is root-owned, mode 0600.
- `MEDIA_GATEWAY_URL`: private RustFS gateway.
- `MEDIA_GATEWAY_TOKEN`: existing RustFS gateway credential, BWS
  `PROXMOX_HOME_HOSTINGER_MEDIA_GATEWAY_TOKEN` (existing local project mirror).
- `TRAILER_FEED_OWNER_PASSWORD`: BWS `PROXMOX_HOME_SHARED_OPERATOR_APP_PASSWORD`.
- `ALLOWED_ORIGINS`: `https://trailerfeed.video`, `https://www.trailerfeed.video`,
  `https://trailer-feed.vercel.app`, and authorized local development origin
  `http://127.0.0.1:5191`. Include both public-domain origins even while the
  apex redirects to `www`; the catalog and owner routes require exact matches.

On 2026-10-05 the public domain initially loaded the frontend but the catalog
response omitted CORS headers because the runtime allowed only Vercel and
local development. Both public origins were added to the existing root-owned
runtime environment and only `trailer-feed-api` was recreated using its existing
release image. The previous runtime environment is retained at
`/opt/trailer-feed/runtime.env.before-public-domain-20261005-112239`.
Public catalog GET and owner-login preflight now return the requesting public
origin; an unrelated origin still receives no CORS permission. All 19 distinct
catalog video URLs passed 1 KiB range requests (206), and all 20 distinct poster
URLs passed HEAD requests (200), with anonymous storage CORS. Browser playback
was not verified because Codex could not verify saved browser permissions.

The build command runs `svelte-kit sync` before the comparison indexer so clean
checkouts have `.svelte-kit/tsconfig.json` before Bun reads the root tsconfig.

The shared storage credential is never exposed to the browser. Owner sessions
expire after 24 hours and are stored as hashes in SQLite. Login is rate limited.
Caddy routes only `/trailer-feed/*` to this container; all existing RustFS
routes retain their upstream.

## Container updates

`trailer-feed-update.timer` checks public GitHub `main` every two minutes.
`/opt/trailer-feed/update.sh` fetches the exact commit and rebuilds only if
`backend/` or `deploy/` changed. Vercel handles frontend-only pushes independently.
The systemd service is root-owned and the API has no Docker socket access.

Before replacement, SQLite's online backup API creates a consistent database
copy in `/opt/trailer-feed/backups/<previous-sha>.sqlite`. The update waits for
the container health check and rolls back the image on failure. The persistent
volume is never recreated. Seed JSON imports only missing records, never
replaces server-owned records. Schema changes must remain backward compatible
with the prior release; destructive migrations require a deliberate backup and
migration procedure. Backups currently remain on the same VM; no off-VM backup
policy is configured by this project.

Manual update: `sudo systemctl start trailer-feed-update.service`.
Inspect: `sudo journalctl -u trailer-feed-update.service` and
`sudo docker logs trailer-feed-api`.
Pause deployment: `sudo systemctl stop trailer-feed-update.timer`.

Python validation: `uv pip install -r backend/requirements.txt`, then
`python -m unittest discover -s backend`. Frontend: `bun run check`.

## Acceptance evidence — 2026-09-14

Public browser sign-in and file chooser uploads passed from Projects (v1) and
Home (v2). Duplicate re-upload created no new version. The shared RustFS worker
completed both jobs; thumbnails appeared, the feed refreshed without deployment,
and the uploaded 1280x720 video played with advancing time and no media error.
The scheduled updater rejected a failing container test while leaving the prior
container healthy, then automatically deployed corrected commit `1c81258`.
Both ready versions survived replacement; an online SQLite backup was created.
Temporary QA records were archived under `/opt/trailer-feed/backups/` and
removed from the live catalog, leaving the three original projects. Tiny QA
media objects remain under the isolated `trailer-feed-upload-qa` key prefix.

Validation: four backend tests (also executed inside the Docker build), Svelte
check with zero errors/warnings, Caddy config validation, public unauthenticated
upload rejection (401), and live browser playback. Health rollback after a
successfully built but unhealthy image was not deliberately fault-injected.
