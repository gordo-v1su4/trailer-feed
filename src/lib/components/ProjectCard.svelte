<script lang="ts">
  import LegacyText from '$lib/components/LegacyText.svelte';
  import ArtifactPreview from './ArtifactPreview.svelte';
  import { toneFor } from '$lib/ui/tones';
  import { plural } from '$lib/ui/studio.svelte';
  import type { ComparisonArtifact } from '$lib/types/comparison';

  let {
    title,
    fullTitle = title,
    cover,
    thumbnailUrl,
    status = '',
    takeCount = 0,
    selected = false,
    compact = false,
    href,
    onselect,
  }: {
    title: string;
    fullTitle?: string;
    cover?: ComparisonArtifact;
    /** Optional project-only cover override, supplied by the Projects strip. */
    thumbnailUrl?: string;
    status?: string;
    takeCount?: number;
    selected?: boolean;
    /** Strip size for the Projects page: title only, no tags. */
    compact?: boolean;
    href?: string;
    onselect?: () => void;
  } = $props();
  let failedThumbnail = $state<string | undefined>();
</script>

<svelte:element
  this={href ? 'a' : 'button'}
  {href}
  type={href ? undefined : 'button'}
  class="poster"
  class:compact
  class:selected
  aria-current={selected ? 'true' : undefined}
  title={fullTitle}
  onclick={onselect}
  role={href ? undefined : 'button'}
>
  <span class="poster-media">{#if thumbnailUrl && failedThumbnail !== thumbnailUrl}<img src={thumbnailUrl} alt="" onerror={() => failedThumbnail = thumbnailUrl} />{:else if cover}<ArtifactPreview artifact={cover} />{/if}</span>
  <span class="poster-shade" aria-hidden="true"></span>
  {#if !compact && status}
    <span class="poster-status stag tone-{toneFor(status)}">{status}</span>
  {/if}
  <span class="poster-copy">
    <span class="t-card"><LegacyText text={title} /></span>
    {#if !compact}<span class="poster-meta">{plural(takeCount, 'take')}</span>{/if}
  </span>
</svelte:element>

<style>
  .poster {
    position: relative;
    display: block;
    box-sizing: border-box;
    width: 100%;
    min-width: 0;
    aspect-ratio: 16 / 9;
    padding: 0;
    overflow: hidden;
    border: 0;
    border-radius: 8px;
    background: #0e0e0e;
    color: var(--dc-text);
    text-align: left;
    text-decoration: none;
    cursor: pointer;
  }

  .poster-media {
    position: absolute;
    inset: 0;
    filter: brightness(0.6) saturate(0.85);
    transition: filter 0.2s ease, transform 0.4s ease;
  }

  .poster-media :global(img),
  .poster-media :global(video) {
    object-fit: cover;
  }

  .poster:hover .poster-media,
  .poster.selected .poster-media {
    filter: none;
  }

  .poster:hover .poster-media {
    transform: scale(1.04);
  }

  /* Selected reads as the one card fully lit, never a line. */
  .poster.selected .poster-shade {
    background: linear-gradient(to top, rgba(0, 0, 0, 0.7) 0%, rgba(0, 0, 0, 0) 50%);
  }

  .poster-shade {
    position: absolute;
    inset: 0;
    background: linear-gradient(to top, rgba(0, 0, 0, 0.88) 0%, rgba(0, 0, 0, 0) 62%);
  }

  .poster-status {
    position: absolute;
    top: 10px;
    left: 10px;
  }

  .poster-copy {
    position: absolute;
    right: 12px;
    bottom: 10px;
    left: 12px;
    display: flex;
    flex-direction: column;
    gap: 2px;
    min-width: 0;
  }

  .poster-copy :global(.t-card) {
    opacity: 0.65;
  }

  .poster-meta {
    color: var(--dc-text-muted);
    font-size: 12px;
  }

  .compact .poster-copy {
    right: 8px;
    bottom: 6px;
    left: 8px;
  }

  .compact .t-card {
    font-size: 15px;
  }

  .poster:focus-visible {
    outline: none;
    box-shadow: 0 0 0 3px rgba(231, 229, 228, 0.3);
  }

  @media (prefers-reduced-motion: reduce) {
    .poster-media {
      transition: none;
    }
  }
</style>
