# Review Room → Trailer Feed hero take (handoff)

> **Paused (2026-11-25):** Do **not** change Review Room or live destination sync today. Review has active work in flight; pick this up **tomorrow**. Trailer Feed already ingests `featured` / `is_current` when Review sends it—no Review-side wiring yet.

**Trailer Feed (done on our side):** `featured` or `is_current` on `POST /external/review/versions` → `featured_artifact_id` on the run. Owner override: `POST /runs/<run_id>/featured` (**Set hero take** in UI). Deploy API when ready so production catalog matches local backend.

**Tomorrow — Review Room only:** When the user chooses **Make current** on a version synced to Trailer Feed, include `"is_current": true` (or `"featured": true`) on the next version delivery (or a dedicated metadata update) so the target hero matches Review's pick without manual **Set hero take** in Trailer Feed.

Suggested touchpoints:

- `convex/destinationSync.ts` / delivery payload builder — add boolean from asset's current version id
- Compare with `PUT /api/v1/assets/{assetId}/current-version` in Review's agent API (the pick)

**Do not** send hero flags for every synced version; only the version that is current at sync time or when Make current changes after sync.