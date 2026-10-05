<script lang="ts">
  import LegacyText from '$lib/components/LegacyText.svelte';
  import { page } from '$app/state';
  import { goto } from '$app/navigation';
  import ProjectCard from '$lib/components/ProjectCard.svelte';
  import ProjectThumbnailPanel from '$lib/components/ProjectThumbnailPanel.svelte';
  import ClipCard from '$lib/components/ClipCard.svelte';
  import TakePlayer, { type CompareMode } from '$lib/components/TakePlayer.svelte';
  import GlassModal from '$lib/components/GlassModal.svelte';
  import VersionDropzone from '$lib/components/VersionDropzone.svelte';
  import VersionDetails from '$lib/components/VersionDetails.svelte';
  import CopyButton from '$lib/components/CopyButton.svelte';
  import Icon from '$lib/components/Icon.svelte';
  import { studio, plural, type Take } from '$lib/ui/studio.svelte';
  import { toneFor } from '$lib/ui/tones';
  import { mediaApi } from '$lib/data/media-api';
  import { parseRunQuestion } from '$lib/data/run-brief';
  import { removeProject, saveProjectText, signInOwner, SignInRequired } from '$lib/data/titles';
  import type { GenerationPrompt, ModelAnswer } from '$lib/types/comparison';

  type Drawer = 'prompt' | 'shots' | 'versions' | 'source' | 'thumbnail';

  const project = $derived(studio.project(page.url.searchParams.get('run')) ?? studio.projects[0]);
  const takes = $derived(project?.takes ?? []);
  const take = $derived(takes.find((t) => t.id === page.url.searchParams.get('take')) ?? takes.at(-1));
  const takeIndex = $derived(take ? takes.indexOf(take) : -1);

  let compareId = $state<string | null>(null);
  const compareTake = $derived(
    takes.find((t) => t.id === compareId && t.id !== take?.id) ?? takes[takeIndex - 1] ?? takes.find((t) => t.id !== take?.id),
  );

  let mode = $state<CompareMode>('watch');
  let drawer = $state<Drawer>('prompt');
  let importOpen = $state(false);
  let shotUrl = $state<string | null>(null);
  let dropzone = $state<ReturnType<typeof VersionDropzone>>();
  let pendingFiles = $state<File[]>([]);
  let draggingCut = $state(false);
  let writerId = $state<string | null>(null);
  let details = $state<ReturnType<typeof VersionDetails>>();

  const detail = $derived(project?.detail);
  const promptsMap = $derived(new Map<string, GenerationPrompt>((detail?.prompts ?? []).map((p) => [p.prompt_id, p])));
  const writers = $derived((detail?.answers ?? []).filter((answer) => answer.ui_status !== 'missing'));
  const writer = $derived(writers.find((w) => w.answer_id === writerId) ?? writers.find((w) => w.answer_id === take?.artifact.answer_id) ?? writers[0]);
  const grids = $derived(
    (detail?.artifacts ?? []).filter((a) => a.media_url && (a.artifact_type === 'shot_grid' || a.artifact_type === 'image_result')),
  );
  const shots = $derived([
    ...new Set([
      ...(project?.shotGrids ?? []).map((grid) => grid.media_url!),
      ...takes.flatMap((t) => (t.artifact.shot_grid_url ? [t.artifact.shot_grid_url] : [])),
    ]),
  ]);
  const question = $derived(detail?.question?.trim() ?? '');
  const brief = $derived(detail?.brief?.trim() || parseRunQuestion(question).creativeBrief || '');

  function go(runId: string, takeId?: string) {
    const params = new URLSearchParams({ run: runId });
    if (takeId) params.set('take', takeId);
    void goto(`?${params}`, { replaceState: true, noScroll: true, keepFocus: true });
  }

  function selectProject(runId: string) {
    if (runId === project?.runId) return;
    compareId = null;
    writerId = null;
    mode = 'watch';
    cancelRename();
    go(runId);
  }

  function selectTake(next: Take) {
    if (!project) return;
    // Comparing: the take on screen becomes the one it's compared against.
    if (mode !== 'watch' && take && next.id !== take.id) compareId = take.id;
    go(project.runId, next.id);
  }

  function step(direction: number) {
    if (!project || takes.length < 2) return;
    const next = takes[(takeIndex + direction + takes.length) % takes.length];
    go(project.runId, next.id);
  }

  function writerConcept(answer: ModelAnswer) {
    const concept = answer.structured_prompt;
    if (concept && typeof concept === 'object' && !Array.isArray(concept) && 'summary' in concept) {
      return { title: String(concept.title ?? ''), logline: String(concept.logline ?? ''), body: String(concept.summary ?? '') };
    }
    return { title: '', logline: '', body: answer.answer_text };
  }

  async function reload() {
    if (project) await studio.reload(project.runId);
  }

  function dropCut(event: DragEvent) {
    event.preventDefault();
    draggingCut = false;
    pendingFiles = Array.from(event.dataTransfer?.files ?? []);
    importOpen = true;
  }

  // Hand a dropped cut to the dropzone once the import modal has mounted it.
  $effect(() => {
    if (dropzone && pendingFiles.length) {
      dropzone.add(pendingFiles);
      pendingFiles = [];
    }
  });

  $effect(() => {
    void studio.ensure();
    const interval = setInterval(() => void studio.refresh(), 15000);
    return () => clearInterval(interval);
  });

  // ── Rename (owner sign-in) ─────────────────────────────────────────
  let editing = $state(false);
  let titleDraft = $state('');
  let loglineDraft = $state('');
  let renameBusy = $state(false);
  let renameError = $state('');
  let needSignIn = $state(false);
  let password = $state('');
  let removeOpen = $state(false);
  let removeConfirm = $state('');
  let removeBusy = $state(false);
  let removeError = $state('');
  let removePassword = $state('');
  let removeNeedSignIn = $state(false);

  function openRemove() {
    removeConfirm = '';
    removeError = '';
    removePassword = '';
    removeNeedSignIn = false;
    removeOpen = true;
  }

  async function confirmRemove(event: SubmitEvent) {
    event.preventDefault();
    if (!project || removeConfirm !== project.title || removeBusy) return;
    const runId = project.runId;
    removeBusy = true;
    removeError = '';
    try {
      if (removeNeedSignIn) await signInOwner(removePassword);
      await removeProject(runId);
      removeOpen = false;
      studio.forget(runId);
      const next = studio.projects[0];
      await goto(next ? `/comparisons?run=${encodeURIComponent(next.runId)}` : '/comparisons', { replaceState: true });
    } catch (error) {
      if (error instanceof SignInRequired) removeNeedSignIn = true;
      removeError = error instanceof Error ? error.message : 'Project removal failed';
    } finally {
      removeBusy = false;
    }
  }

  function startRename() {
    titleDraft = project?.fullTitle ?? '';
    loglineDraft = project?.detail.logline ?? project?.logline ?? '';
    renameError = '';
    editing = true;
  }

  function cancelRename() {
    editing = false;
    renameError = '';
    password = '';
  }

  async function saveRename(event: SubmitEvent) {
    event.preventDefault();
    if (!project || !titleDraft.trim()) return;
    renameBusy = true;
    renameError = '';
    try {
      if (needSignIn) {
        await signInOwner(password);
        password = '';
        needSignIn = false;
      }
      await saveProjectText(project.runId, { title: titleDraft.trim(), logline: loglineDraft.trim() });
      await reload();
      editing = false;
    } catch (error) {
      if (error instanceof SignInRequired) needSignIn = true;
      renameError = error instanceof Error ? error.message : 'Save failed';
    } finally {
      renameBusy = false;
    }
  }
</script>

<svelte:head>
  <title>{project ? `${project.title} · Projects` : 'Projects'} · Trailer Feed</title>
</svelte:head>

<div class="studio-column projects">
  {#if !studio.loaded}
    <p class="state"><Icon name="loader" size={16} /> Opening the review bay…</p>
  {:else if !project}
    <div class="state-empty">
      <h1 class="t-page">No projects yet</h1>
      <p class="muted">Import a finished video to start your portfolio.</p>
      <a class="sbtn sbtn-primary" href="/create"><Icon name="sparkles" /> Import project</a>
    </div>
  {:else}
    {#if studio.projects.length > 1}
      <nav class="strip" aria-label="Projects">
        {#each studio.projects as p (p.runId)}
          <div class="strip-item">
            <ProjectCard
              compact
              title={p.title}
              fullTitle={p.fullTitle}
              cover={p.takes.at(-1)?.artifact ?? p.shotGrids[0]}
              thumbnailUrl={p.projectThumbnailUrl}
              selected={p.runId === project.runId}
              onselect={() => selectProject(p.runId)}
            />
          </div>
        {/each}
      </nav>
    {/if}

    <header class="head">
      <div class="head-copy">
        {#if editing}
          <form class="rename" onsubmit={saveRename}>
            <input class="sinput" bind:value={titleDraft} maxlength="120" aria-label="Project title" placeholder="Project title" disabled={renameBusy} />
            <textarea class="stextarea" bind:value={loglineDraft} rows="2" maxlength="600" aria-label="Logline" placeholder="Logline: who, what pulls them in, and what it costs" disabled={renameBusy}></textarea>
            <div class="rename-actions">
              {#if needSignIn}
                <input class="sinput password" type="password" bind:value={password} placeholder="Owner password" autocomplete="current-password" aria-label="Owner password" disabled={renameBusy} />
              {/if}
              <button type="submit" class="sbtn sbtn-primary" disabled={renameBusy || !titleDraft.trim() || (needSignIn && !password)}>
                {renameBusy ? 'Saving…' : 'Save'}
              </button>
              <button type="button" class="sbtn" onclick={cancelRename} disabled={renameBusy}>Cancel</button>
            </div>
            {#if renameError}<p class="error" role="alert">{renameError}</p>{/if}
          </form>
        {:else}
          <div class="title-row">
            <h1 class="t-page" title={project.fullTitle}><LegacyText text={project.title} /></h1>
            <button type="button" class="sbtn" onclick={startRename}><Icon name="edit" size={12} /> Rename</button>
            <button type="button" class="sbtn" onclick={openRemove}>Remove project</button>
          </div>
          <p class="logline" title={project.logline}><LegacyText text={project.logline} /></p>
        {/if}
        {#if studio.pending.includes(project.runId)}
          <p class="pending" role="status"><Icon name="loader" size={12} /> Saved. Showing the change here as soon as the catalog can be read again.</p>
        {/if}
        <div class="tags">
          <span class="stag tone-{toneFor(project.status)}">{project.status}</span>
          <span class="stag tone-review">{plural(takes.length, 'take')}</span>
          {#each writers as w (w.answer_id)}
            <span class="stag tone-{toneFor(w.model_name)}">{w.model_name}</span>
          {/each}
        </div>
      </div>
      <div class="head-actions">
        <button type="button" class="sbtn" onclick={() => (importOpen = true)}><Icon name="upload" /> Import cut</button>
      </div>
    </header>

    {#if take}
      <section class="review" aria-label="Takes">
        <TakePlayer
          primary={take}
          secondary={compareTake}
          bind:mode
          canStep={takes.length > 1}
          onprev={() => step(-1)}
          onnext={() => step(1)}
        />
        <div class="rail" aria-label="All takes">
          {#each takes.toReversed() as t (t.id)}
            <div class="rail-item">
              <ClipCard
                density="thumb"
                title={project.title}
                fullTitle={`${project.fullTitle} ${t.code}`}
                takeLabel={t.code}
                writer={t.writer}
                videoModel={t.model}
                videoUrl={t.artifact.media_url}
                thumbnailUrl={t.artifact.thumbnail_url}
                isNewest={t.isNewest}
                playOnHover={studio.playOnHover}
                selected={t.id === take.id || (mode !== 'watch' && t.id === compareTake?.id)}
                onselect={() => selectTake(t)}
              />
            </div>
          {/each}
        </div>
      </section>
    {:else}
      <button
        type="button"
        class="empty-drop"
        class:dragging={draggingCut}
        ondragover={(e) => { e.preventDefault(); draggingCut = true; }}
        ondragleave={() => (draggingCut = false)}
        ondrop={dropCut}
        onclick={() => (importOpen = true)}
      >
        <Icon name="upload" size={20} />
        <strong>No takes yet</strong>
        <span class="muted">Drop a cut here, or generate the first take.</span>
      </button>
    {/if}

    <section class="drawer">
      <div class="drawer-tabs" role="tablist" aria-label="Project details">
        {#each [['prompt', 'Prompt'], ['shots', `Shots${shots.length ? ` ${shots.length}` : ''}`], ['versions', `Versions ${takes.length}`], ['source', 'Source'], ['thumbnail', 'Thumbnail']] as [id, label] (id)}
          <button type="button" role="tab" class="tab" class:active={drawer === id} aria-selected={drawer === id} onclick={() => (drawer = id as Drawer)}>
            {label}
          </button>
        {/each}
      </div>

      {#if drawer === 'prompt'}
        <div class="panel glass-panel">
          {#if take}
            <div class="panel-head">
              <div class="panel-title">
                <h2 class="t-body">Take {take.code}</h2>
                {#if take.model}<span class="stag tone-{toneFor(take.model)}"><LegacyText text={take.model} /></span>{/if}
              </div>
              {#if mediaApi}
                <button type="button" class="sbtn" onclick={() => details?.edit()}><Icon name="edit" size={12} /> Edit version details</button>
              {/if}
            </div>
            {#key take.id}
              <VersionDetails bind:this={details} artifact={take.artifact} showHeading={false} {grids} {promptsMap} onSaved={reload} />
            {/key}
          {/if}

          {#if writers.length}
            <div class="writers">
              <div class="panel-head">
                <h2 class="t-body">Writers room</h2>
                <div class="writer-tags" role="group" aria-label="Writers">
                  {#each writers as w (w.answer_id)}
                    <button
                      type="button"
                      class="stag tone-{toneFor(w.model_name)}"
                      class:selected={w.answer_id === writer?.answer_id}
                      aria-pressed={w.answer_id === writer?.answer_id}
                      onclick={() => (writerId = w.answer_id)}
                    >
                      {w.model_name}
                    </button>
                  {/each}
                </div>
              </div>
              {#if writer}
                {@const concept = writerConcept(writer)}
                <div class="treatment raised">
                  {#if concept.title}<p class="t-card"><LegacyText text={concept.title} /></p>{/if}
                  {#if concept.logline}<p class="treatment-logline"><LegacyText text={concept.logline} /></p>{/if}
                  <p class="treatment-body"><LegacyText text={concept.body} /></p>
                  <div class="treatment-actions"><CopyButton text={concept.body} label="Copy" /></div>
                </div>
              {/if}
            </div>
          {/if}
        </div>
      {:else if drawer === 'shots'}
        {#if shots.length}
          <div class="shots">
            {#each shots as url (url)}
              <button type="button" class="shot" onclick={() => (shotUrl = url)} aria-label="Open shot grid">
                <img src={url} alt="" loading="lazy" />
              </button>
            {/each}
          </div>
        {:else}
          <p class="panel-note muted">No shot grids yet. Attach one to a take with Edit version details.</p>
        {/if}
      {:else if drawer === 'versions'}
        <div class="versions">
          {#each takes.toReversed() as t (t.id)}
            <div class="version-item">
              <ClipCard
                density="thumb"
                title={project.title}
                takeLabel={t.code}
                writer={t.writer}
                videoModel={t.model}
                videoUrl={t.artifact.media_url}
                thumbnailUrl={t.artifact.thumbnail_url}
                isNewest={t.isNewest}
                playOnHover={studio.playOnHover}
                selected={t.id === take?.id}
                onselect={() => selectTake(t)}
              />
            </div>
          {/each}
          <button
            type="button"
            class="version-item drop-tile"
            class:dragging={draggingCut}
            ondragover={(e) => { e.preventDefault(); draggingCut = true; }}
            ondragleave={() => (draggingCut = false)}
            ondrop={dropCut}
            onclick={() => (importOpen = true)}
          >
            <Icon name="upload" size={18} />
            <span>Drop a cut</span>
          </button>
        </div>
      {:else if drawer === 'source'}
        <div class="panel glass-panel source">
          {#if brief}<p class="source-brief"><LegacyText text={brief} /></p>{/if}
          {#if question}
            <pre><LegacyText text={question} /></pre>
          {:else}
            <p class="muted">No source saved for this project.</p>
          {/if}
        </div>
      {:else if drawer === 'thumbnail'}
        {#key project.runId}<ProjectThumbnailPanel {project} onSaved={reload} />{/key}
      {/if}
    </section>


    {#if importOpen}
      <GlassModal title="Import cut" fullTitle={`Import a cut into ${project.fullTitle}`} onclose={() => (importOpen = false)}>
        <VersionDropzone bind:this={dropzone} runId={project.runId} title={project.title} onAdded={reload} />
        <p class="modal-note muted">Each file becomes the next take. Afterwards, use Edit version details to attach its prompt, shot grid and video model.</p>
      </GlassModal>
    {/if}

    {#if shotUrl}
      <GlassModal title="Shot grid" width={1120} onclose={() => (shotUrl = null)}>
        <img class="shot-full" src={shotUrl} alt="Shot grid" />
      </GlassModal>
    {/if}
    {#if removeOpen}
      <GlassModal title="Remove project" fullTitle={`Remove ${project.fullTitle}`} onclose={() => { if (!removeBusy) removeOpen = false; }}>
        <form class="rename" onsubmit={confirmRemove}>
          <p>This permanently removes <strong>{project.title}</strong>, its {plural(takes.length, 'take')}, and uploaded video files stored for this project. This cannot be undone.</p>
          <p class="muted">Project ID: <code>{project.runId}</code></p>
          <p class="muted">Type the project title to confirm: <strong>{project.title}</strong></p>
          <input class="sinput" bind:value={removeConfirm} aria-label="Type project title to confirm removal" autocomplete="off" disabled={removeBusy} />
          {#if removeNeedSignIn}
            <input class="sinput password" type="password" bind:value={removePassword} placeholder="Owner password" autocomplete="current-password" aria-label="Owner password" disabled={removeBusy} />
          {/if}
          {#if removeError}<p class="error" role="alert">{removeError}</p>{/if}
          <div class="rename-actions">
            <button type="submit" class="sbtn sbtn-danger" disabled={removeBusy || removeConfirm !== project.title || (removeNeedSignIn && !removePassword)}>{removeBusy ? 'Removing…' : 'Remove project and videos'}</button>
            <button type="button" class="sbtn" onclick={() => (removeOpen = false)} disabled={removeBusy}>Cancel</button>
          </div>
        </form>
      </GlassModal>
    {/if}
  {/if}
</div>

<style>
  .projects {
    display: grid;
    grid-template-columns: minmax(0, 1fr);
    gap: 24px;
    padding-top: 20px;
    padding-bottom: 64px;
  }

  .state {
    display: flex;
    align-items: center;
    gap: 10px;
    margin: 72px 0;
    color: var(--dc-text-muted);
    font-size: 14px;
  }

  .state-empty {
    display: grid;
    justify-items: start;
    gap: 12px;
    padding-block: 48px;
  }

  .state-empty p {
    margin: 0;
  }

  /* ── Poster strip ─────────────────────────────────────────────── */

  .strip {
    display: flex;
    gap: 12px;
    overflow-x: auto;
    scrollbar-width: none;
    scroll-snap-type: x proximity;
  }

  .strip::-webkit-scrollbar {
    display: none;
  }

  .strip-item {
    flex: 0 0 clamp(150px, 16vw, 210px);
    scroll-snap-align: start;
  }

  /* ── Header ───────────────────────────────────────────────────── */

  .head {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 16px 24px;
  }

  .head-copy {
    flex: 1;
    min-width: 0;
  }

  .title-row {
    display: flex;
    flex-wrap: wrap;
    min-width: 0;
    align-items: center;
    gap: 12px;
  }

  .logline {
    display: -webkit-box;
    max-width: 780px;
    height: calc(2 * 1.5em);
    margin: 8px 0 0;
    overflow: hidden;
    color: var(--dc-text-muted);
    font-size: 14px;
    line-height: 1.5;
    line-clamp: 2;
    -webkit-box-orient: vertical;
    -webkit-line-clamp: 2;
  }

  .tags {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    margin-top: 12px;
  }

  .pending {
    display: flex;
    align-items: center;
    gap: 6px;
    margin: 8px 0 0;
    color: var(--dc-text-muted);
    font-size: 12px;
  }

  .head-actions {
    display: flex;
    flex-shrink: 0;
    flex-wrap: wrap;
    gap: 8px;
  }

  .rename {
    display: grid;
    gap: 8px;
    max-width: 720px;
  }

  .rename-actions {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 8px;
  }

  .password {
    width: 200px;
  }

  .sbtn-danger {
    background: #843b38;
    color: #fff;
  }

  .sbtn-danger:hover:not(:disabled) {
    background: #a14742;
  }

  .error {
    margin: 0;
    color: #f0a8a0;
    font-size: 12px;
  }

  /* ── Player + rail ────────────────────────────────────────────── */

  .review {
    display: grid;
    grid-template-columns: minmax(0, 1fr) 184px;
    gap: 12px;
    align-items: start;
  }

  .rail {
    display: flex;
    flex-direction: column;
    gap: 8px;
    max-height: calc((100vw - 2 * var(--dc-gutter-x) - 196px) * 9 / 16);
    overflow-y: auto;
    scrollbar-width: none;
  }

  .rail::-webkit-scrollbar {
    display: none;
  }

  .rail-item {
    flex-shrink: 0;
  }

  @media (min-width: 1473px) {
    .rail {
      max-height: calc((var(--dc-page-max) - 196px) * 9 / 16);
    }
  }

  .empty-drop,
  .drop-tile {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 8px;
    border: 0;
    border-radius: 8px;
    background: #0e0e0e;
    color: var(--dc-text);
    font: inherit;
    font-size: 13px;
    cursor: pointer;
    transition: background 0.15s ease;
  }

  .empty-drop {
    aspect-ratio: 16 / 9;
    max-height: 60vh;
  }

  .empty-drop strong {
    font: 400 24px / 1.2 var(--dc-font-serif);
  }

  .empty-drop:hover,
  .drop-tile:hover,
  .dragging {
    background: #1a1a1a;
  }

  /* ── Drawer ───────────────────────────────────────────────────── */

  .drawer-tabs {
    display: flex;
    gap: 2px;
    margin-bottom: 12px;
    overflow-x: auto;
    scrollbar-width: none;
  }

  .tab {
    flex-shrink: 0;
    height: 28px;
    padding: 0 12px;
    border: 0;
    border-radius: 4px;
    background: transparent;
    color: var(--dc-text-muted);
    font: 13px var(--dc-font-sans);
    cursor: pointer;
    transition: background 0.15s ease, color 0.15s ease;
  }

  .tab:hover {
    background: #0e0e0e;
    color: var(--dc-text);
  }

  .tab.active {
    background: #1f1f1f;
    color: var(--dc-text);
  }

  .panel {
    display: grid;
    gap: 18px;
    padding: 18px;
  }

  .panel-head {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    justify-content: space-between;
    gap: 8px 12px;
    margin-bottom: 12px;
  }

  .panel-title,
  .writer-tags {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 6px;
  }

  .panel-title .t-body,
  .writers .t-body {
    width: auto;
  }

  .writers {
    padding-top: 8px;
  }

  .treatment {
    padding: 14px 16px;
  }

  .treatment p {
    margin: 0;
  }

  .treatment-logline {
    margin-top: 6px !important;
    color: var(--dc-text);
    font-size: 14px;
    line-height: 1.5;
  }

  .treatment-body {
    margin-top: 10px !important;
    color: var(--dc-text-muted);
    font-size: 14px;
    line-height: 1.6;
    white-space: pre-wrap;
  }

  .treatment-actions {
    margin-top: 12px;
  }

  .panel-note {
    margin: 0;
    font-size: 13px;
  }

  .shots {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(min(100%, 320px), 1fr));
    gap: 8px;
  }

  .shot {
    aspect-ratio: 16 / 9;
    padding: 0;
    overflow: hidden;
    border: 0;
    border-radius: 6px;
    background: #0e0e0e;
    cursor: zoom-in;
  }

  .shot img {
    display: block;
    width: 100%;
    height: 100%;
    object-fit: cover;
    transition: transform 0.3s ease;
  }

  .shot:hover img {
    transform: scale(1.03);
  }

  .shot-full {
    display: block;
    width: 100%;
    max-height: calc(100dvh - 140px);
    object-fit: contain;
    border-radius: 6px;
  }

  .versions {
    display: flex;
    gap: 12px;
    overflow-x: auto;
    scrollbar-width: none;
  }

  .versions::-webkit-scrollbar {
    display: none;
  }

  .version-item {
    flex: 0 0 240px;
  }

  .drop-tile {
    aspect-ratio: 16 / 9;
  }

  .source-brief {
    margin: 0;
    color: var(--dc-text);
    font-size: 14px;
    line-height: 1.6;
  }

  .source pre {
    margin: 0;
    color: var(--dc-text-muted);
    font: 13px / 1.65 var(--dc-font-sans);
    white-space: pre-wrap;
    overflow-wrap: anywhere;
  }

  .modal-note {
    margin: 12px 0 0;
    font-size: 12px;
    line-height: 1.5;
  }

  /* ── Tablet and phone ─────────────────────────────────────────── */

  @media (max-width: 1000px) {
    .review {
      grid-template-columns: minmax(0, 1fr);
    }

    .rail {
      flex-direction: row;
      max-height: none;
      overflow-x: auto;
      overflow-y: visible;
    }

    .rail-item {
      width: 176px;
    }
  }

  @media (max-width: 760px) {
    .projects {
      gap: 20px;
      padding-top: 14px;
    }

    .head {
      flex-direction: column;
    }


    .panel {
      padding: 14px;
    }

    .version-item {
      flex-basis: 200px;
    }
  }
</style>
