<script lang="ts">
  import { page } from '$app/state';
  import { goto } from '$app/navigation';
  import { readVariant, VARIANT_BLURBS, type PrototypeVariant } from '$lib/ui/prototype-variant';

  const dev = import.meta.env.DEV;
  const variants: PrototypeVariant[] = ['A', 'B', 'C'];
  const current = $derived(readVariant(page.url.searchParams));
  const blurb = $derived(
    page.url.pathname === '/comparisons' ? VARIANT_BLURBS[current].projects : VARIANT_BLURBS[current].home,
  );

  function pick(variant: PrototypeVariant) {
    const params = new URLSearchParams(page.url.searchParams);
    if (variant === 'A') params.delete('variant');
    else params.set('variant', variant);
    const query = params.toString();
    void goto(query ? `${page.url.pathname}?${query}` : page.url.pathname, { replaceState: true, keepFocus: true, noScroll: true });
  }
</script>

{#if dev}
  <div class="proto-bar" role="region" aria-label="UI prototype variants (development only)">
    <span class="proto-kicker">Portfolio A/B/C</span>
    <div class="proto-buttons" role="group" aria-label="Variant">
      {#each variants as variant (variant)}
        <button
          type="button"
          class="proto-btn"
          class:active={current === variant}
          title={VARIANT_BLURBS[variant].title}
          aria-pressed={current === variant}
          onclick={() => pick(variant)}
        >
          {variant}<span class="proto-name">{VARIANT_BLURBS[variant].title}</span>
        </button>
      {/each}
    </div>
    <p class="proto-blurb">{blurb}</p>
  </div>
{/if}

<style>
  .proto-bar {
    position: fixed;
    z-index: 2000;
    right: 16px;
    bottom: 16px;
    max-width: min(360px, calc(100vw - 32px));
    display: grid;
    gap: 8px;
    padding: 10px 12px;
    border-radius: 10px;
    background: rgba(10, 10, 10, 0.94);
    border: 1px solid #333;
    box-shadow: 0 12px 40px rgba(0, 0, 0, 0.55);
    font-size: 12px;
  }

  .proto-kicker {
    font-weight: 600;
    letter-spacing: 0.04em;
    text-transform: uppercase;
    color: var(--dc-text-muted);
    font-size: 10px;
  }

  .proto-buttons {
    display: flex;
    gap: 4px;
  }

  .proto-btn {
    flex: 1;
    display: grid;
    gap: 2px;
    min-height: 40px;
    padding: 6px 8px;
    border: 1px solid #2a2a2a;
    border-radius: 6px;
    background: #141414;
    color: var(--dc-text-muted);
    font: 600 13px / 1 var(--dc-font-sans);
    cursor: pointer;
  }

  .proto-name {
    font-size: 10px;
    font-weight: 500;
    color: #888;
  }

  .proto-btn.active {
    border-color: #555;
    background: #242424;
    color: var(--dc-text);
  }

  .proto-btn.active .proto-name {
    color: var(--dc-text-muted);
  }

  .proto-blurb {
    margin: 0;
    color: var(--dc-text-muted);
    line-height: 1.35;
  }
</style>