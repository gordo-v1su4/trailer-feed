/**
 * The screening room's shared view of the catalog: every project with its
 * playable takes, the newest take across the studio, and the director's
 * viewing preferences. The nav, Home and Projects all read from here so a
 * take is numbered and labelled the same way on every page.
 */
import { loadComparisonRun, loadComparisonsIndex } from '$lib/data/comparisons';
import { showTitle } from '$lib/data/titles';
import { videoModel } from '$lib/data/version-context';
import type { ComparisonArtifact, ComparisonRunDetail, ComparisonRunSummary } from '$lib/types/comparison';

export interface Take {
  id: string;
  runId: string;
  /** "v3": the take's version, or its place in the project when unnumbered. */
  code: string;
  number: number;
  writer: string;
  model: string;
  selected: boolean;
  isNewest: boolean;
  createdAt: string;
  artifact: ComparisonArtifact;
}

export interface Project {
  runId: string;
  projectThumbnailUrl?: string;
  title: string;
  fullTitle: string;
  logline: string;
  status: string;
  created: string;
  summary: ComparisonRunSummary;
  detail: ComparisonRunDetail;
  /** Oldest first, so v1 is the first take and the last is the newest. */
  takes: Take[];
  shotGrids: ComparisonArtifact[];
}

export function isVideo(artifact: ComparisonArtifact) {
  return artifact.artifact_type === 'video_result' || artifact.artifact_type === 'end_video';
}

export function statusLabel(status: string | undefined) {
  const text = (status ?? 'active').replace(/_/g, ' ');
  return text.charAt(0).toUpperCase() + text.slice(1);
}

export function modelLabel(artifact: ComparisonArtifact) {
  const model = videoModel(artifact);
  if (model !== 'Model not set') return model;
  if (artifact.provider === 'sora' || artifact.provider === 'direct_sora') return 'Sora 2';
  if (artifact.provider === 'seedance') return 'Seedance';
  return '';
}

export function timecode(seconds: number) {
  if (!Number.isFinite(seconds) || seconds < 0) return '';
  const whole = Math.round(seconds);
  return `${Math.floor(whole / 60)}:${String(whole % 60).padStart(2, '0')}`;
}

export function plural(count: number, noun: string) {
  return `${count} ${noun}${count === 1 ? '' : 's'}`;
}

function loglineOf(detail: ComparisonRunDetail, summary: ComparisonRunSummary) {
  if (detail.logline) return detail.logline;
  for (const answer of detail.answers) {
    const concept = answer.structured_prompt;
    if (concept && typeof concept === 'object' && !Array.isArray(concept) && 'logline' in concept) {
      return String(concept.logline);
    }
  }
  return summary.logline || 'Logline not added yet.';
}

function buildProject(summary: ComparisonRunSummary, detail: ComparisonRunDetail): Project {
  const writers = new Map(detail.answers.map((answer) => [answer.answer_id, answer.model_name || answer.agent_name]));
  const playable = detail.artifacts
    .filter((artifact) => isVideo(artifact) && !!artifact.media_url && artifact.status !== 'pending' && artifact.status !== 'failed')
    .sort((a, b) => a.created_at.localeCompare(b.created_at));

  // Stored version numbers are kept; unnumbered takes fill the free numbers
  // in the order they were made, so no two takes ever share a code.
  const used = new Set(playable.flatMap((artifact) => (artifact.version_number ? [artifact.version_number] : [])));
  let next = 1;
  const takes = playable.map((artifact): Take => {
    let number = artifact.version_number;
    if (!number) {
      while (used.has(next)) next += 1;
      number = next;
      used.add(number);
    }
    return {
      id: artifact.artifact_id,
      runId: summary.run_id,
      code: `v${number}`,
      number,
      writer: artifact.source_model_label || (artifact.answer_id ? writers.get(artifact.answer_id) ?? '' : ''),
      model: modelLabel(artifact),
      selected: artifact.status === 'selected',
      isNewest: false,
      createdAt: artifact.created_at,
      artifact,
    };
  });

  // Target numbering is authoritative even when a later sync uses an older source date.
  takes.sort((a,b) => a.number - b.number || a.createdAt.localeCompare(b.createdAt) || a.id.localeCompare(b.id));

  return {
    runId: summary.run_id,
    projectThumbnailUrl: detail.project_thumbnail_url,
    title: showTitle(detail.title || summary.title),
    fullTitle: detail.title || summary.title,
    logline: loglineOf(detail, summary),
    status: statusLabel(detail.status || summary.status),
    created: summary.created,
    summary,
    detail,
    takes,
    shotGrids: detail.artifacts.filter((artifact) => artifact.artifact_type === 'shot_grid' && !!artifact.media_url),
  };
}

/** Map over items with at most `limit` calls in flight, keeping order. */
async function mapLimit<T, R>(items: T[], limit: number, fn: (item: T) => Promise<R>): Promise<R[]> {
  const results = new Array<R>(items.length);
  let cursor = 0;
  const worker = async () => {
    while (cursor < items.length) {
      const i = cursor++;
      results[i] = await fn(items[i]);
    }
  };
  await Promise.all(Array.from({ length: Math.min(limit, items.length) }, worker));
  return results;
}

const PREFS_KEY = 'trailer-feed-screening-prefs';

function readPrefs(): { heroAutoRotate: boolean; playOnHover: boolean } {
  try {
    const current = localStorage.getItem(PREFS_KEY);
    const legacy = current === null ? localStorage.getItem('directors-cut-screening-prefs') : null;
    const stored = JSON.parse(current || legacy || '{}');
    if (legacy) localStorage.setItem(PREFS_KEY, legacy);
    return { heroAutoRotate: !!stored.heroAutoRotate, playOnHover: !!stored.playOnHover };
  } catch {
    return { heroAutoRotate: false, playOnHover: false };
  }
}

class Studio {
  projects = $state<Project[]>([]);
  loaded = $state(false);
  heroAutoRotate = $state(false);
  playOnHover = $state(false);
  /** Projects saved here whose fresh copy could not be read yet; retried until it arrives. */
  pending = $state<string[]>([]);

  /** Every take in the studio, newest first. */
  takes = $derived(
    this.projects.flatMap((project) => project.takes).sort((a, b) => b.createdAt.localeCompare(a.createdAt)),
  );
  newest = $derived(this.takes[0]);

  /** Last-seen data per project, to skip rebuilding what did not change. */
  private sigs = new Map<string, string>();
  /** Bumped by every reload, so an overlapping refresh never undoes one. */
  private epochs = new Map<string, number>();
  private removed = new Set<string>();
  private loading: Promise<void> | null = null;
  private refreshing: Promise<void> | null = null;

  constructor() {
    if (typeof localStorage !== 'undefined') {
      const prefs = readPrefs();
      this.heroAutoRotate = prefs.heroAutoRotate;
      this.playOnHover = prefs.playOnHover;
    }
  }

  project(runId: string | null | undefined) {
    return this.projects.find((project) => project.runId === runId);
  }

  setPref(key: 'heroAutoRotate' | 'playOnHover', value: boolean) {
    this[key] = value;
    try {
      localStorage.setItem(PREFS_KEY, JSON.stringify({ heroAutoRotate: this.heroAutoRotate, playOnHover: this.playOnHover }));
    } catch {
      /* private mode: the toggle still works for this visit */
    }
  }

  /** Load once; later calls share the same request. */
  ensure() {
    this.loading ??= this.refresh(true);
    return this.loading;
  }

  /**
   * Bring the catalog up to date. Every project's files are read (four
   * projects at a time, each project's five files in parallel) and a project
   * is rebuilt only when something in them changed, so answers, prompts and
   * version details edited elsewhere show up on every open page.
   */
  async refresh(force = false) {
    if (!force && typeof document !== 'undefined' && document.hidden) return;
    if (this.refreshing) return this.refreshing;
    this.refreshing = this.sync(force).finally(() => (this.refreshing = null));
    return this.refreshing;
  }

  private async sync(force: boolean) {
    const index = await loadComparisonsIndex();
    const summaries = index.runs
      .filter((run) => run.status !== 'promoted' && !this.removed.has(run.run_id))
      .sort((a, b) => b.created.localeCompare(a.created));
    const startEpochs = new Map(this.epochs);

    const results = await mapLimit(summaries, 4, async (summary) => {
      // With good data already on screen, a failed read keeps it (strict);
      // a first load takes whatever it can read.
      const strict = !!this.project(summary.run_id);
      const detail = await loadComparisonRun(summary.run_id, undefined, { strict }).catch(() => null);
      return { summary, detail, sig: detail ? JSON.stringify([summary, detail]) : '' };
    });

    let changed = force || results.length !== this.projects.length;
    const projects = results.flatMap(({ summary, detail, sig }): Project[] => {
      if (this.removed.has(summary.run_id)) return [];
      const current = this.project(summary.run_id);
      // A reload finished while this refresh was reading: its data is newer.
      if (current && this.epochs.get(summary.run_id) !== startEpochs.get(summary.run_id)) return [current];
      if (!detail) return current ? [current] : [];
      if (current && !force && this.sigs.get(summary.run_id) === sig) return [current];
      changed = true;
      this.pending = this.pending.filter((id) => id !== summary.run_id);
      this.sigs.set(summary.run_id, sig);
      return [buildProject(summary, detail)];
    });

    if (changed || projects.some((project, i) => project !== this.projects[i])) {
      this.projects = projects;
      this.markNewest();
    }
    this.loaded = true;
  }

  private markNewest() {
    const newestId = this.takes[0]?.id;
    for (const project of this.projects) for (const take of project.takes) take.isNewest = take.id === newestId;
  }

  forget(runId: string) {
    this.removed.add(runId);
    this.epochs.set(runId, (this.epochs.get(runId) ?? 0) + 1);
    this.sigs.delete(runId);
    this.pending = this.pending.filter((id) => id !== runId);
    this.projects = this.projects.filter((project) => project.runId !== runId);
    this.markNewest();
  }

  /** Re-read one project after it changed (rename, upload, new take). */
  async reload(runId: string) {
    const summary = this.project(runId)?.summary;
    if (!summary) return this.refresh(true);
    const epoch = (this.epochs.get(runId) ?? 0) + 1;
    this.epochs.set(runId, epoch);
    let detail: ComparisonRunDetail | null = null;
    for (let attempt = 0; attempt < 3 && !detail; attempt++) {
      if (attempt) await new Promise((resolve) => setTimeout(resolve, attempt * 1000));
      detail = await loadComparisonRun(runId, undefined, { strict: true }).catch(() => null);
    }
    // A later reload of the same project owns the result.
    if (this.epochs.get(runId) !== epoch) return;
    this.sigs.delete(runId);
    if (!detail) {
      // The change is saved but could not be read back: keep what is on
      // screen, flag the project, and let refreshes retry until it lands.
      if (!this.pending.includes(runId)) this.pending = [...this.pending, runId];
      setTimeout(() => void this.refresh(), 5000);
      return;
    }
    this.pending = this.pending.filter((id) => id !== runId);
    const fresh = buildProject({ ...summary, title: detail.title, logline: detail.logline }, detail);
    this.projects = this.projects.map((project) => (project.runId === runId ? fresh : project));
    this.markNewest();
  }
}

export const studio = new Studio();
