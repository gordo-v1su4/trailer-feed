export type PrototypeVariant = 'A' | 'B' | 'C';

export const VARIANT_BLURBS: Record<PrototypeVariant, { title: string; home: string; projects: string }> = {
  A: {
    title: 'Dense',
    home: 'Glass hero card, take pills, Latest + Projects grids',
    projects: 'Player + side rail + drawer below',
  },
  B: {
    title: 'Compact',
    home: 'Split hero: video beside copy; no Latest row',
    projects: 'Take dropdown, no rail, drawer first',
  },
  C: {
    title: 'Editorial',
    home: 'Title on picture, one Watch CTA, posters only',
    projects: 'Wide player, quiet header, drawer tabs as chips',
  },
};

export function readVariant(searchParams: URLSearchParams): PrototypeVariant {
  const raw = (searchParams.get('variant') ?? 'A').toUpperCase();
  if (raw === 'B' || raw === 'C') return raw;
  return 'A';
}

/** Keep ?variant= when linking between Home and Projects. */
export function hrefWithVariant(path: string, searchParams: URLSearchParams): string {
  const variant = searchParams.get('variant');
  if (!variant || variant.toUpperCase() === 'A') return path;
  const join = path.includes('?') ? '&' : '?';
  return `${path}${join}variant=${encodeURIComponent(variant)}`;
}

export function searchParamsWithVariant(searchParams: URLSearchParams): URLSearchParams {
  const next = new URLSearchParams(searchParams);
  const variant = searchParams.get('variant');
  if (variant && variant.toUpperCase() !== 'A') next.set('variant', variant);
  else next.delete('variant');
  return next;
}