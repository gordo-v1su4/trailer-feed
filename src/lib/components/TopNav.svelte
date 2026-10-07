<script lang="ts">
  import { page } from '$app/state';
  import { NAV_LINKS } from '$lib/nav';
  import { studio } from '$lib/ui/studio.svelte';
  import { showTitle } from '$lib/data/titles';
  import Icon from './Icon.svelte';

  const pathname = $derived(page.url.pathname);
  const newest = $derived(studio.newest);
  const newestProject = $derived(newest ? studio.project(newest.runId) : undefined);

  $effect(() => {
    void studio.ensure();
  });
</script>

<header class="nav">
  <div class="nav-bar">
    <a class="brand" href="/" title="Trailer Feed, the private trailer screening room">
      <Icon name="film" size={16} />
      <span>Trailer Feed</span>
    </a>

    <nav class="tabs" aria-label="Main">
      {#each NAV_LINKS as link (link.href)}
        <a
          href={link.href}
          class="tab"
          class:active={link.match(pathname)}
          title={link.hint}
          aria-current={link.match(pathname) ? 'page' : undefined}
        >
          {link.label}
        </a>
      {/each}
    </nav>

    {#if newest && newestProject}
      <a
        class="sbtn sbtn-primary newest"
        href={`/comparisons?run=${newest.runId}&take=${newest.id}`}
        title={`Jump to the newest take: ${newestProject.fullTitle} (${newest.code})`}
      >
        <Icon name="play" size={12} filled />
        <span class="newest-text">Newest: {showTitle(newestProject.title)} ({newest.code})</span>
      </a>
    {/if}
  </div>
</header>

<style>
  .nav {
    position: fixed;
    z-index: 50;
    top: 0;
    right: 0;
    left: 0;
    padding-top: var(--dc-safe-t);
    background: rgba(0, 0, 0, 0.25);
    backdrop-filter: blur(18px) saturate(1.2);
    -webkit-backdrop-filter: blur(18px) saturate(1.2);
  }

  .nav-bar {
    display: flex;
    align-items: center;
    gap: clamp(16px, 3vw, 48px);
    height: var(--dc-nav-height);
    max-width: var(--dc-page-max);
    box-sizing: content-box;
    margin: 0 auto;
    padding-inline: max(var(--dc-gutter-x), var(--dc-safe-l)) max(var(--dc-gutter-x), var(--dc-safe-r));
  }

  .brand {
    display: inline-flex;
    flex-shrink: 0;
    align-items: center;
    gap: 8px;
    color: var(--dc-text);
    font: 400 20px / 1 var(--dc-font-serif);
    letter-spacing: -0.01em;
    text-decoration: none;
    white-space: nowrap;
  }

  .tabs {
    display: flex;
    min-width: 0;
    align-items: center;
    gap: clamp(4px, 1vw, 16px);
    overflow-x: auto;
    scrollbar-width: none;
  }

  .tabs::-webkit-scrollbar {
    display: none;
  }

  .tab {
    display: inline-flex;
    flex-shrink: 0;
    align-items: center;
    height: 28px;
    padding: 0 10px;
    border-radius: 4px;
    color: var(--dc-text-muted);
    font-size: 13px;
    text-decoration: none;
    white-space: nowrap;
    transition: color 0.15s ease, background 0.15s ease;
  }

  .tab:hover {
    color: var(--dc-text);
    background: rgba(255, 255, 255, 0.06);
  }

  .tab.active {
    color: var(--dc-text);
    background: rgba(255, 255, 255, 0.12);
  }

  .newest {
    min-width: 0;
    margin-left: auto;
  }

  .newest-text {
    max-width: 260px;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  /* Narrow phones: all five tabs win over the logo mark. */
  @media (max-width: 400px) {
    .brand {
      display: none;
    }
  }

  .brand:focus-visible,
  .tab:focus-visible,
  .newest:focus-visible {
    outline: none;
    box-shadow: 0 0 0 3px rgba(231, 229, 228, 0.2);
  }

  /* Phones: the icon stands in for the wordmark and the newest take for its label. */
  @media (max-width: 720px) {
    .brand span {
      display: none;
    }

    .nav-bar {
      gap: 6px;
    }

    .tabs {
      flex: 1;
    }

    .tab {
      padding: 0 7px;
    }

    .newest {
      width: 28px;
      padding: 0;
    }

    .newest-text {
      display: none;
    }
  }
</style>
