# Review external registration checkpoint

V1S-166 implementation begins on `codex/external-review-versions`; it is not deployed.

`POST /external/review/versions` accepts only the server-side Review ingestion bearer configured as `TRAILER_FEED_REVIEW_INGEST_KEY`. Owner login sessions do not grant this permission, and browser Origin requests are rejected. The deployment must provision this distinct secret through BWS; no runtime value has been created or configured by this code change.

The body specifies the already connected target `run_id`, immutable `source_asset_id` and `source_version_id`, timezone-aware `source_created_at`, controlled `media_url`, and initial `metadata.prompt` / `metadata.model`. Media URLs must address the canonical HTTPS Review destination resolver and the selected exact version. Arbitrary URLs, private owner routes and token-bearing queries are rejected. The catalog contains external ownership/provenance and the resolver URL, without storage object keys or bearer credentials. Registration does not copy or fetch original media.

SQLite persists the source tuple, target project, artifact identity and assigned version. An immediate transaction serializes allocation. Retrying after restart returns the existing artifact and preserves target edits. A conflicting target project or missing disconnected artifact is rejected; ordinary retries cannot recreate it.

Remaining required work: reserve the complete ordered consent batch before per-version delivery; grids/reference images and full metadata transport; stable project connection and explicit collision handling; persistent target suppression and generation-aware reactivation; source-deletion delivery and fill-empty refresh; service-key provisioning; deployments and browser acceptance. Existing local uploads and unrelated checkout edits remain intact.

Backend verification on Windows: `uv run --with robyn==0.88.0 --with httpx==0.28.1 python -X utf8 -m unittest discover -s backend`. UTF-8 mode is required for the existing catalog seed files.
