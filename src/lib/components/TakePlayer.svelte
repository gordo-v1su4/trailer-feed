<script lang="ts" module>
  export type CompareMode = "watch" | "pair" | "blend" | "diff";
</script>

<script lang="ts">
  import LegacyText from '$lib/components/LegacyText.svelte';
  import Icon from './Icon.svelte';
  import { toneFor } from '$lib/ui/tones';
  import { timecode, type Take } from '$lib/ui/studio.svelte';
  import { TakeCompositor } from '$lib/webgpu/take-compositor';


  let {
    primary,
    secondary,
    mode = $bindable('watch'),
    canStep = false,
    onprev,
    onnext,
  }: {
    primary: Take;
    /** The take compared against in Pair, Blend and Diff. */
    secondary?: Take;
    mode?: CompareMode;
    canStep?: boolean;
    onprev?: () => void;
    onnext?: () => void;
  } = $props();

  const gpuCapable = typeof navigator !== 'undefined' && 'gpu' in navigator;
  const modes = $derived<{ id: CompareMode; label: string; hint: string }[]>([
    { id: 'watch', label: 'Watch', hint: 'One take, full frame' },
    { id: 'pair', label: 'Pair', hint: 'Two takes side by side' },
    { id: 'blend', label: 'Blend', hint: 'Wipe between two takes on one frame' },
    ...(gpuCapable ? [{ id: 'diff' as const, label: 'Diff', hint: 'Light up every pixel that changed between the takes' }] : []),
  ]);

  let videoA = $state<HTMLVideoElement | null>(null);
  let videoB = $state<HTMLVideoElement | null>(null);
  let canvas = $state<HTMLCanvasElement | null>(null);
  let compositor = $state<TakeCompositor | null>(null);
  let gpuFailed = $state(false);
  let playing = $state(true);
  let muted = $state(true);
  let split = $state(0.5);
  let duration = $state(0);
  let current = $state(0);
  let swipeX: number | null = null;

  const comparing = $derived(mode !== 'watch' && !!secondary && secondary.id !== primary.id);
  const gpuView = $derived(comparing && (mode === 'blend' || mode === 'diff') && gpuCapable && !gpuFailed);
  /** WebGPU samples frames; everything else plays the catalog URL as-is (Review Room URLs break with ?cors=1). */
  const needCorsFrames = $derived(gpuView);

  function playUrl(url: string | undefined) {
    if (!url) return url;
    if (!needCorsFrames) return url;
    return `${url}${url.includes('?') ? '&' : '?'}cors=1`;
  }

  function togglePlay() {
    playing = !playing;
  }

  $effect(() => {
    void primary.id;
    playing = true;
  });

  // Keep both takes playing, pausing and positioned together.
  $effect(() => {
    const a = videoA;
    const b = comparing ? videoB : null;
    if (!a) return;
    if (playing) {
      void a.play().catch(() => (playing = false));
      if (b) void b.play().catch(() => {});
    } else {
      a.pause();
      b?.pause();
    }
  });

  function syncB() {
    if (!videoA || !videoB || !comparing) return;
    if (Math.abs(videoB.currentTime - videoA.currentTime) > 0.2) videoB.currentTime = videoA.currentTime;
  }

  function onTime() {
    if (!videoA) return;
    current = videoA.currentTime;
    syncB();
  }

  function onLoaded(video: HTMLVideoElement) {
    if (video === videoA) duration = video.duration || 0;
    if (playing) void video.play().catch(() => {});
  }

  function seek(event: PointerEvent) {
    const bar = event.currentTarget as HTMLElement;
    const move = (e: PointerEvent) => {
      const rect = bar.getBoundingClientRect();
      const t = Math.min(1, Math.max(0, (e.clientX - rect.left) / rect.width));
      if (videoA && duration) {
        videoA.currentTime = t * duration;
        current = videoA.currentTime;
        syncB();
      }
    };
    move(event);
    bar.setPointerCapture(event.pointerId);
    bar.onpointermove = move;
    bar.onpointerup = () => (bar.onpointermove = null);
  }

  function dragSplit(event: PointerEvent) {
    const track = event.currentTarget as HTMLElement;
    const move = (e: PointerEvent) => {
      const rect = track.getBoundingClientRect();
      split = Math.min(1, Math.max(0, (e.clientX - rect.left) / rect.width));
    };
    move(event);
    track.setPointerCapture(event.pointerId);
    track.onpointermove = move;
    track.onpointerup = () => (track.onpointermove = null);
  }

  function splitKeys(event: KeyboardEvent) {
    if (event.key === 'ArrowLeft') split = Math.max(0, split - 0.04);
    if (event.key === 'ArrowRight') split = Math.min(1, split + 0.04);
  }

  // Bring the GPU up when a blend view opens, and let it go when it closes.
  $effect(() => {
    const target = canvas;
    if (!target) return;
    let disposed = false;
    let made: TakeCompositor | null = null;
    void TakeCompositor.create(target).then((instance) => {
      if (disposed) return instance?.destroy();
      if (!instance) gpuFailed = true;
      made = compositor = instance;
    });
    return () => {
      disposed = true;
      made?.destroy();
      compositor = null;
    };
  });

  // Draw every frame while the blend view is open.
  $effect(() => {
    const gpu = compositor;
    const target = canvas;
    const a = videoA;
    const b = videoB;
    const blendMode = mode === 'diff' ? 'diff' : 'wipe';
    if (!gpu || !target || !a || !b || !gpuView) return;
    let frame = 0;
    const tick = () => {
      try {
        gpu.draw(target, a, b, split, blendMode);
      } catch {
        gpuFailed = true;
        return;
      }
      frame = requestAnimationFrame(tick);
    };
    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
  });
</script>

<div class="player">
  <!-- svelte-ignore a11y_no_static_element_interactions -->
  <div
    class="stage mode-{comparing ? mode : 'watch'}"
    class:gpu={gpuView}
    onpointerdown={(e) => { if (!comparing && canStep) swipeX = e.clientX; }}
    onpointerup={(e) => {
      if (swipeX === null) return;
      const delta = e.clientX - swipeX;
      swipeX = null;
      if (delta > 56) onprev?.();
      else if (delta < -56) onnext?.();
    }}
  >
    <video
      bind:this={videoA}
      class="take take-a"
      src={playUrl(primary.artifact.media_url)}
      poster={comparing ? playUrl(primary.artifact.thumbnail_url) : undefined}
      crossorigin={needCorsFrames ? 'anonymous' : undefined}
      {muted}
      autoplay
      playsinline
      loop
      preload="auto"
      aria-label={`Take ${primary.code}`}
      ontimeupdate={onTime}
      onloadeddata={(e) => onLoaded(e.currentTarget)}
      onloadedmetadata={(e) => (duration = e.currentTarget.duration || 0)}
      onended={() => (playing = false)}
    ></video>

    {#if comparing && secondary}
      <video
        bind:this={videoB}
        class="take take-b"
        src={playUrl(secondary.artifact.media_url)}
        poster={playUrl(secondary.artifact.thumbnail_url)}
        crossorigin={needCorsFrames ? 'anonymous' : undefined}
        muted
        playsinline
        loop
        preload="auto"
        aria-label={`Take ${secondary.code}`}
        style:clip-path={mode === 'blend' && !gpuView ? `inset(0 0 0 ${split * 100}%)` : undefined}
        onloadeddata={(e) => { syncB(); onLoaded(e.currentTarget); }}
      ></video>
    {/if}

    {#if gpuView}
      <canvas bind:this={canvas} class="gpu-canvas" aria-label={mode === 'diff' ? 'Difference between the two takes' : 'Wipe between the two takes'}></canvas>
    {/if}

    {#if comparing && mode === 'blend'}
      <div
        class="split"
        role="slider"
        tabindex="0"
        aria-label="Wipe position"
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={Math.round(split * 100)}
        onpointerdown={dragSplit}
        onkeydown={splitKeys}
      >
        <span class="split-line" style:left="{split * 100}%"></span>
        <span class="split-handle" style:left="{split * 100}%"></span>
      </div>
    {/if}

    <div class="overlay-top">
      <div class="tags">
        <span class="stag">{primary.code}</span>
        {#if primary.writer}<span class="stag tone-{toneFor(primary.writer)}">{primary.writer}</span>{/if}
        {#if primary.model}<span class="stag tone-{toneFor(primary.model)}"><LegacyText text={primary.model} /></span>{/if}
        {#if comparing && secondary}
          <span class="versus dim">vs</span>
          <span class="stag tone-warm">{secondary.code}</span>
          {#if secondary.model}<span class="stag tone-{toneFor(secondary.model)} hide-sm"><LegacyText text={secondary.model} /></span>{/if}
        {/if}
      </div>
      {#if duration}<span class="time">{timecode(current)} / {timecode(duration)}</span>{/if}
    </div>

    <div class="scrub" role="presentation" onpointerdown={seek}>
      <span class="scrub-fill" style:width="{duration ? (current / duration) * 100 : 0}%"></span>
    </div>
  </div>
  <div class="overlay-bottom">
    <div class="modes" role="group" aria-label="Compare mode">
      {#each modes as option (option.id)}
        <button
          type="button"
          class="sbtn glassy"
          class:sbtn-primary={mode === option.id}
          aria-pressed={mode === option.id}
          title={option.hint}
          disabled={option.id !== 'watch' && !secondary}
          onclick={() => (mode = option.id)}
        >
          {option.label}
        </button>
      {/each}
    </div>
    <div class="transport">
      {#if canStep}
        <button type="button" class="sbtn sbtn-icon glassy" onclick={onprev} aria-label="Previous take"><Icon name="left" size={16} /></button>
      {/if}
      <button type="button" class="sbtn sbtn-primary" onclick={togglePlay}>
        <Icon name={playing ? 'pause' : 'play'} size={12} filled />
        <span>{playing ? 'Pause' : 'Play'}</span>
      </button>
      {#if canStep}
        <button type="button" class="sbtn sbtn-icon glassy" onclick={onnext} aria-label="Next take"><Icon name="right" size={16} /></button>
      {/if}
      <button type="button" class="sbtn sbtn-icon glassy" onclick={() => (muted = !muted)} aria-label={muted ? 'Turn sound on' : 'Turn sound off'} aria-pressed={!muted}>
        <Icon name={muted ? 'mute' : 'volume'} />
      </button>
    </div>
  </div>

</div>

<style>
  .player {
    position: relative;
    min-width: 0;
  }

  .stage {
    position: relative;
    aspect-ratio: 16 / 9;
    min-height: 200px;
    overflow: hidden;
    border-radius: 8px;
    background: #000;
    touch-action: pan-y;
    user-select: none;
  }

  .take,
  .gpu-canvas {
    position: absolute;
    inset: 0;
    width: 100%;
    height: 100%;
    object-fit: cover;
  }

  /* Pair: two whole frames side by side, letterboxed on black. */
  .mode-pair .take {
    width: 50%;
    object-fit: contain;
  }

  .mode-pair .take-b {
    left: 50%;
  }

  /* GPU view: the videos keep decoding underneath the canvas. */
  .stage.gpu .take {
    opacity: 0;
  }

  .split {
    position: absolute;
    z-index: 2;
    inset: 0;
    cursor: ew-resize;
    touch-action: none;
  }

  .split:focus-visible {
    outline: none;
  }

  .split-line {
    position: absolute;
    top: 0;
    bottom: 0;
    width: 1px;
    background: rgba(255, 255, 255, 0.4);
  }

  .split-handle {
    position: absolute;
    top: 50%;
    width: 5px;
    height: 72px;
    border-radius: 2px;
    background: rgba(255, 255, 255, 0.75);
    transform: translate(-50%, -50%);
  }

  .split:focus-visible .split-handle {
    box-shadow: 0 0 0 4px rgba(255, 255, 255, 0.2);
  }

  .overlay-top,
  .overlay-bottom {
    position: absolute;
    z-index: 3;
    right: 12px;
    left: 12px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
  }

  .overlay-top {
    top: 12px;
    pointer-events: none;
  }

  .overlay-bottom {
    bottom: 16px;
    flex-wrap: wrap;
  }

  .tags,
  .modes,
  .transport {
    display: flex;
    min-width: 0;
    align-items: center;
    gap: 6px;
  }

  .versus {
    font-size: 12px;
  }

  .time {
    flex-shrink: 0;
    height: 20px;
    padding: 0 8px;
    border-radius: 3px;
    background: rgba(0, 0, 0, 0.7);
    color: var(--dc-text-muted);
    font-size: 12px;
    line-height: 20px;
    font-variant-numeric: tabular-nums;
  }

  .glassy:not(.sbtn-primary) {
    background: rgba(22, 22, 22, 0.62);
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
  }

  .glassy:not(.sbtn-primary):hover:not(:disabled) {
    background: rgba(40, 40, 40, 0.75);
  }

  .scrub {
    position: absolute;
    z-index: 4;
    right: 0;
    bottom: 0;
    left: 0;
    height: 10px;
    cursor: pointer;
    touch-action: none;
  }

  .scrub::before,
  .scrub-fill {
    position: absolute;
    bottom: 0;
    left: 0;
    height: 3px;
  }

  .scrub::before {
    content: '';
    right: 0;
    background: rgba(255, 255, 255, 0.14);
  }

  .scrub-fill {
    background: rgba(255, 255, 255, 0.7);
  }

  .scrub:hover::before,
  .scrub:hover .scrub-fill {
    height: 5px;
  }

  /* Phones: the controls sit under the picture instead of over it. */
  @media (max-width: 640px) {
    .overlay-bottom {
      position: static;
      margin-top: 8px;
    }

    .glassy:not(.sbtn-primary) {
      background: #161616;
    }

    .modes .sbtn {
      padding: 0 8px;
    }

    .hide-sm {
      display: none;
    }
  }
</style>
