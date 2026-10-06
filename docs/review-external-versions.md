# Review external registration checkpoint

V1S-166 implementation begins on `codex/external-review-versions`; it is not deployed.

`POST /external/review/connections` persists source project/folder IDs to a target run ID. Use `mode: "create"` with an explicitly confirmed title or `mode: "connect"` with an explicitly selected existing `run_id`. Omit `source_folder_id` for the project root. Creating with a colliding title returns409 and the existing target ID for a user choice. Replays return the persisted target despite either side's rename; they do not rematch names or silently move the connection. Removed targets cannot be recreated by a connection retry.

`POST /external/review/versions` accepts only the server-side Review ingestion bearer configured as `TRAILER_FEED_REVIEW_INGEST_KEY`. Owner login sessions do not grant this permission, and browser Origin requests are rejected. The deployment must provision this distinct secret through BWS; no runtime value has been created or configured by this code change.

First, `POST /external/review/batches` with immutable `batch_id`, connected target `run_id`, and up to 100 source identities (`source_asset_id`, `source_version_id`, timezone-aware `source_created_at`). SQLite atomically reserves every target Vn in oldest-first order before any item is delivered. A batch replay with reordered input is equivalent; changing its selection or target is a conflict. Local uploads account for these reservations too.

Each version delivery specifies that `batch_id`, target `run_id`, source identity and creation date, controlled `media_url`, optional `poster_url`, optional `grid`, up to 20 `references`, and initial `metadata`. Images specify exact `source_version_id` and controlled `media_url`; they must use the root's grant slug. Metadata copies model, prompt, source label/date, notes, release date/platforms and typed custom fields, including cleared number/boolean values. Media URLs must address the canonical HTTPS Review destination resolver and the selected exact version. Arbitrary URLs, private owner routes and token-bearing queries are rejected. The catalog contains external ownership/provenance and the resolver URL, without storage object keys or bearer credentials. Registration does not copy or fetch original media.

SQLite persists the source tuple, target project, artifact identity and assigned version. An immediate transaction serializes allocation. Retrying after restart returns the existing artifact and preserves target edits. A conflicting target project or missing disconnected artifact is rejected; ordinary retries cannot recreate it.

Reserved slots survive restart and partial delivery: a later successful delivery cannot take the failed older item's number. Concurrent retries produce one artifact. Draft projects become ready for review after successful delivery. Image attachments retain parent/source provenance and external ownership. Registration retries preserve all target edits and existing attachments. Invalid metadata does not consume the reservation.

Review connection/selection UI, durable outbox, target suppression and exact-version reactivation are implemented on stacked branches. Service provisioning, deployments and browser acceptance remain required; existing local uploads and unrelated checkout edits remain intact.

## Suppression and reactivation implementation

The stacked `codex/external-version-suppression` branch adds owner-confirmed `POST /versions/<artifact_id>/remove` with `run_id`, `confirm_artifact_id` and `expected_generation`. External removal persists `target_suppressed` before dropping the root and its external image attachments. It does not call storage or Review. Project removal also suppresses registered and reserved mappings after its existing target-storage cleanup succeeds. Source-deleted state is retained if a target removal is repeated.

Server-side `POST /external/review/status` reports exact source states, target identity and `consent_generation` for reconciliation. Every batch identity, reservation and delivered root carries a consent generation (initially1). Old delivery/batch retries cannot restore suppressed entries or act on a newer generation. A stale owner removal receives409 instead of deleting a reactivated version.

`POST /external/review/reactivations` requires `intent: "sync-again"`, exact source identity/date, target `run_id`, a new immutable `batch_id`, and the current `expected_generation`. It reserves the next generation for that exact suppressed version; optional higher `consent_generation` aligns with a Review grant whose generation advanced during an earlier failed handoff. Normal version delivery then uses the new batch/generation and a fresh Review grant. The operation replay is idempotent. Reactivation preserves Vn in the same target; another explicitly selected target gets a new local Vn. Independent persistent version counters retain the old project's allocation history after a move. Local upload allocation shares that counter under an immediate transaction.

The owner take-details UI confirms removal of the captured external artifact and consent generation, requires owner sign-in, and reloads the project after success. Takes sort by assigned target Vn, including an older source version published later. Review's explicit Sync again atomically rotates its grant and durably retries a separate reactivation operation before batch reservation; uncertain confirmations retain the same nonce, metadata revision and image preview.

## Terminal source deletion

Server-only `POST /external/review/source-deletions` accepts exact `source_asset_id`, `source_version_id` and `consent_generation`. It persists `source_deleted` before removing the corresponding root and its external image attachments, without storage or Review calls. Replays are idempotent, including after restart. Source deletion is terminal across consent generations: batch delivery, generic retry and explicit reactivation cannot recreate it. Deletion arriving before reservation creates a tombstone without allocating a target Vn; a delayed reservation is rejected.

Deleted image versions also receive terminal tombstones. Their matching external grid/reference attachments and parent links are removed deliberately while the video, Vn and populated target edits remain. Delayed initial delivery omits tombstoned images instead of recreating them. Distinct unallocated tombstone identities do not consume project Vn or collide with one another. Review emits these removals durably in its normal owner deletion/purge transaction, revokes root grants immediately, contracts deleted image allowlists and clears source reference metadata with a new revision.

## Explicit fill-empty metadata refresh

Server-only `POST /external/review/metadata-refreshes` requires `intent: "refresh-empty"`, immutable `operation_id`, exact source identity/generation, target `run_id`, controlled root `media_url`, and candidate metadata/grid/references. It accepts only a registered mapping at the same generation. Suppression, source deletion and a missing project/artifact reject refresh before mutation; refresh cannot reactivate a version.

Only empty target fields are filled. Populated model, prompt, notes, grid and references remain, as do custom values including `false` and `0`; custom identities/kinds stay stable. Deleted reference tombstones are respected. Target Vn, created date, identity and media URL stay unchanged. Changed context increments its revision to protect concurrent owner edits. SQLite stores a request hash and receipt for each operation so a lost-response replay neither adds duplicate images nor refills a field the owner cleared after that operation.

Still required: Review-side refresh consent/transport/UI, unsync, explicit replacement of a deleted folder connection, service provisioning, deployments and live acceptance. Local checks prove implementation behavior, not deployed cross-app acceptance.

Backend verification on Windows: `uv run --with robyn==0.88.0 --with httpx==0.28.1 python -X utf8 -m unittest discover -s backend`. UTF-8 mode is required for the existing catalog seed files.
