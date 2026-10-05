> Historical only. Retired 2026-10-05. Trailer Feed is a portfolio and no longer connects to the Raycast bridge.

# Bridge Artifact Handshake

> Single source of truth for how `raycast-pro-bridge` and `trailer-feed`
> exchange artifacts. Both sides cite this document.

## Ownership principle

**Bridge produces DRAFT artifacts. Trailer Feed owns ACCEPTED/persisted artifacts.**

The bridge may write research outputs (sources, candidates, draft cards) into
ephemeral job directories. Trailer Feed decides which drafts are promoted to
the canonical prompt library and comparison runs.

## Research job artifacts (bridge → trailer-feed)

When `start_prompt_research` completes, the Hermes dispatcher writes artifacts
under a job directory (default `~/.raycast-pro-bridge/jobs/<job_id>/`):

| Artifact | Content type | Purpose |
|---|---|---|
| `sources.md` | `text/markdown` | Markdown list of source URLs and notes Hermes used |
| `candidates.jsonl` | `application/jsonl` | One JSON object per candidate prompt card |
| `draft-cards/` | directory | Individual draft card `.md` files (optional) |

Each `candidates.jsonl` row follows `CandidateCard` shape (see
`src/lib/bridge/types.ts`):

```json
{
  "slug": "seedance-netflix-teaser-title-slam",
  "title": "Seedance Netflix Teaser Title Slam",
  "model_family": "seedance",
  "use_cases": ["netflix_teaser"],
  "evidence_type": "official",
  "library_status": "seed_pattern",
  "source_urls": ["https://..."],
  "body_markdown": "# ...full card body..."
}
```

Trailer Feed reads these via `read_research_artifact`, reviews them, then
promotes accepted cards into:

```
content/cards/<family>/<slug>.md
```

The card frontmatter must satisfy `schemas/prompt-card.schema.json`.

## Comparison run artifacts (trailer-feed owned)

Comparison runs live entirely in trailer-feed. The bridge does NOT create
comparison artifacts — it only provides research that feeds into them.

Layout:

```
content/comparisons/<run-id>/
├── comparison-run.md    # run metadata, prompt, models, rubric
├── answers.jsonl        # one JSON object per model answer
└── grades.jsonl         # one JSON object per graded answer (optional, manual)
```

`answers.jsonl` rows must satisfy `schemas/model-answer.schema.json`.
The run metadata must satisfy `schemas/comparison-run.schema.json`.

**Rule: answers must be real Raycast/model outputs. No fabrication.**

If real answers are unavailable, leave the directory empty and document
the blocker in a `README.md` inside the comparison folder.

## Bridge client (trailer-feed side)

`src/lib/bridge/types.ts` contains the type contract copied from
`raycast-pro-bridge/src/contracts/` with a provenance header.

When the SvelteKit scaffold arrives (B3), replace this copied file with
a real import from the bridge contract (private package or git dep).

The thin client function `callBridgeTool(options, toolName, input)` sends
authenticated POST requests to the bridge. **Never embed the bridge token
in static browser bundles** — call the bridge only from SvelteKit server
routes/actions.

## Bridge endpoints (raycast-pro-bridge side)

| Method | Path | Auth | Purpose |
|---|---|---|---|
| GET | `/health` | none | Liveness probe |
| GET | `/tools` | bearer | List allowed tools |
| POST | `/tools/:tool` | bearer | Invoke a tool |

Default bind: `127.0.0.1:8787`. Tailscale exposure is explicit via env.

Dispatcher mode: `RAYCAST_BRIDGE_DISPATCHER=hermes-cli` for real Hermes
spawn; `stub` (default) for honest typed stubs.

## Raycast entry point (Mac-local Script Commands)

Script Commands in `raycast-pro-bridge/script-commands/`:

- **Bridge Status** — checks `/health` + lists `/tools`
- **Bridge Call Tool** — POSTs to `/tools/<tool>` with bearer token
- **Trailer Feed Comparison Prompt** — copies the current project comparison
  prompt to the clipboard (`trailer-feed-comparison-prompt.sh`)
- **Capture Trailer Feed Answer** — appends the current clipboard as one
  schema-shaped `answers.jsonl` row under
  `trailer-feed/content/comparisons/<run-id>/` and creates `comparison-run.md`
  on first capture (`trailer-feed-capture-answer.sh`). Args: exact model
  label, optional run id, optional target model.

Capture loop (no fabrication):
1. Raycast AI chat → `Shift+Cmd+M` pick model
2. Run **Trailer Feed Comparison Prompt** → paste → send
3. Copy the real answer → run **Capture Trailer Feed Answer** with the exact
   model label Raycast showed
4. Repeat for 3–5 models; only then build B3b comparison UI

Hotkeys are assigned in Raycast UI (Configure Command), not in `.sh` metadata.
Suggested: prompt `Ctrl+Opt+Cmd+P`, capture `Ctrl+Opt+Cmd+C`.

Point Raycast at the `script-commands/` directory via
Extensions → Script Commands → Add Directories.
