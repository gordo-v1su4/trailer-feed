> Historical only. Retired 2026-10-05. Trailer Feed is a portfolio and no longer connects to the Raycast bridge.

---
name: raycast-concept-capture
description: Capture a Trailer Feed comparison run through Raycast using computer use. Opens Raycast AI chat for Sora 2 - ChatGPT and Sora 2 - Haiku, pastes the canonical brief, copies each answer, and persists via trailer-feed-capture-answer.sh. Use when the user asks to capture a concept run, automate Raycast capture, or run computer use for Trailer Feed.
---

# Raycast Concept Capture (Computer Use)

Automate the Raycast half of the Trailer Feed Create flow. The web app creates the run via bridge `create_comparison_run`; this skill drives Raycast with **computer use** and persists answers with the existing Script Command.

## When to use

- User chose **Automated** on `/create` and a run ID was created
- User says: "capture concept run …", "run computer use for Raycast", "get ChatGPT and Claude answers"
- `content/comparisons/<run-id>/capture-request.json` exists with `"workflow": "computer_use"`

## Prerequisites

- Raycast open on the Mac with agents:
  - **Sora 2 - ChatGPT**
  - **Sora 2 - Haiku** (Claude)
- App name is usually `Raycast` or `Raycast Beta` (script auto-detects)
- **Accessibility** granted to Cursor (or Terminal) in System Settings → Privacy & Security → Accessibility — required for computer-use keystrokes
- `raycast-pro-bridge` Script Commands installed
- `TRAILER_FEED_PATH` points at the trailer-feed checkout
- Bridge running with `TRAILER_FEED_PATH` set

## Inputs

1. **run_id** — from Create automated panel or `capture-request.json`
2. Read run metadata:
   - `content/comparisons/<run-id>/comparison-run.md`
   - `content/comparisons/<run-id>/capture-request.json`

## Build the model prompt

Run the existing prompt packager (do not invent a new brief):

```bash
cd "$TRAILER_FEED_PATH/../raycast-pro-bridge/script-commands"
TRAILER_FEED_PATH="$TRAILER_FEED_PATH" \
TRAILER_FEED_CLIPBOARD_FILE="/tmp/dc-prompt.txt" \
./trailer-feed-comparison-prompt.sh "<run-id>"
```

Read `/tmp/dc-prompt.txt` — that is the exact text to paste into each Raycast agent.

## Automated path (preferred)

After Create calls `create_comparison_run`, the app chains:

1. `prepare_concept_capture` — prompt on clipboard + active run binding
2. `run_concept_capture` — background AppleScript drives Raycast Beta / Raycast, captures both models, persists answers
3. Poll `get_concept_capture_status` — answers appear in Create UI and Projects

No manual Run ID typing. Do **not** use the legacy **Capture Trailer Feed Answer** command for automated runs.

## Manual computer use loop (per model)

For each pending model in `capture-request.json` (`ChatGPT`, then `Claude`):

1. **Open Raycast** (Cmd+Space or click dock icon if needed)
2. **Open the Raycast agent** named in `raycast_agent` (e.g. `Sora 2 - ChatGPT`)
3. **Paste** the full prompt from `/tmp/dc-prompt.txt`
4. **Send** and wait until the complete response is visible (scroll if needed)
5. **Select all + copy** the model's full reply
6. **Persist via Script Command** (preferred over hand-editing JSONL):

```bash
TRAILER_FEED_PATH="$TRAILER_FEED_PATH" \
  ./trailer-feed-capture-answer.sh "<ModelLabel>" "<run-id>" sora-2
```

Use exact labels: `ChatGPT` and `Claude`.

7. Verify capture output reports valid `creative_concept_v1` or explicit invalid structure (never rewrite the answer)

## After both models

```bash
cd "$TRAILER_FEED_PATH" && bun run build:comparisons
```

Poll bridge status or open Projects:

```bash
curl -s -H "Authorization: Bearer $RAYCAST_BRIDGE_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"run_id":"<run-id>"}' \
  http://127.0.0.1:8787/tools/get_concept_capture_status
```

Success: `captured_valid_count: 2`, `run_status: answers_collected`.

## Rules

- Never fabricate or repair model output
- Run ChatGPT then Claude **serially** (clipboard capture)
- If structure is invalid, leave it invalid; user can recapture
- Do not call billable Sora generation unless the user explicitly asks

## Manual fallback

If computer use fails, tell the user to switch Create to **Manual** and use:

1. **Start Trailer Feed Concept Run**
2. **Capture Trailer Feed Answer** × 2
