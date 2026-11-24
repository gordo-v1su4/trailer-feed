<script lang="ts">
  import LegacyText from '$lib/components/LegacyText.svelte';
  import { fade } from 'svelte/transition';
  import { goto } from '$app/navigation';
  import MediaLightbox from '$lib/components/MediaLightbox.svelte';
  import ClipCard from '$lib/components/ClipCard.svelte';
  import ProjectCard from '$lib/components/ProjectCard.svelte';
  import Icon from '$lib/components/Icon.svelte';
  import { featuredCoverArtifact, featuredTake, plural, portfolioStatusVisible, studio, type Take } from '$lib/ui/studio.svelte';
  import { showTitle } from '$lib/data/titles';
  import type { ComparisonArtifact } from '$lib/types/comparison';

  let heroIndex = $state(0);
  let heroPlaying = $state(true);
  let heroMuted = $state(true);
  let heroVideo = $state<HTMLVideoElement | null>(null);
  let lightboxArtifacts = $state<ComparisonArtifact[] | null>(null);
  let lightboxIndex = $state(0);

  const projects = $derived(studio.projects);
  const featured = $derived(projects[heroIndex] ?? projects[0]);
  const heroTake = $derived(featured ? featuredTake(featured) : undefined);
  const latest = $derived(studio.takes.slice(0, 8));

  function move(direction: number) {
    if (projects.length < 2) return;
    heroIndex = (heroIndex + direction + projects.length) % projects.length;
  }

  function togglePlay() {
    if (!heroVideo) return;
    if (heroVideo.paused) {
      void heroVideo.play().catch(() => {});
      heroPlaying = true;
    } else {
      heroVideo.pause();
      heroPlaying = false;
    }
  }

  function openTake(take: Take) {
    const project = studio.project(take.runId);
    if (!project) return;
    lightboxArtifacts = project.takes.map((t) => t.artifact);
    lightboxIndex = Math.max(0, project.takes.findIndex((t) => t.id === take.id));
  }

  $effect(() => {
    void studio.ensure();
    const interval = setInterval(() => void studio.refresh(), 15000);
    return () => clearInterval(interval);
  });

  $effect(() => {
    if (!studio.heroAutoRotate || projects.length < 2 || lightboxArtifacts) return;
    const timer = setInterval(() => move(1), 9000);
    return () => clearInterval(timer);
  });

  $effect(() => {
    const video = heroVideo;
    if (!video) return;
    const sync = () => {
      if (document.hidden || lightboxArtifacts || !heroPlaying) video.pause();
      else void video.play().catch(() => {});
    };
    sync();
    document.addEventListener('visibilitychange', sync);
    return () => document.removeEventListener('visibilitychange', sync);
  });

  // Swap hero source in place — no {#key} teardown, no poster flash on project change.
  $effect(() => {
    const url = heroTake?.artifact.media_url;
    const video = heroVideo;
    if (!url || !video) return;
    const absolute = new URL(url, document.baseURI).href;
    if (video.currentSrc === absolute) return;

    video.removeAttribute('poster');
    video.src = url;
    video.load();

    if (!heroPlaying || lightboxArtifacts || document.hidden) return;
    const start = () => {
      video.currentTime = 0;
      void video.play().catch(() => {});
    };
    if (video.readyState >= HTMLMediaElement.HAVE_CURRENT_DATA) start();
    else video.addEventListener('loadeddata', start, { once: true });
  });

  $effect(() => {
    if (!lightboxArtifacts) return;
    const previous = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => {
      document.body.style.overflow = previous;
    };
  });
</script>

<svelte:head><title>Trailer Feed</title></svelte:head>

{#if lightboxArtifacts}
  <MediaLightbox artifacts={lightboxArtifacts} activeIndex={lightboxIndex} showDetails={false} onClose={() => (lightboxArtifacts = null)} />
{/if}

<div class="home">
  {#if !studio.loaded}
    <div class="studio-column state"><Icon name="loader" size={16} /> Opening the screening room…</div>
  {:else if !featured}
    <div class="studio-column state-empty">
      <h1 class="t-page">Nothing in the edit yet</h1>
      <p class="muted">Pitch a project and its renders will show up here.</p>
      <a class="sbtn sbtn-primary" href="/create"><Icon name="sparkles" /> Import project</a>
    </div>
  {:else}
    <section class="hero" aria-label="Now playing">
      <div class="screen">
        {#if heroTake}
          <video
            bind:this={heroVideo}
            muted={heroMuted}
            autoplay
            loop
            playsinline
            preload="auto"
            aria-label={featured.title}
          ></video>
        {:else}
          <p class="screen-empty muted">No render for this project yet</p>
        {/if}
        <div class="scrim" aria-hidden="true"></div>

        <div class="overlay">
          {#key featured.runId}
            <div class="stack" in:fade={{ duration: 520 }} out:fade={{ duration: 440 }}>
              <p class="hero-kicker mono">Now showing</p>
              <a class="hero-title-link" href={`/comparisons?run=${featured.runId}`} title={featured.fullTitle}>
                <h1 class="hero-title"><LegacyText text={featured.title} /></h1>
              </a>
              <p class="hero-takes-quiet mono">{plural(featured.takes.length, 'take')}</p>
              <p class="hero-logline">
                {#if featured.logline?.trim()}
                  <LegacyText text={featured.logline} />
                {/if}
              </p>
            </div>
          {/key}

            <div class="media-controls">
              {#if heroTake}
                <button type="button" class="ctl" onclick={togglePlay} aria-label={heroPlaying ? 'Pause' : 'Play'}>
                  <Icon name={heroPlaying ? 'pause' : 'play'} size={14} filled={!heroPlaying} />
                </button>
                <button type="button" class="ctl" onclick={() => (heroMuted = !heroMuted)} aria-label={heroMuted ? 'Unmute' : 'Mute'} aria-pressed={!heroMuted}>
                  <Icon name={heroMuted ? 'mute' : 'volume'} size={14} />
                </button>
              {/if}
              {#if projects.length > 1}
                <button type="button" class="ctl" onclick={() => move(-1)} aria-label="Previous project"><Icon name="left" size={14} /></button>
                <button type="button" class="ctl" onclick={() => move(1)} aria-label="Next project"><Icon name="right" size={14} /></button>
              {/if}
            </div>
        </div>
      </div>
    </section>

    <div class="studio-column rows">
      {#if latest.length}
        <section aria-labelledby="latest-title">
          <div class="row-head">
            <div class="row-title">
              <h2 id="latest-title" class="t-section">Latest renders</h2>
              <span class="dim latest-kicker">Newest takes across every project</span>
            </div>
            <a class="sbtn" href="/create"><Icon name="sparkles" /> Import project</a>
          </div>
          <div class="grid-clips">
            {#each latest as take (take.id)}
              {@const project = studio.project(take.runId)}
              <ClipCard
                title={project?.title ?? showTitle(take.artifact.title)}
                fullTitle={project?.fullTitle}
                takeLabel={take.code}
                status={take.selected ? 'Selected' : ''}
                videoUrl={take.artifact.media_url}
                thumbnailUrl={take.artifact.thumbnail_url}
                isNewest={take.isNewest}
                playOnHover={studio.playOnHover}
                onselect={() => openTake(take)}
              />
            {/each}
          </div>
        </section>
      {/if}

      <section aria-labelledby="projects-title">
        <div class="row-head">
          <div class="row-title">
            <h2 id="projects-title" class="t-section">Projects</h2>
            <span class="dim row-note">{projects.length} in the library</span>
          </div>
          <a class="sbtn" href="/comparisons">All projects <Icon name="up-right" /></a>
        </div>
        <div class="grid-posters">
          {#each projects as project, i (project.runId)}
            <ProjectCard
              title={project.title}
              fullTitle={project.fullTitle}
              cover={featuredCoverArtifact(project)}
              status={portfolioStatusVisible(project.status) ? project.status : ''}
              takeCount={project.takes.length}
              selected={i === heroIndex}
              onselect={() => goto(`/comparisons?run=${project.runId}`)}
            />
          {/each}
        </div>
      </section>
    </div>
  {/if}
</div>

<style>
  .home {
    padding-bottom: clamp(48px, 6vw, 88px);
  }

  .state {
    display: flex;
    align-items: center;
    gap: 10px;
    padding-block: 96px;
    color: var(--dc-text-muted);
    font-size: 14px;
  }

  .state-empty {
    display: grid;
    justify-items: start;
    gap: 12px;
    padding-block: 64px;
  }

  .state-empty p {
    margin: 0;
  }

  .hero {
    position: relative;
    margin-top: calc(-1 * var(--dc-nav-offset));
    container-type: inline-size;
  }

  .screen {
    position: relative;
    width: 100%;
    aspect-ratio: 16 / 9;
    max-height: calc(100dvh - 40px);
    min-height: 240px;
    overflow: hidden;
    background: #000;
  }

  .screen video {
    position: absolute;
    inset: 0;
    width: 100%;
    height: 100%;
    object-fit: cover;
  }

  .screen-empty {
    display: grid;
    height: 100%;
    margin: 0;
    place-items: center;
    font-size: 14px;
  }

  .scrim {
    position: absolute;
    inset: 0;
    pointer-events: none;
    background:
      linear-gradient(to top, rgba(0, 0, 0, 0.72) 0%, rgba(0, 0, 0, 0.12) 32%, transparent 58%),
      linear-gradient(to right, rgba(0, 0, 0, 0.48) 0%, transparent 50%);
  }

  .overlay {
    position: absolute;
    inset: 0;
    display: flex;
    flex-direction: column;
    justify-content: flex-end;
    align-items: flex-start;
    padding-block: clamp(16px, 3vw, 28px);
    padding-inline: max(var(--dc-gutter-x), var(--dc-safe-l)) max(var(--dc-gutter-x), var(--dc-safe-r));
    pointer-events: none;
  }

  .overlay > * {
    pointer-events: auto;
  }

  .mono {
    font-family: var(--dc-font-mono);
    letter-spacing: 0.06em;
    text-transform: uppercase;
    font-size: 10px;
  }

  .hero-title {
    margin: 0;
    color: #fff;
    line-height: 1.08;
    text-shadow: 0 2px 20px rgba(0, 0, 0, 0.65);
  }

  .stack {
    position: relative;
    max-width: min(440px, 92%);
    display: grid;
    grid-template-rows: auto auto auto minmax(calc(2 * 1.5em), calc(2 * 1.5em));
    gap: 6px;
    margin-bottom: 44px;
  }

  .hero-title-link {
    color: inherit;
    text-decoration: none;
  }

  .hero-title-link:hover .hero-title {
    opacity: 0.78;
  }

  .hero-title {
    font-family: var(--dc-font-sans);
    font-size: clamp(1.35rem, 2.4vw, 1.85rem);
    font-weight: 600;
    letter-spacing: -0.03em;
    opacity: 0.65;
  }

  .hero-kicker {
    margin: 0;
    font-size: 10px;
    color: rgba(255, 255, 255, 0.5);
    text-transform: uppercase;
    letter-spacing: 0.14em;
  }

  .hero-takes-quiet {
    margin: 0;
    min-height: 1.2em;
    font-size: 9px;
    color: rgba(255, 255, 255, 0.38);
    text-transform: uppercase;
    letter-spacing: 0.12em;
  }

  .hero-logline {
    margin: 0;
    font-family: var(--dc-font-sans);
    font-size: 13px;
    font-weight: 400;
    line-height: 1.5;
    color: rgba(255, 255, 255, 0.55);
    display: -webkit-box;
    -webkit-line-clamp: 2;
    line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
    min-height: calc(2 * 1.5em);
  }

  .media-controls {
    position: absolute;
    bottom: clamp(16px, 3vw, 28px);
    left: max(var(--dc-gutter-x), var(--dc-safe-l));
    display: flex;
    gap: 6px;
    pointer-events: auto;
  }

  .ctl {
    width: 32px;
    height: 32px;
    display: grid;
    place-items: center;
    border: 0;
    border-radius: 6px;
    background: rgba(0, 0, 0, 0.45);
    color: #fff;
    cursor: pointer;
    backdrop-filter: blur(6px);
  }

  .rows {
    display: grid;
    grid-template-columns: minmax(0, 1fr);
    gap: clamp(40px, 5vw, 64px);
    margin-top: clamp(20px, 3vw, 32px);
  }

  .row-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 16px;
    margin-bottom: 14px;
  }

  .row-title {
    display: flex;
    min-width: 0;
    align-items: baseline;
    gap: 12px;
  }

  .row-title .t-section {
    flex-shrink: 0;
  }

  .row-note {
    overflow: hidden;
    font-size: 13px;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .latest-kicker {
    font-family: var(--dc-font-sans);
    font-size: 13px;
    font-weight: 400;
    letter-spacing: 0;
    text-transform: none;
    line-height: 1.5;
    color: var(--dc-text-muted);
  }

  .grid-clips {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(min(100%, 280px), 1fr));
    gap: 16px;
  }

  .grid-posters {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(min(100%, 240px), 1fr));
    gap: 16px;
  }

  @media (max-width: 560px) {
    .row-note {
      display: none;
    }

    .grid-clips,
    .grid-posters {
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 10px;
    }
  }
</style>