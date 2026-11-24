<script lang="ts">
  import LegacyText from '$lib/components/LegacyText.svelte';
  import { fade } from 'svelte/transition';
  import { goto } from '$app/navigation';
  import MediaLightbox from '$lib/components/MediaLightbox.svelte';
  import ClipCard from '$lib/components/ClipCard.svelte';
  import ProjectCard from '$lib/components/ProjectCard.svelte';
  import Icon from '$lib/components/Icon.svelte';
  import PrototypeSwitcher from '$lib/components/PrototypeSwitcher.svelte';
  import { page } from '$app/state';
  import { hrefWithVariant, readVariant } from '$lib/ui/prototype-variant';
  import { featuredCoverArtifact, featuredTake, portfolioStatusVisible, studio, type Take } from '$lib/ui/studio.svelte';
  import { toneFor } from '$lib/ui/tones';
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
  const variant = $derived(readVariant(page.url.searchParams));

  function pad(n: number) {
    return String(n).padStart(2, '0');
  }

  function takeHref(take: Take) {
    return `/comparisons?run=${take.runId}&take=${take.id}`;
  }

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

  // Rotate the hero only when the director asked for it on Sources.
  $effect(() => {
    if (!studio.heroAutoRotate || projects.length < 2 || lightboxArtifacts) return;
    const timer = setInterval(() => move(1), 9000);
    return () => clearInterval(timer);
  });

  // Quiet the hero in a background tab and under the player.
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

  // Phones scroll the document; hold it still while the player is open.
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

<div class="home" data-variant={variant}>
  {#if !studio.loaded}
    <div class="studio-column state"><Icon name="loader" size={16} /> Opening the screening room…</div>
  {:else if !featured}
    <div class="studio-column state-empty">
      <h1 class="t-page">Nothing in the edit yet</h1>
      <p class="muted">Pitch a project and its renders will show up here.</p>
      <a class="sbtn sbtn-primary" href="/create"><Icon name="sparkles" /> Import project</a>
    </div>
  {:else}
    <!-- Now playing: the video runs edge to edge, under the glass nav. -->
    <section class="hero" class:hero-b={variant === 'B'} class:hero-c={variant === 'C'} aria-label="Now playing">
      <div class="screen">
        {#if heroTake}
          {#key heroTake.id}
            <video
              bind:this={heroVideo}
              src={heroTake.artifact.media_url}
              poster={heroTake.artifact.thumbnail_url}
              muted={heroMuted}
              autoplay
              loop
              playsinline
              aria-label={featured.title}
              transition:fade={{ duration: 400 }}
            ></video>
          {/key}
        {:else}
          <p class="screen-empty muted">No render for this project yet</p>
        {/if}
        <div class="screen-scrim" aria-hidden="true"></div>
      </div>

      <div class="hero-overlay studio-column" class:overlay-c={variant === 'C'}>
        {#key featured.runId}
          <div class="title-card" class:glass-panel={variant !== 'C'} class:editorial-card={variant === 'C'} in:fade={{ duration: 300 }}>
            {#if variant !== 'C'}
              <div class="tags">
                {#if portfolioStatusVisible(featured.status)}
                  <span class="stag tone-{toneFor(featured.status)}">{featured.status}</span>
                {/if}
                {#if heroTake}
                  <span class="stag tone-{toneFor(heroTake.model || heroTake.writer)}">
                    {heroTake.code}{heroTake.writer ? ` · ${heroTake.writer}` : ''}{#if heroTake.model} · <LegacyText text={heroTake.model} />{/if}
                  </span>
                {/if}
              </div>
            {:else if heroTake?.model}
              <p class="editorial-kicker"><LegacyText text={heroTake.model} /> · {heroTake.code}</p>
            {/if}
            <h1 class="t-page" class:editorial-title={variant === 'C'} title={featured.fullTitle}><LegacyText text={featured.title} /></h1>
            {#if variant !== 'C'}
              <p class="logline"><LegacyText text={featured.logline} /></p>
            {:else}
              <p class="logline editorial-logline"><LegacyText text={featured.logline} /></p>
            {/if}
            {#if variant === 'A' && featured.takes.length > 1}
              <nav class="take-pills" aria-label="Takes for this project">
                {#each featured.takes as t (t.id)}
                  <a
                    class="take-pill"
                    class:active={t.id === heroTake?.id}
                    href={takeHref(t)}
                    aria-current={t.id === heroTake?.id ? 'true' : undefined}
                  >{t.code}</a>
                {/each}
              </nav>
            {/if}
            <div class="actions" class:actions-c={variant === 'C'}>
              {#if heroTake}
                <a class="sbtn sbtn-primary" class:editorial-cta={variant === 'C'} href={hrefWithVariant(takeHref(heroTake), page.url.searchParams)}>
                  <Icon name="play" size={12} filled />
                  Watch {heroTake.code}
                </a>
              {/if}
              {#if variant !== 'C'}
                <a class="sbtn" href={hrefWithVariant(`/comparisons?run=${featured.runId}`, page.url.searchParams)}>
                  <span class="wide-only">Compare all takes</span><span class="narrow-only">All takes</span> ({featured.takes.length}) <Icon name="up-right" />
                </a>
                {#if heroTake}
                  <button type="button" class="sbtn sbtn-icon" onclick={togglePlay} aria-label={heroPlaying ? 'Pause hero video' : 'Play hero video'}>
                    <Icon name={heroPlaying ? 'pause' : 'play'} filled={!heroPlaying} />
                  </button>
                  <button type="button" class="sbtn sbtn-icon" onclick={() => (heroMuted = !heroMuted)} aria-label={heroMuted ? 'Turn sound on' : 'Turn sound off'} aria-pressed={!heroMuted}>
                    <Icon name={heroMuted ? 'mute' : 'volume'} />
                  </button>
                {/if}
              {/if}
            </div>
          </div>
        {/key}

        {#if projects.length > 1 && variant !== 'C'}
          <div class="switcher">
            <span class="dim counter">{pad(heroIndex + 1)} / {pad(projects.length)}</span>
            <button type="button" class="sbtn sbtn-icon glassy" onclick={() => move(-1)} aria-label="Previous featured project">
              <Icon name="left" size={16} />
            </button>
            <button type="button" class="sbtn sbtn-icon glassy" onclick={() => move(1)} aria-label="Next featured project">
              <Icon name="right" size={16} />
            </button>
          </div>
        {/if}
      </div>
    </section>

    <div class="studio-column rows" class:rows-b={variant === 'B'} class:rows-c={variant === 'C'}>
      {#if latest.length && variant === 'A'}
        <section aria-labelledby="latest-title">
          <div class="row-head">
            <div class="row-title">
              <h2 id="latest-title" class="t-section">Latest renders</h2>
              <span class="dim row-note">Newest takes across every project</span>
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
                writer={take.writer}
                videoModel={take.model}
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
          <a class="sbtn" href={hrefWithVariant('/comparisons', page.url.searchParams)}>All projects <Icon name="up-right" /></a>
        </div>
        <div class="grid-posters" class:poster-strip={variant === 'B' || variant === 'C'}>
          {#each projects as project, i (project.runId)}
            <ProjectCard
              title={project.title}
              fullTitle={project.fullTitle}
              cover={featuredCoverArtifact(project)}
              status={portfolioStatusVisible(project.status) ? project.status : ''}
              takeCount={project.takes.length}
              selected={i === heroIndex}
              onselect={() => goto(hrefWithVariant(`/comparisons?run=${project.runId}`, page.url.searchParams))}
            />
          {/each}
        </div>
      </section>
    </div>
  {/if}
</div>

<PrototypeSwitcher />

<style>
  .home {
    padding-bottom: clamp(48px, 6vw, 88px);
  }

  .take-pills {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    margin-top: 12px;
  }

  .take-pill {
    height: 26px;
    padding: 0 10px;
    border-radius: 999px;
    border: 1px solid #333;
    background: #121212;
    color: var(--dc-text-muted);
    font-size: 12px;
    font-weight: 600;
    text-decoration: none;
    display: inline-flex;
    align-items: center;
  }

  .take-pill.active {
    border-color: #666;
    background: #2a2a2a;
    color: var(--dc-text);
  }

  .hero-b {
    display: grid;
    gap: 16px;
  }

  @media (min-width: 900px) {
    .hero-b {
      grid-template-columns: minmax(0, 1.35fr) minmax(280px, 0.85fr);
      align-items: stretch;
    }

    .hero-b .screen {
      max-height: none;
      min-height: min(56vh, 640px);
    }

    .hero-b .hero-overlay {
      position: static;
      margin-top: 0;
      justify-content: center;
    }

    .hero-b .title-card {
      width: 100%;
    }
  }

  .hero-c {
    position: relative;
  }

  .hero-c .screen {
    max-height: min(88vh, 900px);
  }

  .hero-c .screen-scrim {
    background:
      linear-gradient(to top, #000 0%, rgba(0, 0, 0, 0.15) 40%, rgba(0, 0, 0, 0) 70%),
      linear-gradient(to bottom, rgba(0, 0, 0, 0.35) 0%, rgba(0, 0, 0, 0) 22%);
  }

  .overlay-c {
    position: absolute;
    inset: auto 0 0 0;
    padding: 0 clamp(16px, 4vw, 32px) clamp(20px, 4vw, 40px);
    pointer-events: none;
  }

  .overlay-c .title-card,
  .overlay-c .actions {
    pointer-events: auto;
  }

  .editorial-card {
    max-width: 720px;
    padding: 0;
    background: transparent;
  }

  .editorial-kicker {
    margin: 0 0 8px;
    color: rgba(255, 255, 255, 0.75);
    font-size: 13px;
    text-transform: uppercase;
    letter-spacing: 0.08em;
  }

  .editorial-title {
    font-size: clamp(2rem, 5vw, 3.25rem);
    line-height: 1.05;
    text-shadow: 0 2px 24px rgba(0, 0, 0, 0.8);
  }

  .editorial-logline {
    max-width: 42ch;
    color: rgba(255, 255, 255, 0.72);
    text-shadow: 0 1px 12px rgba(0, 0, 0, 0.85);
  }

  .actions-c {
    margin-top: 20px;
  }

  .editorial-cta {
    padding-inline: 18px;
    font-size: 15px;
  }

  .rows-b,
  .rows-c {
    margin-top: 20px;
  }

  .poster-strip {
    display: flex;
    gap: 12px;
    overflow-x: auto;
    scroll-snap-type: x mandatory;
    padding-bottom: 4px;
    scrollbar-width: thin;
  }

  .poster-strip :global(.poster) {
    flex: 0 0 min(280px, 72vw);
    scroll-snap-align: start;
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

  /* ── Hero ─────────────────────────────────────────────────────── */

  .hero {
    position: relative;
    /* Run under the floating nav so the glass has picture behind it. */
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

  .screen-scrim {
    position: absolute;
    inset: 0;
    pointer-events: none;
    background:
      linear-gradient(to top, #000 0%, rgba(0, 0, 0, 0) 30%),
      linear-gradient(to bottom, rgba(0, 0, 0, 0.2) 0%, rgba(0, 0, 0, 0) 18%);
  }

  .hero-overlay {
    position: relative;
    display: flex;
    flex-direction: column;
    gap: 12px;
    margin-top: -24px;
  }

  .title-card {
    min-width: 0;
    padding: 18px;
  }

  .tags {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    height: 20px;
    margin-bottom: 10px;
    overflow: hidden;
  }

  .tags .stag {
    max-width: 100%;
  }

  .logline {
    display: -webkit-box;
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

  .actions {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 8px;
    margin-top: 16px;
  }

  .switcher {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .counter {
    margin-right: 4px;
    font-size: 13px;
    font-variant-numeric: tabular-nums;
  }

  .glassy {
    background: rgba(22, 22, 22, 0.6);
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
  }

  /* Wide enough to be a screen: the glass card sits over the picture. */
  @container (min-width: 760px) {
    .screen-scrim {
      background:
        linear-gradient(to top, #000 0%, rgba(0, 0, 0, 0.3) 26%, rgba(0, 0, 0, 0) 50%),
        linear-gradient(to right, rgba(0, 0, 0, 0.55) 0%, rgba(0, 0, 0, 0) 50%),
        linear-gradient(to bottom, rgba(0, 0, 0, 0.2) 0%, rgba(0, 0, 0, 0) 16%);
    }

    .hero-overlay {
      position: absolute;
      right: 0;
      bottom: clamp(24px, 4cqi, 56px);
      left: 0;
      flex-direction: row;
      align-items: flex-end;
      justify-content: space-between;
      margin-top: 0;
    }

    .title-card {
      width: min(560px, 60%);
      padding: 22px 24px;
      background: rgba(22, 22, 22, 0.55);
    }
  }

  /* ── Rows ─────────────────────────────────────────────────────── */

  .rows {
    display: grid;
    grid-template-columns: minmax(0, 1fr);
    gap: clamp(40px, 5vw, 64px);
    margin-top: clamp(32px, 4vw, 48px);
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

  .narrow-only {
    display: none;
  }

  @media (max-width: 560px) {
    .wide-only {
      display: none;
    }

    .narrow-only {
      display: inline;
    }

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
