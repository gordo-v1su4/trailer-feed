---
title: Trailer Feed Deep-Dive Plan
project: trailer-feed
repo: github.com/gordo-v1su4/trailer-feed
status: draft-plan
created: 2026-07-02
owner: Hermes
related_repos:
  - github.com/gordo-v1su4/trailer-feed
  - github.com/gordo-v1su4/raycast-pro-bridge
related_notes:
  - [[30-Mac-Automation/Raycast Hermes Integration Research]]
  - [[04-Projects/Mac Automation and Raycast Bridge]]
  - [[04-Projects/Syncthing Obsidian Vault Sync]]
tags:
  - trailer-feed
  - prompt-library
  - seedance
  - sora
  - raycast
  - hermes
  - svelte
---

# Trailer Feed Deep-Dive Plan

> **For Hermes / omp / Gordo:** `trailer-feed` is the creative consumer repo. It should own prompt libraries, creative workflows, visual review/database UX, and eventually prompt-comparison outputs. `raycast-pro-bridge` owns the Raycast Pro layer and bridge plumbing. Hermes remains the durable backend/research/tool runner. Obsidian remains shared non-secret state. Bitwarden remains the secret source.

## Goal

Build `trailer-feed` into the visual creative prompt/workflow database for Seedance, Sora, trailer/teaser prompts, and future creative setups. It should let Gordo run short creative research sessions, compare multiple model/agent answers to the same prompt problem, curate the best outputs into prompt cards, browse them like a dense dark visual database, copy prompts quickly, and connect each card to videos, references, evidence, tests, and human ratings.

## Architecture summary

```text
Raycast Pro UI / Agents / AI Commands
  -> raycast-pro-bridge HTTP MCP tools over Tailscale
  -> Hermes backend research/comparison jobs
  -> Obsidian prompt library files + JSONL indexes
  -> trailer-feed Svelte 5 visual browser
```

`trailer-feed` should not become the Raycast integration repo. It consumes Raycast/Hermes as services and owns the creative artifacts: prompt cards, prompt packs, references, model comparisons, video links, review/rating data, schemas, and the visual browsing app.

## Non-negotiable constraints

- No Ollama / local LLM hosting on the Mac.
- Do not use `raycast2api`; it replays Raycast bearer tokens as an OpenAI endpoint and is ToS-risky.
- Secrets live in Bitwarden Secrets Manager, never in repo or Obsidian.
- Obsidian vault is synced shared non-secret state across agents/machines.
- Raycast Pro credits are used through Raycast UI/Agents/AI Commands, not by spoofing an API.
- v1 is for occasional ~1hr creative brainstorming/research sessions, not always-on infrastructure.
- UI target: dark, dense, image/video-first, compact, clean, in the visual family of Pindeck / project-stack-structure.

---

# 1. Prompt-card schema

Use human-readable Markdown notes with YAML frontmatter as the canonical authoring format, plus generated JSONL indexes for fast app/Raycast/Hermes search.

## 1.1 Core identity fields

```yaml
---
id: seedance-camera-push-emotional-reveal
slug: seedance-camera-push-emotional-reveal
title: Emotional Camera Push Reveal
summary: Slow cinematic push-in pattern for emotional reveal shots.
repo_scope: trailer-feed
card_type: prompt_card # prompt_card | prompt_pack | comparison_result | workflow_setup
created: 2026-07-02
updated: 2026-07-02
created_by: hermes # hermes | omp | gordo | raycast | imported
curator: Gordo
---
```

Rules:
- `id` is stable and kebab-case.
- `slug` defaults to `id` but can differ if the visible URL changes.
- `card_type` lets one folder contain related creative artifacts without losing structure.
- `created_by` is provenance, not authorship ego. It helps later understand which agent/workflow made the card.

## 1.2 Model/prompt targeting fields

```yaml
model_family: seedance # seedance | sora | veo | kling | runway | general_video | image | text
model_targets:
  - Seedance 2.0
  - Sora
prompt_mode: seedance_director # seedance_director | seedance_json_en_zh | teaser_trailer_screenplay | sora_freeform | comparison_question
output_shape: prose # prose | json | bilingual_json | timecoded | shot_list | table
use_cases:
  - netflix_teaser
  - music_video
  - cinematic_character
  - product_reveal
aspect_ratio: 2.39:1
runtime_seconds: 12
```

Seedance-specific notes:
- Hermes currently has `seedance-director`, which emphasizes English-only production-ready prose, shot-structure header, duration, aspect ratio, camera/action/environment/style ordering, no negative prompt field, and a `Total: <Ns> / <N> shot(s) / <ratio>` close.
- omp also referenced a `seedance2-director` schema with EN+ZH JSON and scene archetype router (`action`, `general`, `dialogue`). `trailer-feed` should support both by storing `prompt_mode` and `output_shape` separately.
- Do not collapse Sora and Seedance prompts together. Sora cards can share evidence/rating fields but need their own prompt structure and scoring rubric.

## 1.3 Evidence grading fields

Separate evidence from usefulness. Do not make day-one Seedance cards useless just because reproducible ground truth is scarce.

```yaml
evidence_type: community_corroborated
# official | prompt_with_output | community_corroborated | practitioner_claim | generic_pattern | unknown

confidence: medium
# high | medium | low | speculative

source_count: 4
source_urls:
  - https://example.com/source-1
  - https://github.com/example/repo
source_notes:
  - Same camera-motion structure appeared in multiple independent examples.
  - No exact reproducible Seedance output yet.
```

Definitions:
- `official`: official model docs, release notes, cookbook, vendor sample.
- `prompt_with_output`: source includes prompt and visible/rendered output.
- `community_corroborated`: same technique appears in 3+ independent sources, or a creator shows multiple examples using the same structure, or the pattern matches known video-model behavior.
- `practitioner_claim`: a credible creator says it works but evidence is incomplete.
- `generic_pattern`: useful prompt-writing advice, not model-specific proof.
- `unknown`: imported candidate not yet vetted.

## 1.4 Library workflow fields

```yaml
library_status: adapted_template
# seed_pattern | adapted_template | internally_tested | promoted | deprecated

tested_by_us: false
test_runs:
  - run_id: hf-2026-07-02-001
    model: Seedance 2.0
    status: queued # queued | succeeded | failed | rejected | partial
    output_url:
    notes: Needs first internal render.

human_rating:
  gordo_score: null # 1-5 once rated
  aesthetic_fit: unrated # strong | good | mixed | weak | unrated
  production_readiness: draft # draft | usable | ready | archive
  notes:
```

Workflow:
1. `seed_pattern`: raw mined idea or source pattern.
2. `adapted_template`: rewritten into a reusable Trailer Feed card.
3. `internally_tested`: rendered or dry-run through our tooling.
4. `promoted`: recommended/top performer for a use case.
5. `deprecated`: model drift, poor results, duplicate, or failed aesthetic fit.

## 1.5 Prompt content fields / body sections

Each Markdown prompt card should include these sections in this order:

```markdown
# Emotional Camera Push Reveal

## At a glance
One tight paragraph explaining when to use the card.

## Reusable template
The copyable prompt template or structured prompt body.

## Variables
- subject:
- environment:
- emotional beat:
- camera motion:
- lighting:
- final close-up detail:

## Example prompt
A filled-in example ready to copy.

## Model-specific notes
### Seedance
Notes from seedance-director / seedance2-director.

### Sora
Notes for Sora-specific adaptation.

## Why this pattern may work
Evidence-aware reasoning.

## Source evidence
Bulleted source list with links and short excerpts.

## Test history
Render/test outcomes, links, screenshots, video refs.

## Gordo notes
Human taste notes and approvals/rejections.
```

---

# 2. Obsidian folder structure

Use this Obsidian layout as shared non-secret source of truth. `trailer-feed` can later mirror or import these files into its repo.

```text
20-Video-Workflows/
  Trailer Feed/
    README.md
    Trailer Feed Deep-Dive Plan.md

    schemas/
      prompt-card.schema.json
      prompt-pack.schema.json
      comparison-run.schema.json
      model-answer.schema.json

    indexes/
      prompt-cards.index.jsonl
      prompt-packs.index.jsonl
      comparison-runs.index.jsonl
      references.index.jsonl

    cards/
      seedance/
        seedance-camera-push-emotional-reveal.md
        seedance-product-orbit-hero-shot.md
      sora/
        sora-netflix-teaser-cold-open.md
      cross-model/
        netflix-teaser-act-structure.md

    packs/
      Seedance-Sora-Netflix-Teaser-Pack.md
      Music-Video-Camera-Language-Pack.md

    comparisons/
      2026-07-02-netflix-teaser-seedance-vs-sora/
        run.md
        answers.jsonl
        grades.jsonl
        winner-summary.md
        prompt-question.md

    references/
      videos/
        refs.index.jsonl
      docs/
        sources.index.jsonl
      images/
        refs.index.jsonl

    raw/
      2026-07-02-seedance-sora-research/
        run-manifest.json
        sources.jsonl
        extracted-prompts.jsonl
        extracted-patterns.jsonl
        notes.md
```

In the `trailer-feed` repo, mirror this as either:

```text
content/prompt-library/...
src/lib/prompt-library/...
```

or load directly from exported vault indexes during build/dev:

```text
public/data/prompt-cards.index.jsonl
public/data/comparison-runs.index.jsonl
```

Recommendation: for v1 app speed, copy generated JSONL indexes into `trailer-feed/public/data/` and render from there. Keep Markdown canonical in Obsidian until the app needs full editing.

---

# 3. Multi-agent / multi-model comparison flow

## 3.1 User story

Gordo asks one creative question, for example:

> “Create a Netflix-style teaser trailer prompt for Seedance and Sora for this concept. I want to compare model/agent answers and see who gives the strongest usable prompt.”

The system asks 3-5 agents/models the same question, stores answers, grades them, shows the table, and promotes the best outputs into prompt cards/packs.

## 3.2 Roles

Minimum useful comparison set:

1. `Seedance Director Agent`
   - Uses Seedance prompt rules.
   - Outputs Seedance-ready prompt, usually prose or JSON EN+ZH depending `prompt_mode`.

2. `Sora Trailer Agent`
   - Optimizes for Sora-style cinematic continuity and natural language scene description.
   - Should not blindly copy Seedance constraints.

3. `Trailer Screenplay Agent`
   - Uses Hermes `teaser-trailer-screenplay` skill style: timecoded acts, cut cadence, title-card mechanics, flash frames, audio sync.

4. `Creative Critic Agent`
   - Scores drama, clarity, novelty, visual specificity, and production readiness.

5. `Gordo Taste Proxy Agent` eventually
   - Learns from Gordo’s ratings and notes over time.
   - In v1, this is just a rubric seeded from Pindeck/Trailer Feed style notes and user comments.

## 3.3 Run artifact schema

`comparisons/<run-id>/run.md` frontmatter:

```yaml
---
run_id: dc-compare-2026-07-02-001
title: Netflix teaser comparison — Seedance vs Sora
question: Create a Netflix-style teaser trailer prompt for...
created: 2026-07-02
created_by: raycast
status: graded # draft | running | answers_collected | graded | promoted
models_requested:
  - Raycast Standard Model A
  - Raycast Standard Model B
  - Hermes selected model
  - Seedance Director Agent
  - Trailer Screenplay Agent
target_models:
  - Seedance 2.0
  - Sora
source_refs:
  - path: references/videos/example-ref.mp4
  - url: https://...
---
```

`answers.jsonl` line shape:

```json
{
  "answer_id": "ans-001",
  "run_id": "dc-compare-2026-07-02-001",
  "agent_name": "Seedance Director Agent",
  "model_name": "raycast-standard-latest",
  "model_class": "raycast_standard",
  "target_model": "Seedance 2.0",
  "prompt_mode": "seedance_director",
  "answer_text": "Single continuous shot, 12 seconds...",
  "structured_prompt": null,
  "created_at": "2026-07-02T00:00:00Z",
  "tokens_estimated": null,
  "source": "raycast"
}
```

`grades.jsonl` line shape:

```json
{
  "answer_id": "ans-001",
  "run_id": "dc-compare-2026-07-02-001",
  "grader": "Hermes Creative Critic",
  "scores": {
    "model_fit": 4,
    "visual_specificity": 5,
    "temporal_control": 4,
    "copy_paste_readiness": 5,
    "novelty": 3,
    "gordo_aesthetic_guess": 4,
    "evidence_alignment": 3
  },
  "weighted_total": 4.15,
  "class_rank": 1,
  "overall_rank": 2,
  "notes": "Strong Seedance camera language; could reduce overloaded constraints.",
  "promote_to_card": true
}
```

## 3.4 Comparison orchestration

Raycast-first path:

1. Gordo starts a Raycast Agent: “Prompt Comparison / Trailer Feed.”
2. Agent asks the same question to multiple Raycast models/agents where Raycast supports it.
3. Agent calls `raycast-pro-bridge` MCP tool:
   - `save_comparison_answer(run_id, agent_name, model_name, answer_text, metadata)`
4. Raycast calls Hermes via bridge:
   - `grade_comparison_run(run_id)`
   - `promote_winners_to_prompt_cards(run_id)`
5. Trailer Feed app reads `comparison-runs.index.jsonl` and shows the run.

Hermes-first path:

1. Gordo/omp tells Hermes to run a comparison.
2. Hermes asks local skills/subagents plus web/Higgsfield research where useful.
3. Raycast may be used manually for Raycast Pro model answers.
4. Answers are saved to Obsidian and indexed.

Important: do not fake Raycast model answers from Hermes. If a row says Raycast, it must come from Raycast.

## 3.5 Grading rubric

Score 1-5:

- `model_fit`: Does it fit Seedance/Sora specifically?
- `visual_specificity`: Concrete camera, lighting, subject, movement, texture.
- `temporal_control`: Clear duration, pacing, cuts, transitions.
- `copy_paste_readiness`: Can Gordo use it immediately?
- `novelty`: Not generic slop.
- `gordo_aesthetic_guess`: Fits known dark/dense/cinematic taste.
- `evidence_alignment`: Uses proven/community-corroborated prompt patterns.

Derived badges:

- `Top Seedance`
- `Top Sora`
- `Best Trailer Structure`
- `Best Visual Language`
- `Needs Human Taste Check`
- `Promoted`

---

# 4. Svelte 5 visual browser web app

## 4.1 Stack

Preferred:

- Svelte 5 with runes.
- SvelteKit unless the repo intentionally stays static-only.
- TanStack Table v9 Svelte adapter with runes support, marked alpha; isolate table adapter usage behind local components so it is easy to swap if API changes.
- TypeScript.
- Local JSONL/JSON data first.
- No backend required for Phase 0-1. Later add API routes for live rebuild/search if needed.

Suggested repo structure:

```text
trailer-feed/
  src/
    routes/
      +layout.svelte
      +page.svelte
      prompts/
        +page.svelte
        [id]/+page.svelte
      comparisons/
        +page.svelte
        [runId]/+page.svelte
      references/
        +page.svelte
      workflows/
        +page.svelte
    lib/
      data/
        promptCards.ts
        comparisons.ts
        jsonl.ts
      schemas/
        prompt-card.ts
        comparison-run.ts
      components/
        AppShell.svelte
        DenseTable.svelte
        PromptCardTable.svelte
        PromptCardPreview.svelte
        PromptDetailDrawer.svelte
        CopyPromptButton.svelte
        EvidenceBadge.svelte
        StatusBadge.svelte
        VideoReferenceCell.svelte
        ModelAnswerComparisonTable.svelte
        ScoreBar.svelte
        TagPill.svelte
      styles/
        tokens.css
        pindeck-theme.css
  public/
    data/
      prompt-cards.index.jsonl
      comparison-runs.index.jsonl
      references.index.jsonl
```

## 4.2 Routes

### `/`

Dashboard:
- Recent prompt cards.
- Recent comparison runs.
- Top promoted Seedance/Sora cards.
- “Needs Gordo rating” queue.
- Quick links to copy top prompts.

### `/prompts`

Dense visual prompt database.

Features:
- TanStack Table with filtering/sorting/grouping.
- Left filter rail: model family, use case, evidence type, status, tags, tested_by_us.
- Right preview drawer with Markdown excerpt, example prompt, video refs.
- Copy prompt button visible on row hover/selection.

### `/prompts/[id]`

Prompt detail page:
- Markdown-rendered full card.
- Reusable template and example prompt blocks with copy buttons.
- Evidence/source panel.
- Test history panel.
- Related cards/packs.
- Human rating area.

### `/comparisons`

Comparison run browser.

Columns:
- run title
- question summary
- status
- answer count
- top Seedance agent/model
- top Sora agent/model
- promoted count
- created date

### `/comparisons/[runId]`

Comparison detail:
- Original question at top.
- Model/agent answer table.
- Side-by-side prompt previews.
- Rubric scores.
- “Promoted to card” badges.
- Copy answer / copy rewritten winner.

### `/references`

Video/reference browser:
- Reference videos/images/docs used by prompt cards.
- Embed video previews when URL/file path exists.
- Link references to cards and comparison runs.

### `/workflows`

Saved creative workflows/setups:
- “Netflix teaser prompt comparison.”
- “Seedance music-video beat prompt.”
- “Sora cinematic scene expansion.”
- “Research run -> cards -> compare -> promote.”

## 4.3 TanStack Table columns

Prompt card columns:

```ts
const promptCardColumns = [
  'preview',              // thumbnail/video still if available
  'title',
  'model_family',
  'target_models',
  'use_cases',
  'evidence_type',
  'library_status',
  'confidence',
  'gordo_score',
  'tested_by_us',
  'source_count',
  'tags',
  'updated',
  'copy'
]
```

Comparison answer columns:

```ts
const comparisonAnswerColumns = [
  'rank',
  'agent_name',
  'model_name',
  'target_model',
  'prompt_mode',
  'weighted_total',
  'model_fit',
  'visual_specificity',
  'temporal_control',
  'copy_paste_readiness',
  'novelty',
  'gordo_aesthetic_guess',
  'promote_to_card',
  'copy'
]
```

## 4.4 Data loading

V1:
- Fetch `/data/prompt-cards.index.jsonl` in the browser.
- Parse JSONL client-side.
- Fetch detail Markdown only when opening a detail page/drawer, or store enough preview text in the index.

V2:
- Add SvelteKit server loaders or static generated JSON.
- Add search indexes generated by Hermes/Node script.
- Add `pnpm/bun run rebuild:index` script that reads Markdown cards and writes JSONL.

Parsing utility:

```ts
export function parseJsonl<T>(text: string): T[] {
  return text
    .split('\n')
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line) => JSON.parse(line) as T);
}
```

## 4.5 Copy-to-clipboard prompts

Copy buttons:
- `Copy template`
- `Copy example`
- `Copy Seedance prompt`
- `Copy Sora prompt`
- `Copy winner`

Implementation:
- Browser `navigator.clipboard.writeText`.
- Small HUD/toast: “Copied Seedance prompt.”
- Avoid huge CTA buttons. Compact, subtle, fast.

## 4.6 Video/reference embedding

Reference object shape:

```json
{
  "ref_id": "ref-001",
  "type": "video",
  "title": "Night flood music video reference",
  "url": "https://...",
  "local_path": null,
  "thumbnail_url": "https://...",
  "linked_cards": ["seedance-camera-push-emotional-reveal"],
  "notes": "Used for falling camera orbit and water impact pacing."
}
```

UI rules:
- Use thumbnail-first cards. Do not mount many `<video>` elements in a table.
- In tables, show still thumbnail + duration + source badge.
- Open video in drawer/modal only on click.
- Keep scrolling snappy.

## 4.7 Visual style tokens

Adopt Pindeck-like dark/dense tokens as the initial house style:

```css
:root {
  --dc-bg: #08080a;
  --dc-panel: rgba(18, 18, 22, 0.82);
  --dc-panel-strong: #111116;
  --dc-border: rgba(255, 255, 255, 0.08);
  --dc-border-strong: rgba(255, 255, 255, 0.14);
  --dc-text: #f2f2f4;
  --dc-muted: #8d8d99;
  --dc-subtle: #5c5c66;
  --dc-accent: #3a7bff;
  --dc-accent-soft: rgba(58, 123, 255, 0.16);
  --dc-danger: #ff4d5e;
  --dc-warn: #f4b860;
  --dc-good: #44d07b;
  --dc-radius-xs: 3px;
  --dc-radius-sm: 5px;
  --dc-radius-md: 8px;
  --dc-font-size: 13px;
  --dc-font-small: 12px;
  --dc-row-height: 42px;
}
```

UI tone:
- Dark, image-first, compact 13px body.
- Small radii 3-5px for controls/cards.
- Glass panels only for floating overlays/drawers, not everything.
- Dense table rows, subtle hover, sticky header.
- Small compact buttons, not large CTA blocks.
- Use color as signal: evidence/status/ranking, not decoration overload.

---

# 5. How Trailer Feed consumes Raycast and Hermes

## 5.1 Boundary between repos

`raycast-pro-bridge` owns:
- HTTP MCP server Raycast points to.
- Raycast AI Commands config.
- Raycast Agents config.
- Script Commands.
- Raycast extension research/prototypes.
- Tailscale/HTTP bridge docs.

`trailer-feed` owns:
- Prompt library schemas.
- Prompt cards and prompt packs.
- Comparison run artifacts.
- Reference/video database.
- Svelte visual browser.
- Creative workflows.
- Ratings and promotion workflow.

## 5.2 MCP tools Trailer Feed expects from raycast-pro-bridge

Minimum tool surface:

```text
start_prompt_research(topic, target_models, use_cases, depth)
get_research_status(job_id)
read_research_artifact(job_id, artifact_name)
search_prompt_library(query, filters)
save_prompt_pack(pack)
save_comparison_answer(run_id, answer)
grade_comparison_run(run_id)
promote_winners_to_prompt_cards(run_id)
```

For v1, only five are required:

```text
start_prompt_research
get_research_status
read_research_artifact
search_prompt_library
save_prompt_pack
```

Comparison tools can be manual or Hermes-side until the library proves value.

## 5.3 Research flow

1. Raycast Agent starts a session:
   - “Mine Seedance/Sora prompt patterns for Netflix teaser trailers.”
2. Raycast calls MCP tool in `raycast-pro-bridge`:
   - `start_prompt_research(...)`
3. Bridge dispatches Hermes job:
   - web/GitHub search
   - source extraction
   - pattern clustering
   - evidence labeling
   - candidate prompt cards
4. Hermes writes to Obsidian:
   - raw sources
   - extracted candidates
   - draft cards
   - indexes
5. Trailer Feed app reads JSONL index and displays cards/runs.
6. Gordo rates/promotes cards.

## 5.4 Comparison flow

1. Raycast asks multiple Agents/models the same question.
2. Raycast/bridge saves each answer to `comparisons/<run-id>/answers.jsonl`.
3. Hermes grades with rubric and writes `grades.jsonl`.
4. Trailer Feed app displays rankings and copy buttons.
5. Best answers become cards or pack entries.

## 5.5 Hermes responsibilities

Hermes should own:
- durable research runs
- indexing Markdown to JSONL
- evidence grading
- Obsidian writes
- prompt-card promotion
- optional Higgsfield/Seedance test runs
- quality review of generated cards

Hermes should not pretend to be Raycast Pro. If a card or row uses Raycast model output, provenance must say so and the answer must come from Raycast.

---

# 6. Build phases / milestones

## Phase 0 — One-hour proof, library first

Goal: prove the creative loop before plumbing.

Deliverables:
- Obsidian folder structure under `20-Video-Workflows/Trailer Feed/`.
- `prompt-card.schema.json` draft.
- 5-10 Markdown prompt cards for Seedance/Sora teaser patterns.
- `prompt-cards.index.jsonl` generated manually or by a small script.
- One comparison run folder with 3-5 manually collected answers if Raycast is available.

Steps:
1. Create folder structure in Obsidian.
2. Create one card template and one comparison-run template.
3. Run focused Hermes research:
   - GitHub + web for Seedance prompt patterns.
   - Web for Sora teaser/trailer prompting patterns.
   - Tag evidence using `evidence_type`.
4. Create cards:
   - at least 3 Seedance cards
   - at least 2 Sora cards
   - at least 1 cross-model Netflix teaser card
5. Generate JSONL index.
6. Manually review in Obsidian.

Success criteria:
- Gordo can open Obsidian and see useful prompt cards.
- At least one card is copy-paste usable.
- Evidence/status fields feel useful instead of bureaucratic.
- No app or bridge required yet.

## Phase 1 — Static Svelte visual browser

Goal: browse/search/copy the library.

Deliverables in `trailer-feed`:
- Svelte 5 app scaffold.
- Pindeck-style tokens.
- `/prompts` table reading `public/data/prompt-cards.index.jsonl`.
- Prompt detail drawer.
- Copy buttons.
- Basic filters.

Tasks:
1. Scaffold SvelteKit/Svelte 5 app.
2. Add `tokens.css` and dark dense layout.
3. Add JSONL loader.
4. Add TanStack Table v9 wrapper component, isolated behind `DenseTable.svelte`.
5. Build prompt card table.
6. Build detail drawer and copy actions.
7. Verify with real JSONL exported from Obsidian.

Success criteria:
- App opens quickly.
- Table is dense, dark, and visually close to Pindeck target.
- Copy prompt works.
- Filtering by model/status/evidence works.

## Phase 2 — Comparison run browser

Goal: make multi-agent answers legible.

Deliverables:
- `/comparisons` route.
- `/comparisons/[runId]` detail route.
- Model answer table with rubric columns.
- Ranking badges and “Top Seedance/Sora” labels.
- Promote/copy UI; promotion can still be manual in Phase 2.

Success criteria:
- One run with 3-5 answers displays cleanly.
- Gordo can identify winner per class.
- Output is easy to copy and promote.

## Phase 3 — Raycast/Hermes bridge integration

Goal: remove manual relay for research and saves.

Dependency: `raycast-pro-bridge` HTTP MCP server exists.

Deliverables:
- Trailer Feed docs describing expected bridge tools.
- Import/sync scripts that consume bridge outputs.
- Raycast workflow: start research -> save artifacts -> app shows results.

Success criteria:
- Raycast starts a prompt research run.
- Hermes writes artifacts to Obsidian.
- Trailer Feed app sees updated JSONL after rebuild/copy.

## Phase 4 — Rating and aesthetic memory loop

Goal: turn Gordo ratings into useful taste signal.

Deliverables:
- `human_rating` UI fields.
- Notes for why a prompt did/did not fit.
- `Gordo Taste Proxy` seed document generated from promoted/deprecated examples.
- “Needs rating” dashboard queue.

Success criteria:
- After rating 20-30 cards, system can summarize what Gordo likes/dislikes.
- Future comparison grading uses the learned taste notes as context.

## Phase 5 — Production/test integration

Goal: connect winning prompts to generation/test outputs.

Deliverables:
- Test run records linked to Higgsfield/Seedance outputs.
- Video references embedded in app.
- Status badges for `internally_tested`, `promoted`, `deprecated`.
- Optional generation queue.

Success criteria:
- A prompt card can show source evidence, generated output, Gordo rating, and final promoted status in one place.

---

# 7. Immediate next tasks

## Task 1: Create canonical Obsidian folders

Create:

```text
/root/Github/hermes-notebook-vault/20-Video-Workflows/Trailer Feed/
/root/Github/hermes-notebook-vault/20-Video-Workflows/Trailer Feed/cards/seedance/
/root/Github/hermes-notebook-vault/20-Video-Workflows/Trailer Feed/cards/sora/
/root/Github/hermes-notebook-vault/20-Video-Workflows/Trailer Feed/cards/cross-model/
/root/Github/hermes-notebook-vault/20-Video-Workflows/Trailer Feed/comparisons/
/root/Github/hermes-notebook-vault/20-Video-Workflows/Trailer Feed/indexes/
/root/Github/hermes-notebook-vault/20-Video-Workflows/Trailer Feed/raw/
/root/Github/hermes-notebook-vault/20-Video-Workflows/Trailer Feed/schemas/
```

## Task 2: Write schema drafts

Create:
- `schemas/prompt-card.schema.json`
- `schemas/comparison-run.schema.json`
- `schemas/model-answer.schema.json`

Keep schemas permissive in v1. Validate required fields only:
- `id`
- `title`
- `model_family`
- `evidence_type`
- `library_status`
- `tags`
- `updated`

## Task 3: Create one manually curated seed card

Use the Hermes `seedance-director` skill and/or omp's `seedance2-director` schema as the first card basis.

Recommended first card:
- `seedance-netflix-teaser-title-slam.md`
- `model_family: seedance`
- `use_cases: [netflix_teaser, trailer, title_card]`
- `evidence_type: generic_pattern` until researched.
- `library_status: adapted_template`

## Task 4: Generate JSONL index

Write a small script in `trailer-feed` later, but for Phase 0 a Hermes script can parse frontmatter and emit:

```text
20-Video-Workflows/Trailer Feed/indexes/prompt-cards.index.jsonl
```

## Task 5: Scaffold app only after cards exist

Do not start with UI blank-state plumbing. Build the Svelte app against real cards and one real comparison run.

---

# 8. Open questions

- Where should `trailer-feed` keep a copy of prompt cards: mirrored from Obsidian into repo, or app reads exported JSONL only?
  - Recommendation: JSONL export only for v1, Markdown canonical in Obsidian.
- Does Gordo want app-side editing in Phase 1?
  - Recommendation: no. Read/copy/filter first. Edit in Obsidian.
- Which exact Raycast models/classes count as “newest standard-tier”?
  - raycast-pro-bridge should record model name/class at answer-save time.
- Where is omp's `seedance2-director` JSON EN+ZH skill stored?
  - Need to import/reference it explicitly if it should become the canonical Seedance JSON adapter.
- Should Sora prompt schema be its own skill/card type?
  - Recommendation: yes, after 5-10 Sora cards reveal recurring structure.

---

# 9. Definition of done for this plan

This plan is ready to pull into `trailer-feed` when:

- It is saved in the synced Obsidian vault.
- The repo owner can copy the folder structure and schemas into the repo.
- The first app milestone has concrete data shapes and route/component names.
- The relationship to `raycast-pro-bridge` is explicit and narrow.
- The Seedance/Sora/trailer prompt workflows are treated as creative assets, not generic notes.
