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
    <section class="hero" aria-label="Now playing">
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
        <div class="scrim scrim-{variant.toLowerCase()}" aria-hidden="true"></div>

        {#key `${featured.runId}-${variant}`}
          <div class="overlay overlay-{variant.toLowerCase()}" in:fade={{ duration: 280 }}>
            {#if variant === 'A'}
              <div class="band">
                <div class="band-main">
                  <p class="hero-meta">{heroTake?.code ?? '—'}{#if heroTake?.model} · <LegacyText text={heroTake.model} />{/if}</p>
                  <h1 class="hero-title" title={featured.fullTitle}><LegacyText text={featured.title} /></h1>
                </div>
                {#if featured.takes.length > 1}
                  <nav class="take-rail mono" aria-label="Takes">
                    {#each featured.takes as t (t.id)}
                      <a class="take-chip" class:active={t.id === heroTake?.id} href={hrefWithVariant(takeHref(t), page.url.searchParams)}>{t.code}</a>
                    {/each}
                  </nav>
                {/if}
                <div class="band-actions">
                  {#if heroTake}
                    <a class="hero-textlink" href={hrefWithVariant(takeHref(heroTake), page.url.searchParams)}>Open {heroTake.code}</a>
                  {/if}
                  <a class="hero-textlink muted-link" href={hrefWithVariant(`/comparisons?run=${featured.runId}`, page.url.searchParams)}>All takes</a>
                </div>
              </div>
            {:else if variant === 'B'}
              <div class="stack">
                <p class="hero-kicker mono">{pad(heroIndex + 1)}/{pad(projects.length)} · NOW SHOWING</p>
                <h1 class="hero-title" title={featured.fullTitle}><LegacyText text={featured.title} /></h1>
                {#if heroTake}
                  <p class="hero-sub sans"><LegacyText text={heroTake.model || heroTake.writer} /> · {heroTake.code}</p>
                {/if}
                <p class="hero-logline sans"><LegacyText text={featured.logline} /></p>
                {#if featured.takes.length > 1}
                  <nav class="take-rail mono" aria-label="Takes">
                    {#each featured.takes as t (t.id)}
                      <a class="take-chip block" class:active={t.id === heroTake?.id} href={hrefWithVariant(takeHref(t), page.url.searchParams)}>{t.code}</a>
                    {/each}
                  </nav>
                {/if}
                <a class="hero-textlink" href={hrefWithVariant(`/comparisons?run=${featured.runId}`, page.url.searchParams)}>Project page →</a>
              </div>
            {:else}
              <div class="poster">
                {#if heroTake?.model}<p class="hero-kicker serif-lite"><LegacyText text={heroTake.model} /></p>{/if}
                <h1 class="hero-title poster-title" title={featured.fullTitle}><LegacyText text={featured.title} /></h1>
                <p class="hero-logline script"><LegacyText text={featured.logline} /></p>
                {#if heroTake}
                  <a class="hero-textlink poster-cta" href={hrefWithVariant(takeHref(heroTake), page.url.searchParams)}>{heroTake.code}</a>
                {/if}
              </div>
            {/if}

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
        {/key}
      </div>
    </section>

    <div class="studio-column rows">
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
        <div class="grid-posters" class:poster-strip={variant === 'C'}>
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

  .scrim {
    position: absolute;
    inset: 0;
    pointer-events: none;
  }

  .scrim-a {
    background: linear-gradient(to top, rgba(0, 0, 0, 0.92) 0%, rgba(0, 0, 0, 0.45) 22%, rgba(0, 0, 0, 0) 48%);
  }

  .scrim-b {
    background:
      linear-gradient(to top, rgba(0, 0, 0, 0.88) 0%, rgba(0, 0, 0, 0.2) 35%, transparent 62%),
      linear-gradient(to right, rgba(0, 0, 0, 0.75) 0%, transparent 55%);
  }

  .scrim-c {
    background:
      radial-gradient(ellipse 90% 70% at 50% 100%, rgba(0, 0, 0, 0.85) 0%, transparent 70%),
      linear-gradient(to top, rgba(0, 0, 0, 0.5) 0%, transparent 40%);
  }

  .overlay {
    position: absolute;
    inset: 0;
    display: flex;
    flex-direction: column;
    justify-content: flex-end;
    padding: clamp(16px, 3vw, 28px);
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

  .sans {
    font-family: var(--dc-font-sans);
  }

  .script {
    font-family: var(--dc-font-script);
    font-style: italic;
    letter-spacing: 0.02em;
  }

  .hero-meta {
    margin: 0 0 6px;
    color: rgba(255, 255, 255, 0.65);
  }

  .hero-title {
    margin: 0;
    color: #fff;
    line-height: 1.08;
    text-shadow: 0 2px 20px rgba(0, 0, 0, 0.65);
  }

  .overlay-a .hero-title {
    font-family: var(--dc-font-serif);
    font-size: clamp(1.6rem, 3.2vw, 2.35rem);
    font-weight: 400;
  }

  .overlay-a .band {
    display: grid;
    grid-template-columns: minmax(0, 1fr) auto auto;
    align-items: end;
    gap: clamp(12px, 2vw, 24px);
    width: 100%;
    padding-top: 12px;
    border-top: 1px solid rgba(255, 255, 255, 0.14);
  }

  .overlay-b .stack {
    max-width: min(420px, 92%);
    display: grid;
    gap: 8px;
    padding: 14px 16px;
    border-radius: 8px;
    background: rgba(8, 8, 8, 0.55);
    border: 1px solid rgba(255, 255, 255, 0.08);
    backdrop-filter: blur(8px);
  }

  .overlay-b .hero-title {
    font-family: var(--dc-font-sans);
    font-size: clamp(1.35rem, 2.4vw, 1.85rem);
    font-weight: 600;
    letter-spacing: -0.03em;
  }

  .overlay-b .hero-kicker {
    margin: 0;
    color: rgba(255, 255, 255, 0.55);
  }

  .overlay-b .hero-sub {
    margin: 0;
    font-size: 12px;
    color: rgba(255, 255, 255, 0.78);
  }

  .overlay-b .hero-logline {
    margin: 0;
    font-size: 13px;
    line-height: 1.45;
    color: rgba(255, 255, 255, 0.62);
    display: -webkit-box;
    -webkit-line-clamp: 2;
    line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
  }

  .overlay-c {
    align-items: center;
    text-align: center;
    padding-bottom: clamp(28px, 5vw, 56px);
  }

  .overlay-c .poster-title {
    font-family: var(--dc-font-serif);
    font-size: clamp(2.2rem, 6.5vw, 4.25rem);
    max-width: 16ch;
  }

  .overlay-c .hero-kicker.serif-lite {
    margin: 0 0 4px;
    font-family: var(--dc-font-serif);
    font-size: 14px;
    font-style: italic;
    color: rgba(255, 255, 255, 0.72);
    text-transform: none;
    letter-spacing: 0;
  }

  .overlay-c .hero-logline {
    margin: 10px 0 0;
    max-width: 36ch;
    font-size: 15px;
    color: rgba(255, 255, 255, 0.78);
  }

  .overlay-c .poster-cta {
    margin-top: 14px;
    font-size: 15px;
    letter-spacing: 0.12em;
    text-transform: uppercase;
  }

  .take-rail {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    align-items: center;
  }

  .take-chip {
    padding: 4px 8px;
    border-radius: 4px;
    border: 1px solid rgba(255, 255, 255, 0.2);
    color: rgba(255, 255, 255, 0.7);
    text-decoration: none;
    font-size: 11px;
  }

  .take-chip.block {
    border-radius: 2px;
  }

  .take-chip.active {
    border-color: rgba(255, 255, 255, 0.55);
    color: #fff;
    background: rgba(255, 255, 255, 0.08);
  }

  .band-actions {
    display: flex;
    flex-direction: column;
    align-items: flex-end;
    gap: 6px;
    white-space: nowrap;
  }

  .hero-textlink {
    color: #fff;
    font-size: 13px;
    font-weight: 500;
    text-decoration: none;
    border-bottom: 1px solid rgba(255, 255, 255, 0.35);
    padding-bottom: 1px;
  }

  .hero-textlink.muted-link {
    color: rgba(255, 255, 255, 0.55);
    border-color: rgba(255, 255, 255, 0.2);
    font-size: 12px;
  }

  .media-controls {
    position: absolute;
    top: clamp(52px, 8vw, 72px);
    right: clamp(16px, 3vw, 28px);
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

  @media (max-width: 720px) {
    .overlay-a .band {
      grid-template-columns: 1fr;
      gap: 10px;
    }

    .band-actions {
      flex-direction: row;
      align-items: center;
    }
  }

  /* ── Rows ─────────────────────────────────────────────────────── */

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
