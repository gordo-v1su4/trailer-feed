<script lang="ts">
  let {
    title,
    fullTitle = title,
    takeLabel,
    status = '',
    videoUrl = '',
    thumbnailUrl = '',
    isNewest = false,
    playOnHover = false,
    selected = false,
    density = 'full',
    rank,
    onselect,
  }: {
    title: string;
    fullTitle?: string;
    takeLabel: string;
    status?: string;
    videoUrl?: string;
    thumbnailUrl?: string;
    isNewest?: boolean;
    playOnHover?: boolean;
    selected?: boolean;
    density?: 'full' | 'thumb';
    rank?: number;
    onselect?: () => void;
  } = $props();

  let video = $state<HTMLVideoElement | null>(null);
  let duration = $state(0);

  const timecode = $derived(
    duration ? `${Math.floor(duration / 60)}:${String(Math.round(duration % 60)).padStart(2, '0')}` : '',
  );

  function keydown(event: KeyboardEvent) {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault();
      onselect?.();
    }
  }
</script>

<div
  class="clip"
  class:is-selected={selected}
  class:thumb={density === 'thumb'}
  role="button"
  tabindex="0"
  title={fullTitle}
  onclick={() => onselect?.()}
  onkeydown={keydown}
  onmouseenter={() => { if (playOnHover && video) void video.play().catch(() => {}); }}
  onmouseleave={() => { if (playOnHover && video && !video.paused) video.pause(); }}
>
  <div class="clip-frame">
    {#if videoUrl}
      <video
        bind:this={video}
        src={videoUrl}
        poster={thumbnailUrl || undefined}
        muted
        playsinline
        loop
        preload="metadata"
        onloadedmetadata={(e) => (duration = e.currentTarget.duration || 0)}
      ></video>
    {:else if thumbnailUrl}
      <img src={thumbnailUrl} alt={title} loading="lazy" />
    {/if}
    <div class="clip-shade" aria-hidden="true"></div>

    {#if density === 'thumb'}
      <div class="clip-top">
        <span class="clip-top-tags">
          <span class="stag">{takeLabel}</span>
          {#if isNewest}<span class="stag tone-warm">Newest take</span>{/if}
        </span>
        {#if timecode}<span class="clip-time">{timecode}</span>{/if}
      </div>
    {:else if rank !== undefined}
      <span class="clip-rank mono" aria-hidden="true">{rank}</span>
    {/if}

    {#if density === 'full'}
      <div class="clip-footer">
        <div class="clip-title-line">
          <span class="t-card clip-title">{title}</span>
          <span class="clip-ver mono">{takeLabel}</span>
          {#if status}<span class="stag tone-review clip-status">{status}</span>{/if}
        </div>
        {#if timecode}<span class="clip-time-bottom mono">{timecode}</span>{/if}
      </div>
    {/if}
  </div>
</div>

<style>
  .clip {
    min-width: 0;
    overflow: hidden;
    border-radius: 8px;
    background: #0e0e0e;
    text-align: left;
    cursor: pointer;
    user-select: none;
    transition: filter 0.15s ease;
  }

  .clip:hover {
    filter: brightness(1.06);
  }

  .clip-frame {
    position: relative;
    aspect-ratio: 16 / 9;
    overflow: hidden;
    background: #161616;
  }

  .clip-frame video,
  .clip-frame img {
    display: block;
    width: 100%;
    height: 100%;
    object-fit: cover;
  }

  .clip.thumb .clip-frame video,
  .clip.thumb .clip-frame img {
    filter: brightness(0.55) saturate(0.8);
    transition: filter 0.2s ease;
  }

  .clip.thumb:hover .clip-frame video,
  .clip.thumb:hover .clip-frame img,
  .clip.thumb.is-selected .clip-frame video,
  .clip.thumb.is-selected .clip-frame img {
    filter: none;
  }

  .clip-shade {
    position: absolute;
    inset: 0;
    pointer-events: none;
    background: linear-gradient(to top, rgba(0, 0, 0, 0.75), transparent 45%, rgba(0, 0, 0, 0.25));
  }

  .clip-rank {
    position: absolute;
    top: 10px;
    left: 10px;
    font-size: 11px;
    color: rgba(255, 255, 255, 0.32);
    letter-spacing: 0.06em;
    pointer-events: none;
  }

  .clip-top {
    position: absolute;
    top: 10px;
    right: 10px;
    left: 10px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
    pointer-events: none;
  }

  .clip-top-tags {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 6px;
    min-width: 0;
  }

  .clip-time {
    display: inline-flex;
    align-items: center;
    height: 20px;
    padding: 0 8px;
    border-radius: 3px;
    background: rgba(0, 0, 0, 0.7);
    color: var(--dc-text-muted);
    font-family: var(--dc-font-mono);
    font-size: 11px;
    font-variant-numeric: tabular-nums;
    letter-spacing: 0.04em;
  }

  .clip-footer {
    position: absolute;
    right: 10px;
    bottom: 10px;
    left: 10px;
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    gap: 4px;
    pointer-events: none;
  }

  .clip-title-line {
    display: flex;
    flex-wrap: wrap;
    align-items: baseline;
    gap: 8px;
    min-width: 0;
    max-width: 100%;
  }

  .clip-title {
    min-width: 0;
    color: #fff;
    opacity: 0.38;
    text-shadow: 0 1px 8px rgba(0, 0, 0, 0.8);
    transition: opacity 0.15s ease;
  }

  .clip:hover .clip-title {
    opacity: 1;
  }

  .clip-ver {
    flex-shrink: 0;
    font-size: 10px;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: rgba(255, 255, 255, 0.35);
    transition: color 0.15s ease;
  }

  .clip:hover .clip-ver {
    color: rgba(255, 255, 255, 0.85);
  }

  .clip-time-bottom {
    font-size: 10px;
    letter-spacing: 0.06em;
    color: rgba(255, 255, 255, 0.32);
    font-variant-numeric: tabular-nums;
    transition: color 0.15s ease;
  }

  .clip:hover .clip-time-bottom {
    color: rgba(255, 255, 255, 0.72);
  }

  .clip-status {
    flex-shrink: 0;
  }
</style>