<script lang="ts">
  import { isLegacySora } from '$lib/create/models';
  import LegacyText from '$lib/components/LegacyText.svelte';
  import type { ComparisonArtifact, GenerationPrompt } from '$lib/types/comparison';
  import { mediaApi, ownerToken } from '$lib/data/media-api';
  import { versionPrompt, videoModel } from '$lib/data/version-context';
  import CopyButton from './CopyButton.svelte';
  import Select from './Select.svelte';
  let { artifact, editable = true, showHeading = true, grids = [], promptsMap = new Map(), onSaved }: {
    artifact: ComparisonArtifact; editable?: boolean; showHeading?: boolean; grids?: ComparisonArtifact[];
    promptsMap?: Map<string, GenerationPrompt>; onSaved?: () => void | Promise<void>;
  } = $props();
  let editing = $state(false);
  let prompt = $state('');
  let model = $state('');
  let gridChoice = $state('keep');
  let file = $state<File | null>(null);
  let busy = $state(false);
  let message = $state('');
  let password = $state('');
  let login = $state(false);
  let picker = $state<HTMLInputElement>();
  const savedPrompt = $derived(versionPrompt(artifact, promptsMap));
  function openDialog(node: HTMLDialogElement) { node.showModal(); }
  /** Opens the editor; a parent that draws its own heading row calls this. */
  export function edit() {
    prompt = savedPrompt;
    model = videoModel(artifact) === 'Model not set' ? '' : videoModel(artifact);
    gridChoice = 'keep'; file = null; message = ''; editing = true;
    login = !ownerToken();
  }
  function choose(files: File[]) {
    const chosen = files[0];
    if (!chosen) return;
    if (files.length !== 1 || !/\.(png|jpe?g|webp)$/i.test(chosen.name) || chosen.size > 10_000_000) {
      message = 'Choose one PNG, JPEG or WebP image, up to 10 MB.'; return;
    }
    file = chosen; gridChoice = 'upload'; message = '';
  }
  async function save(event: SubmitEvent) {
    event.preventDefault(); busy = true; message = '';
    try {
      if (login) {
        const response = await fetch(`${mediaApi}/login`, {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:'gordo',password})});
        const result = await response.json();
        if (!response.ok) throw new Error(result.error || 'Sign in failed');
        sessionStorage.setItem('trailer-feed-owner',result.token); password=''; login=false;
      }
      const payload: Record<string, unknown> = {run_id:artifact.run_id, prompt, video_model:model, revision:artifact.context_revision ?? 0};
      if (gridChoice === 'remove') payload.grid = null;
      else if (gridChoice === 'upload' && file) {
        const data = await new Promise<string>((resolve,reject)=>{
          const reader = new FileReader(); reader.onload=()=>resolve(String(reader.result).split(',')[1]); reader.onerror=()=>reject(new Error('Could not read image')); reader.readAsDataURL(file!);
        });
        payload.grid = {data};
      } else if (gridChoice !== 'keep') payload.grid = {artifact_id:gridChoice};
      const response = await fetch(`${mediaApi}/versions/${encodeURIComponent(artifact.artifact_id)}/details`, {method:'POST',headers:{'Content-Type':'application/json',Authorization:`Bearer ${ownerToken()}`},body:JSON.stringify(payload)});
      const result = await response.json();
      if (response.status === 401) { sessionStorage.removeItem('trailer-feed-owner'); login=true; }
      if (!response.ok) throw new Error(result.error || 'Save failed');
      await onSaved?.(); editing=false; message='Version details saved.';
    } catch(error) { message=error instanceof Error ? error.message : 'Save failed'; }
    finally { busy=false; }
  }
</script>

<section class="version-details" aria-label="Version details">
  {#if showHeading}<div class="heading"><span class="model"><LegacyText text={videoModel(artifact)} /></span>{#if mediaApi && editable}<button class="edit" onclick={edit}>Edit version details</button>{/if}</div>{/if}
  {#if editing}
    <dialog use:openDialog class="editor-dialog" aria-label="Edit version details" oncancel={(e)=>{e.preventDefault();if(!busy)editing=false;}}><form onsubmit={save}>
      <h3>Edit version details</h3>
      <label>Video model<input bind:value={model} list="video-models" placeholder="e.g. Seedance 2.5" maxlength="100" disabled={busy} /></label>
      <datalist id="video-models"><option>Seedance 2.0</option><option>Seedance 2.5</option><option>Mini Max H3</option><option>Veo 3.1</option><option>Kling</option><option>Other / edited</option></datalist>
      <label>Prompt for this version<textarea bind:value={prompt} rows="9" maxlength="100000" placeholder="Paste the exact prompt used for this video…" disabled={busy}></textarea></label>
      <div class="field">Shot grid
        <Select
          label="Shot grid"
          bind:value={gridChoice}
          options={[
            { value: 'keep', label: artifact.shot_grid_url ? 'Keep attached grid' : 'No grid attached' },
            ...grids.map((grid) => ({ value: grid.artifact_id, label: grid.title })),
            ...(file ? [{ value: 'upload', label: file.name }] : []),
            ...(artifact.shot_grid_url ? [{ value: 'remove', label: 'Remove attachment' }] : []),
          ]}
        />
      </div>
      <input bind:this={picker} hidden type="file" accept="image/png,image/jpeg,image/webp" aria-label="Choose shot grid" onchange={(e)=>choose(Array.from(e.currentTarget.files || []))} />
      <button type="button" class="drop" disabled={busy} onclick={()=>picker?.click()} ondragover={(e)=>e.preventDefault()} ondrop={(e)=>{e.preventDefault();if(!busy)choose(Array.from(e.dataTransfer?.files || []));}}>{file ? file.name : 'Drop shot grid here or choose image'}<small>PNG, JPEG or WebP · up to 10 MB</small></button>
      {#if login}<label>Owner password<input type="password" bind:value={password} autocomplete="current-password" required disabled={busy} /></label>{/if}
      <div class="actions"><button type="submit" disabled={busy}>{busy ? 'Saving…' : 'Save version details'}</button><button type="button" disabled={busy} onclick={()=>{editing=false;message='';}}>Cancel</button></div>
      <p class="save-status" role="status">{message || (busy ? 'Saving…' : 'Changes apply to this video version.')}</p>
    </form></dialog>
  {/if}
    {#if isLegacySora(videoModel(artifact))}<p class="legacy-note"><LegacyText text={videoModel(artifact)} /> is unavailable. This take and its original prompt remain available as legacy material.</p>{/if}
    <div class="context-grid">
      <div><div class="heading"><h3>Prompt</h3>{#if savedPrompt}<CopyButton text={savedPrompt} label="Copy" />{/if}</div>
        {#if savedPrompt}<p class="prompt"><LegacyText text={savedPrompt} /></p>{:else}<p class="empty">No prompt saved for this version.</p>{/if}
      </div>
      <div><div class="heading"><h3>Shot grid</h3></div>{#if artifact.shot_grid_url}<a href={artifact.shot_grid_url} target="_blank" rel="noreferrer" aria-label="Open shot grid"><img src={artifact.shot_grid_url} alt="Shot grid for this video version" /></a>{:else}<div class="empty-grid">No shot grid attached to this version.</div>{/if}</div>
    </div>
  <p class="save-status" role="status">{!editing ? message : ''}</p>
</section>

<style>
  .legacy-note { color:var(--dc-text-muted); font-size:12px; margin:0 0 12px; }
  .version-details {min-width:0; color:var(--dc-text);}
  /* Every header row here is 28px tall with 12px below, so rows line up across columns. */
  .heading {height:28px;display:flex;align-items:center;justify-content:space-between;gap:12px;margin-bottom:12px;}
  .actions {min-height:28px;display:flex;align-items:center;gap:12px;flex-wrap:wrap;margin-bottom:12px;}
  .model {font-size:14px;font-weight:600;}
  h3 {margin:0 0 12px;font-size:14px;font-weight:600;color:var(--dc-text);}
  .edit {height:28px;min-height:0;}
  .heading h3 {margin:0;}
  .context-grid {display:grid;grid-template-columns:1fr 1fr;gap:24px;}
  .context-grid > div {min-width:0;}
  .prompt {box-sizing:border-box;white-space:pre-wrap;overflow-wrap:anywhere;margin:0;height:330px;overflow:auto;padding:0 14px 0 0;border:0;border-radius:0;background:transparent;color:#d6d3d1;font:14px/1.65 var(--dc-font-sans);scrollbar-width:thin;scrollbar-color:#3f3f46 transparent;}
  img {width:100%;aspect-ratio:16/9;object-fit:contain;object-position:top;background:var(--dc-bg);display:block;}
  .empty {height:330px;margin:0;}
  .save-status {min-height:20px;margin:8px 0 0;font-size:12px;color:var(--dc-text-muted);}
  .editor-dialog {margin:auto;inset:0;box-sizing:border-box;max-width:calc(100vw - 24px);width:min(680px,calc(100vw - 40px));padding:0;border:0;border-radius:10px;background:transparent;color:var(--dc-text);max-height:calc(100dvh - 40px);}
  .editor-dialog::backdrop {background:rgba(0,0,0,.45);backdrop-filter:blur(6px);}
  .editor-dialog form {width:100%;max-height:calc(100dvh - 40px);overflow:auto;box-sizing:border-box;background:rgba(20,20,20,.78);backdrop-filter:blur(28px);-webkit-backdrop-filter:blur(28px);border:0;border-radius:10px;padding:24px;}
  .empty,.empty-grid {font-size:12px;line-height:1.6;color:var(--dc-text-muted);}
  .empty-grid {aspect-ratio:16/9;border:0;background:#0e0e0e;border-radius:6px;display:grid;place-items:center;text-align:center;padding:12px;box-sizing:border-box;}
  form {display:flex;flex-direction:column;gap:14px;}
  label, .field {font-size:12px;display:flex;flex-direction:column;gap:6px;}
  .field :global(.dc-select) {display:block;}
  input,textarea {box-sizing:border-box;width:100%;padding:10px;background:rgba(0,0,0,.35);color:var(--dc-text);border:0;border-radius:4px;font:inherit;}
  textarea {resize:vertical;line-height:1.6;}
  button {min-height:28px;padding:0 12px;background:rgba(255,255,255,.1);color:var(--dc-text);border:0;border-radius:4px;cursor:pointer;font-size:13px;font-weight:550;}
  button:hover:not(:disabled) {background:rgba(255,255,255,.18);}
  button[type=submit] {background:rgba(255,255,255,.7);color:#000;}
  .editor-dialog h3 {font:400 32px/1 var(--dc-font-serif);margin:0 0 4px;}
  button:disabled {opacity:.5;cursor:wait;}
  .drop {padding:22px;border-style:dashed;}
  small {display:block;margin-top:6px;color:var(--dc-text-muted);}
  .actions {justify-content:flex-start;margin:0;}
  @media(max-width:700px){.context-grid {grid-template-columns:1fr;} input,textarea {font-size:16px;} button {min-height:32px;} .heading {height:auto;min-height:32px;} .edit {height:32px;} .editor-dialog form {padding:16px;} .editor-dialog {width:calc(100vw - 24px);} .actions button {flex:1;} }
</style>
