# Review Room → Trailer Feed hero take (handoff)

> **2026-11-25:** Review Room sends `is_current: true` on `POST /external/review/versions` when the synced version is the asset pick at delivery time (`review-room-svelte` `destinationSync.ts`). Trailer Feed maps that to `featured_artifact_id`. **Still open:** when **Make current** changes after a take is already synced, push hero to Trailer Feed (dedicated ingest call or resync).

**Trailer Feed (done on our side):** `featured` or `is_current` on `POST /external/review/versions` → `featured_artifact_id` on the run. Owner override: `POST /runs/<run_id>/featured` (**Set hero take** in UI). Deploy API when ready so production catalog matches local backend.

**Tomorrow — Review Room only:** When the user chooses **Make current** on a version synced to Trailer Feed, include `"is_current": true` (or `"featured": true`) on the next version delivery (or a dedicated metadata update) so the target hero matches Review's pick without manual **Set hero take** in Trailer Feed.

Suggested touchpoints:

- `convex/destinationSync.ts` / delivery payload builder — add boolean from asset's current version id
- Compare with `PUT /api/v1/assets/{assetId}/current-version` in Review's agent API (the pick)

**Do not** send hero flags for every synced version; only the version that is current at sync time or when Make current changes after sync.