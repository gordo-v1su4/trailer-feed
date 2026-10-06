# Review external registration checkpoint

V1S-166 implementation begins on `codex/external-review-versions`; it is not deployed.

`POST /external/review/connections` persists source project/folder IDs to a target run ID. Use `mode: "create"` with an explicitly confirmed title or `mode: "connect"` with an explicitly selected existing `run_id`. Omit `source_folder_id` for the project root. Creating with a colliding title returns409 and the existing target ID for a user choice. Replays return the persisted target despite either side's rename; they do not rematch names or silently move the connection. Removed targets cannot be recreated by a connection retry.

`POST /external/review/versions` accepts only the server-side Review ingestion bearer configured as `TRAILER_FEED_REVIEW_INGEST_KEY`. Owner login sessions do not grant this permission, and browser Origin requests are rejected. The deployment must provision this distinct secret through BWS; no runtime value has been created or configured by this code change.

First, `POST /external/review/batches` with immutable `batch_id`, connected target `run_id`, and up to 100 source identities (`source_asset_id`, `source_version_id`, timezone-aware `source_created_at`). SQLite atomically reserves every target Vn in oldest-first order before any item is delivered. A batch replay with reordered input is equivalent; changing its selection or target is a conflict. Local uploads account for these reservations too.

Each version delivery specifies that `batch_id`, target `run_id`, source identity and creation date, controlled `media_url`, optional `poster_url`, optional `grid`, up to 20 `references`, and initial `metadata`. Images specify exact `source_version_id` and controlled `media_url`; they must use the root's grant slug. Metadata copies model, prompt, source label/date, notes, release date/platforms and typed custom fields, including cleared number/boolean values. Media URLs must address the canonical HTTPS Review destination resolver and the selected exact version. Arbitrary URLs, private owner routes and token-bearing queries are rejected. The catalog contains external ownership/provenance and the resolver URL, without storage object keys or bearer credentials. Registration does not copy or fetch original media.

SQLite persists the source tuple, target project, artifact identity and assigned version. An immediate transaction serializes allocation. Retrying after restart returns the existing artifact and preserves target edits. A conflicting target project or missing disconnected artifact is rejected; ordinary retries cannot recreate it.

Reserved slots survive restart and partial delivery: a later successful delivery cannot take the failed older item's number. Concurrent retries produce one artifact. Draft projects become ready for review after successful delivery. Image attachments retain parent/source provenance and external ownership. Registration retries preserve all target edits and existing attachments. Invalid metadata does not consume the reservation.

Remaining required work: Review connection/selection UI and durable outbox; persistent target suppression and generation-aware reactivation; source-deletion delivery and fill-empty refresh; service-key provisioning; deployments and browser acceptance. Existing local uploads and unrelated checkout edits remain intact.

Backend verification on Windows: `uv run --with robyn==0.88.0 --with httpx==0.28.1 python -X utf8 -m unittest discover -s backend`. UTF-8 mode is required for the existing catalog seed files.
