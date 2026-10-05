<script lang="ts">
  import Badge, { FAMILY_COLORS, EVIDENCE_COLORS, CONFIDENCE_COLORS } from './Badge.svelte';
  import CopyButton from './CopyButton.svelte';
  import type { PromptCardIndex } from '$lib/types/prompt-card';

  let {
    card,
    open = true,
    onclose,
  }: {
    card: PromptCardIndex | null;
    open?: boolean;
    onclose?: () => void;
  } = $props();

</script>

<aside class="dc-drawer" class:open={open}>
  {#if card}
    <div class="dc-drawer-inner">
      <div class="dc-drawer-header">
        <div class="dc-drawer-heading">
          <h2>{card.title}</h2>
          <div class="dc-drawer-actions">
            <a href="/comparisons?prompt={card.slug}" class="dc-drawer-link-badge">Compare →</a>
          </div>
        </div>
        <div class="dc-drawer-toolbar">
          <CopyButton text={card.file_path} label="Path" />
          {#if onclose}
            <button type="button" class="dc-drawer-close" aria-label="Close details" onclick={onclose}>×</button>
          {/if}
        </div>
      </div>

      <p class="dc-drawer-summary">{card.summary}</p>


      <div class="dc-drawer-badges">
        <Badge label={card.model_family} color={FAMILY_COLORS[card.model_family] ?? 'var(--dc-general)'} />
        {#each card.model_targets as target}
          <Badge label={target} color={FAMILY_COLORS[card.model_family] ?? 'var(--dc-general)'} />
        {/each}
        <Badge label={`${card.aspect_ratio}${card.runtime_seconds ? ` ${card.runtime_seconds}s` : ''}`} />
        <Badge label={card.evidence_type} color={EVIDENCE_COLORS[card.evidence_type] ?? 'var(--dc-evidence-unknown)'} />
        <Badge label={card.confidence} color={CONFIDENCE_COLORS[card.confidence] ?? 'var(--dc-text-dim)'} />
        {#if card.tested_by_us}
          <Badge label="tested" color="var(--dc-conf-high)" />
        {/if}
      </div>

      <section class="dc-drawer-section">
        <h3>Prompt Anatomy</h3>
        <dl class="dc-drawer-dl">
          <dt>Mode</dt><dd>{card.prompt_mode}</dd>
          <dt>Shape</dt><dd>{card.output_shape}</dd>
          <dt>Use cases</dt><dd>{card.use_cases.join(', ')}</dd>
          <dt>Tags</dt><dd>{card.tags.join(', ') || '—'}</dd>
          <dt>Status</dt><dd>{card.library_status}</dd>
        </dl>
      </section>

      <section class="dc-drawer-section">
        <h3>Sources ({card.source_count})</h3>
        <ul class="dc-drawer-sources">
          {#each card.source_urls as url}
            <li><a href={url} target="_blank" rel="noopener">{url}</a></li>
          {/each}
        </ul>
        {#if card.source_notes.length > 0}
          <p class="dc-drawer-note">{card.source_notes.join(' · ')}</p>
        {/if}
      </section>

      <section class="dc-drawer-section">
        <h3>Body Excerpt</h3>
        <pre class="dc-drawer-pre">{card.body_excerpt}</pre>
      </section>
    </div>
  {:else}
    <div class="dc-drawer-empty">Select a card to view details</div>
  {/if}
</aside>

<style>
  .dc-drawer {
    width: min(100%, 420px);
    min-width: 280px;
  }

  /* Below the desktop breakpoint this is a full-width bottom sheet
     (positioned by the shared `.dc-drawer` rules in app.css). */
  @media (max-width: 860px) {
    .dc-drawer {
      width: 100%;
      min-width: 0;
    }

    .dc-drawer-inner {
      padding: 4px 16px max(20px, var(--dc-safe-b));
    }

    .dc-drawer-heading h2 { font-size: 19px; }

    .dc-drawer-close,
    .dc-drawer-link-badge {
      min-height: var(--dc-tap);
      font-size: 13px;
    }

    .dc-drawer-close { width: var(--dc-tap); }
  }

  .dc-drawer-inner {
    padding: 16px;
    padding-bottom: max(16px, env(safe-area-inset-bottom));
  }

  .dc-drawer-header {
    display: flex;
    align-items: start;
    justify-content: space-between;
    gap: 12px;
    margin-bottom: 12px;
  }

  .dc-drawer-heading {
    flex: 1;
    min-width: 0;
  }

  .dc-drawer-heading h2 {
    margin: 0;
    font: 400 24px / 1.15 var(--dc-font-serif);
    color: var(--dc-text);
    line-height: 1.25;
  }

  .dc-drawer-actions {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    margin-top: 10px;
  }

  .dc-drawer-link-badge {
    display: inline-flex;
    align-items: center;
    min-height: 28px;
    padding: 0 12px;
    border: 0;
    border-radius: 4px;
    background: rgba(255, 255, 255, 0.1);
    color: var(--dc-text);
    font-size: 13px;
    text-decoration: none;
    cursor: pointer;
  }

  .dc-drawer-link-badge:hover {
    background: rgba(255, 255, 255, 0.18);
  }

  .dc-drawer-toolbar {
    display: flex;
    align-items: center;
    gap: 8px;
    flex-shrink: 0;
  }

  .dc-drawer-close {
    width: 28px;
    height: 28px;
    border: 0;
    border-radius: 50%;
    background: rgba(255, 255, 255, 0.1);
    color: var(--dc-text);
    font-size: 20px;
    line-height: 1;
    cursor: pointer;
  }

  .dc-drawer-summary {
    margin: 0 0 12px;
    color: var(--dc-text-muted);
    font-size: 13px;
    line-height: 1.5;
  }





  .dc-drawer-badges {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    margin-bottom: 16px;
  }

  .dc-drawer-section {
    margin-bottom: 16px;
  }

  .dc-drawer-section h3 {
    margin: 0 0 8px;
    font-size: 13px;
    font-weight: 600;
    color: var(--dc-text);
  }

  .dc-drawer-dl {
    display: grid;
    grid-template-columns: 96px 1fr;
    gap: 6px 10px;
    margin: 0;
    font-size: 12px;
  }

  .dc-drawer-dl dt {
    color: var(--dc-text-muted);
  }

  .dc-drawer-dl dd {
    margin: 0;
  }

  .dc-drawer-sources {
    list-style: none;
    padding: 0;
    margin: 0;
    display: flex;
    flex-direction: column;
    gap: 6px;
  }

  .dc-drawer-sources a {
    color: var(--dc-text-muted);
    font-size: 13px;
    text-decoration: none;
    word-break: break-all;
  }

  .dc-drawer-note {
    margin: 8px 0 0;
    font-size: 11px;
    color: var(--dc-text-dim);
  }

  .dc-drawer-pre {
    margin: 0;
    max-height: 260px;
    overflow-y: auto;
    font-family: var(--dc-font-sans);
    font-size: 13px;
    line-height: 1.6;
    color: #d6d3d1;
    white-space: pre-wrap;
  }

  .dc-drawer-empty {
    display: flex;
    align-items: center;
    justify-content: center;
    min-height: 100%;
    padding: 24px;
    color: var(--dc-text-dim);
    font-size: 12px;
    text-align: center;
  }

</style>
