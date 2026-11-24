# Review Room → Trailer Feed hero take (handoff)

**Status: implemented on `main` (2026-11-24).** Verify production API `revision` in
`/health` includes `hero-current` before relying on post-sync Make current in prod.

## Two paths to the same hero

| When | Review Room | Trailer Feed API |
|------|-------------|------------------|
| **Version delivery (sync)** | `destinationSync.ts` adds `is_current: true` when `version._id === asset.currentVersionId` on the delivery payload | `POST /external/review/versions` → `apply_hero_take` when `featured` or `is_current` |
| **Make current after sync** | `personal.setCurrentVersion` and `automation.setCurrentVersion` schedule `destinationSync.scheduleHeroForCurrentPick` → `destinationDelivery.heroCurrent` | `POST /external/review/hero-current` with registered `source_asset_id` / `source_version_id` + `run_id` |

Owner override in Trailer Feed UI remains `POST /runs/<run_id>/featured` (**Set hero take**).

## Touchpoints (code)

**Review Room (`review-room-svelte`):**

- `convex/destinationSync.ts` — `is_current` on version delivery; `heroPickContext`, `scheduleHeroForCurrentPick`
- `convex/destinationDelivery.ts` — `heroCurrent` action posts to `hero-current`
- `convex/personal.ts`, `convex/automation.ts` — Make current schedules hero push when pick changes

**Trailer Feed (`trailer-feed`):**

- `backend/app.py` — `review_hero_current`, ingest `is_current` / `featured`
- `backend/test_external.py` — `test_ingest_is_current_sets_hero`, `test_hero_current_after_registration`

## Rules

- Do **not** send hero flags on every synced version; only at delivery when that version is the pick, or when Make current changes after sync.
- Review playback URLs for Watch must **not** use `?cors=1` on `destination-media` originals (Trailer Feed `TakePlayer`).

## Deploy / verify

- **Review:** GitHub `main` → **Deploy to App VM** (Convex + frontend on app-vm).
- **Trailer Feed API:** `trailer-feed-update.service` on app-vm when `backend/` or `deploy/` change on GitHub `main`.
- **Trailer Feed UI:** Vercel from `main` (independent).

```bash
curl -fsS -A "Mozilla/5.0" https://media.v1su4.dev/trailer-feed/health
# revision prefix should match deployed backend commit (includes hero-current route)
```

Homelab URL map: `proxmox-home/docs/trailer-feed-service.md`.