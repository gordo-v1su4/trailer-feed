export type PrototypeVariant = 'A' | 'B' | 'C';

export const VARIANT_BLURBS: Record<PrototypeVariant, { title: string; home: string; projects: string }> = {
  A: {
    title: 'Lower third',
    home: 'Full-bleed video · serif title · mono take rail · no glass card',
    projects: 'Player + thumb rail · classic drawer',
  },
  B: {
    title: 'Studio left',
    home: 'Trailer-first copy · no model or take chips · transport bottom-left',
    projects: 'Thumb filmstrip · take count only in header',
  },
  C: {
    title: 'Poster',
    home: 'Full-bleed video · oversized serif · script logline · center',
    projects: 'Wide player · pill tabs · no writer chrome',
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