<script lang="ts">
  import type { ComparisonArtifact } from '$lib/types/comparison';
  import { ownerToken } from '$lib/data/media-api';
  import { signInOwner, SignInRequired } from '$lib/data/titles';
  import { removeExternalVersion } from '$lib/data/external-version';
  import GlassModal from './GlassModal.svelte';

  let { artifact, code, onRemoved }: { artifact:ComparisonArtifact; code:string; onRemoved:(runId:string) => Promise<void> } = $props();
  let target = $state.raw<{runId:string;artifactId:string;generation:number;code:string;title:string}|null>(null);
  let busy = $state(false);
  let error = $state('');
  let password = $state('');
  let needsSignIn = $state(false);
  const external = $derived(artifact.ownership === 'external' && artifact.source_app === 'review-room');

  function requestRemoval() {
    if (!external || busy) return;
    target = {runId:artifact.run_id,artifactId:artifact.artifact_id,generation:artifact.consent_generation ?? 1,code,title:artifact.title};
    error = ''; password = ''; needsSignIn = !ownerToken();
  }
  function close() { if (busy) return; target = null; password = ''; error = ''; }
  async function confirm(event:SubmitEvent) {
    event.preventDefault();
    if (!target || busy) return;
    const captured = target;
    busy = true; error = '';
    try {
      if (needsSignIn) { await signInOwner(password); password = ''; needsSignIn = false; }
      await removeExternalVersion(captured);
      await onRemoved(captured.runId);
      target = null;
    } catch (cause) {
      if (cause instanceof SignInRequired) needsSignIn = true;
      error = cause instanceof Error ? cause.message : 'Version removal failed.';
    } finally { busy = false; }
  }
</script>

{#if external}<button type="button" class="remove-version sbtn" onclick={requestRemoval}>Remove {code}</button>{/if}
{#if target}
  <GlassModal title={`Remove ${target.code} from Trailer Feed?`} onclose={close} width={520}>
    <form onsubmit={confirm}>
      <p><strong>{target.title} · {target.code}</strong></p>
      <p>This removes only this video version and its attached images from Trailer Feed. The original video and images remain in Review Room.</p>
      <p>Retries will keep this version removed. Restoring it requires explicit Sync again consent for this exact version in Review Room.</p>
      {#if needsSignIn}<label>Owner password<input type="password" bind:value={password} autocomplete="current-password" required disabled={busy}/></label>{/if}
      {#if error}<p class="error" role="alert">{error}</p>{/if}
      <div class="actions"><button type="button" class="sbtn" disabled={busy} onclick={close}>Cancel</button><button type="submit" class="sbtn remove-confirm" disabled={busy || (needsSignIn && !password)}>{busy ? 'Removing…' : `Remove ${target.code}`}</button></div>
      {#if busy}<p role="status">Removing this exact version…</p>{/if}
    </form>
  </GlassModal>
{/if}

<style>
  .remove-version{color:var(--dc-text-muted)}
  form{display:grid;gap:14px;padding:20px}p{margin:0;font-size:13px;line-height:1.6;color:var(--dc-text-muted)}strong{color:var(--dc-text)}label{display:grid;gap:8px;font-size:13px}input{padding:10px;border:1px solid var(--dc-border);border-radius:6px;background:var(--dc-bg);color:var(--dc-text);font:inherit}.actions{display:flex;justify-content:flex-end;gap:10px;margin-top:10px}.remove-confirm{color:#f0afa8}.error{color:#f0afa8}
</style>
