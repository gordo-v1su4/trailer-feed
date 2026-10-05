> Historical only. Retired 2026-10-05. Trailer Feed is a portfolio and no longer connects to the Raycast bridge.

# Trailer Feed — Raycast → Sora Vertical Slice Handoff

**Updated:** 2026-08-14

**Primary branch:** `main`
**Companion repository:** `gordo-v1su4/raycast-pro-bridge`

## Goal

Turn one Trailer Feed creative brief into two independently developed concepts through Raycast—one from ChatGPT and one from Claude—then carry each concept into exactly one open-ended 12-second Sora video prompt.

The generated video is the creative submission. There is no editor/timeline role in this slice.

## Implemented in Trailer Feed

- `CreativeConceptPackage` contract with:
  - title
  - logline
  - 1–2 sentence summary/hook
  - exactly one Sora prompt
  - `runtime_seconds: 12`
  - `prompt_count: 1`
- Backward-compatible validation for legacy `structured_prompt` records.
- Raw model output remains canonical in `answer_text` when structured parsing fails.
- Explicit run states for partial answer and generation workflows.
- Real line-by-line validation of persisted `answers.jsonl`, including file and line diagnostics.
- Schema dependencies declared in `package.json` and `bun.lock`.
- Create UI adapted for the first vertical slice:
  - project title
  - 12-second Sora target
  - integrated writing/image/action/sound/music direction
  - canonical ChatGPT + Claude Raycast brief
  - clear handoff to the Raycast Script Command workflow
- Focused schema tests in `scripts/test-model-answer-schema.ts`.
- Full implementation plan in `.hermes/plans/2026-08-14_022750-trailer-feed-raycast-sora-vertical-slice.md`.
- Generated `public/data` build artifacts are not staged by this handoff; the Projects index is rebuilt by the Raycast start command or the standard Bun build command.

## Implemented in Raycast Pro Bridge

The companion repository contains these Script Commands:

- `script-commands/trailer-feed-start-concept-run.sh`
  - creates the canonical comparison run
  - requests ChatGPT and Claude
  - rebuilds the Trailer Feed Projects index
  - copies the canonical model prompt
- `script-commands/trailer-feed-comparison-prompt.sh`
  - reads `comparison-run.md`; no hard-coded Glass House prompt
  - appends the strict creative-concept response contract
- `script-commands/trailer-feed-capture-answer.sh`
  - preserves real clipboard output verbatim
  - parses TITLE, LOGLINE, HOOK, and SORA PROMPT — 12 SECONDS
  - writes atomically
  - rejects exact duplicates
  - records invalid parsing without repairing or fabricating output
  - advances `answers_partial` → `answers_collected`
- Test coverage:
  - `script-commands/test-trailer-feed-start-run.sh`
  - `script-commands/test-trailer-feed-workflow.sh`

## Verified commands

Trailer Feed:

```bash
bun run scripts/test-model-answer-schema.ts
bun run scripts/validate-schemas.ts
bun run check
bun run build
```

Observed results before handoff:

- concept schema tests: 6 passed, 0 failed
- repository schema validation: 15 OK, 0 errors
- Svelte diagnostics: 0 errors, 0 warnings
- production build: passed

Raycast Pro Bridge:

```bash
bash -n script-commands/trailer-feed-*.sh
./script-commands/test-trailer-feed-start-run.sh
./script-commands/test-trailer-feed-workflow.sh
bun run scripts/validate-contract.ts
bun run scripts/validate-security.ts
bun run scripts/smoke-server.ts
```

Observed results before handoff:

- run creation/index/prompt handoff: passed
- parsing/raw preservation/state/deduplication: passed
- contract validation: 18 passed, 0 failed
- security validation: 22 passed, 0 failed
- bridge smoke test: 14 passed, 0 failed

## Manual first-run workflow

1. Open Trailer Feed → **Create**.
2. Enter a project title and creative brief.
3. Click **Prepare Raycast concept run** and copy the canonical brief.
4. In Raycast, run **Start Trailer Feed Concept Run**.
5. Paste the copied prompt into ChatGPT in Raycast.
6. Copy the complete response and run **Capture Trailer Feed Answer** with model label `ChatGPT`.
7. Repeat with Claude and exact model label `Claude`.
8. Run the Trailer Feed comparison index build or let the start command do it automatically.
9. Open Projects/Comparisons and verify both packages.
10. Submit each validated prompt to the existing Sora/Higgsfield workflow. Ask before any billable generation.

## Safety and data rules

- Never fabricate model responses, generation IDs, or media.
- Never silently rewrite a malformed answer into a valid package.
- Keep `answer_text` verbatim.
- Run ChatGPT and Claude serially when clipboard capture is used.
- Do not spoof or reverse-engineer a Raycast API; use legitimate Raycast Pro interaction.
- Preserve repository-backed Markdown/JSONL as canonical data.
- Ask before billable Sora/Higgsfield generation.

## Remaining work

1. Install/register the new Script Commands in the owner’s live Raycast Script Commands directory.
2. Perform one real ChatGPT + Claude capture on the M3 Mac.
3. Confirm both answers appear in the Projects UI after index rebuild.
4. The Higgsfield video lane now quotes, confirms, submits, polls, downloads, indexes, and returns playable video previews from the actual MP4 rather than reusing image-grid posters.
5. The optional Nano Banana Pro lane now uses the same quote/confirm/poll/download/index lifecycle. Higgsfield's API/CLI machine id is `nano_banana_2`; the UI must always call it Nano Banana Pro. Grid prompts require a full-bleed edge-to-edge 3×3 canvas with no white/black borders, thick gutters, frames, mats, margins, letterboxing, or pillarboxing.
6. Attach both real videos to their source answers with provenance.
7. Add video-only review actions: **Keep / Iterate / Extend / Reject**.
8. Run a browser smoke test of Create and Projects on desktop and mobile widths.
9. Expand the future team profile only after this slice works: Creative Director, Story Producer, integrated Writer/Prompt/Sound role, and Brutal Review Critic.
