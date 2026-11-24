<script lang="ts">
  import ArtifactPreview from './ArtifactPreview.svelte';
  import { uploadProjectThumbnail, removeProjectThumbnail } from '$lib/data/project-thumbnail';
  import { signInOwner, SignInRequired } from '$lib/data/titles';
  import { featuredCoverArtifact, type Project } from '$lib/ui/studio.svelte';

  let { project, onSaved }: { project: Project; onSaved: () => void | Promise<void> } = $props();
  let file = $state<File | null>(null);
  let previewUrl = $state<string | null>(null);
  let busy = $state(false);
  let error = $state('');
  let message = $state('');
  let needSignIn = $state(false);
  let password = $state('');
  let pending = $state<'upload' | 'reset'>('upload');
  let picker: HTMLInputElement;

  const fallback = $derived(featuredCoverArtifact(project));

  $effect(() => {
    if (!file) { previewUrl = null; return; }
    const url = URL.createObjectURL(file);
    previewUrl = url;
    return () => URL.revokeObjectURL(url);
  });

  function selectFile(event: Event) {
    const selected = (event.currentTarget as HTMLInputElement).files?.[0] ?? null;
    error = '';
    message = '';
    if (selected && (!['image/png', 'image/jpeg', 'image/webp'].includes(selected.type) || selected.size > 5_000_000 || !selected.size)) {
      file = null;
      error = 'Choose a PNG, JPEG or WebP image up to 5 MB.';
      return;
    }
    file = selected;
  }

  async function change(action: 'upload' | 'reset') {
    if (busy || (action === 'upload' && !file)) return;
    pending = action;
    busy = true;
    error = '';
    message = '';
    try {
      if (needSignIn) {
        await signInOwner(password);
        password = '';
        needSignIn = false;
      }
      if (action === 'upload') await uploadProjectThumbnail(project.runId, file!);
      else await removeProjectThumbnail(project.runId);
      file = null;
      if (picker) picker.value = '';
      await onSaved();
      message = action === 'upload' ? 'Project thumbnail updated.' : 'Automatic thumbnail restored.';
    } catch (cause) {
      if (cause instanceof SignInRequired) needSignIn = true;
      error = cause instanceof Error ? cause.message : 'Thumbnail change failed.';
    } finally {
      busy = false;
    }
  }
</script>

<div class="panel glass-panel thumbnail-panel">
  <div>
    <h2 class="t-body">Project thumbnail</h2>
    <p class="muted intro">This image appears on the project card above. Take previews keep their own images.</p>
  </div>
  <div class="thumbnail-layout">
    <div class="thumbnail-preview" aria-label="Project thumbnail preview">
      {#if previewUrl}<img src={previewUrl} alt="Selected project thumbnail preview" />
      {:else if project.projectThumbnailUrl}<img src={project.projectThumbnailUrl} alt="Current project thumbnail" />
      {:else if fallback}<ArtifactPreview artifact={fallback} />
      {:else}<span class="muted">No image yet</span>{/if}
      <span class="preview-title">{project.title}</span>
    </div>
    <div class="thumbnail-controls">
      <label class="t-label" for="project-thumbnail-file">Upload a thumbnail</label>
      <input bind:this={picker} id="project-thumbnail-file" class="sinput" type="file" accept="image/png,image/jpeg,image/webp,.png,.jpg,.jpeg,.webp" onchange={selectFile} disabled={busy} />
      <p class="muted hint">PNG, JPEG or WebP · up to 5 MB · 16:9 works best.</p>
      {#if file}<p class="filename">Selected: {file.name}</p>{/if}
      {#if needSignIn}
        <form class="signin" onsubmit={(event) => { event.preventDefault(); void change(pending); }}>
          <input class="sinput" type="password" bind:value={password} autocomplete="current-password" placeholder="Owner password" aria-label="Owner password" required disabled={busy} />
          <button class="sbtn sbtn-primary" type="submit" disabled={busy || !password}>{busy ? 'Saving…' : 'Sign in and save'}</button>
        </form>
      {:else}
        <div class="actions">
          <button class="sbtn sbtn-primary" type="button" onclick={() => void change('upload')} disabled={busy || !file}>{busy ? 'Saving…' : 'Upload thumbnail'}</button>
          {#if project.projectThumbnailUrl}<button class="sbtn" type="button" onclick={() => void change('reset')} disabled={busy}>Use automatic thumbnail</button>{/if}
        </div>
      {/if}
      {#if error}<p class="error" role="alert">{error}</p>{/if}
      {#if message}<p class="muted" role="status">{message}</p>{/if}
    </div>
  </div>
</div>

<style>
  .thumbnail-panel { display: grid; gap: 18px; padding: 18px; }
  .thumbnail-panel h2, .intro { margin: 0; }
  .intro { margin-top: 6px; font-size: 13px; line-height: 1.5; }
  .thumbnail-layout { display: grid; grid-template-columns: minmax(220px, 360px) minmax(220px, 1fr); align-items: start; gap: 22px; }
  .thumbnail-preview { position: relative; aspect-ratio: 16 / 9; overflow: hidden; display: grid; place-items: center; border-radius: 8px; background: #0e0e0e; }
  .thumbnail-preview :global(img), .thumbnail-preview :global(video) { position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover; }
  .thumbnail-preview::after { content: ''; position: absolute; inset: 0; background: linear-gradient(to top, rgba(0,0,0,.82), transparent 65%); pointer-events: none; }
  .preview-title { position: absolute; z-index: 1; left: 12px; bottom: 10px; font: 18px var(--dc-font-serif); }
  .thumbnail-controls { display: grid; justify-items: start; gap: 10px; min-width: 0; }
  .thumbnail-controls input[type='file'] { max-width: 100%; }
  .hint, .filename, .error { margin: 0; font-size: 12px; }
  .filename { overflow-wrap: anywhere; }
  .actions, .signin { display: flex; flex-wrap: wrap; gap: 8px; }
  .signin .sinput { width: min(100%, 260px); }
  .error { color: var(--dc-error, #ef9a9a); }
  @media (max-width: 700px) { .thumbnail-layout { grid-template-columns: minmax(0, 1fr); } .thumbnail-panel { padding: 14px; } }
</style>
