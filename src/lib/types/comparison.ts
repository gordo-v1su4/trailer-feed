/*
 * Trailer Feed comparison lab types.
 *
 * Aligned with schemas/model-answer.schema.json and schemas/comparison-run.schema.json,
 * plus the artifact/versioning UX described in docs/comparison-lab-requirements.md.
 */

export interface ComparisonRun {
  run_id: string;
  title: string;
  logline?: string;
  brief?: string;
  question: string;
  created: string;
  created_by: string;
  status:
    | 'draft'
    | 'running'
    | 'answers_partial'
    | 'answers_collected'
    | 'concepts_approved'
    | 'generation_partial'
    | 'partially_generated'
    | 'ready_for_review'
    | 'graded'
    | 'promoted';
  models_requested?: string[];
  target_models?: string[];
  source_refs?: Record<string, unknown>[];
  tags?: string[];
  project_thumbnail_url?: string;
  project_thumbnail_object_key?: string;
}

export interface CreativeConceptPackage {
  package_type: 'creative_concept_v1';
  title: string;
  logline: string;
  summary: string;
  sora_prompt: string;
  runtime_seconds: 12;
  prompt_count: 1;
}

export type LegacyStructuredPrompt =
  | string
  | number
  | boolean
  | null
  | LegacyStructuredPrompt[]
  | { [key: string]: LegacyStructuredPrompt };

export interface ModelAnswer {
  answer_id: string;
  run_id: string;
  agent_name: string;
  model_name: string;
  model_class: string | null;
  target_model: string;
  prompt_mode: string | null;
  answer_text: string;
  structured_prompt?: CreativeConceptPackage | LegacyStructuredPrompt;
  structure_status?: 'valid' | 'invalid' | 'unparsed';
  created_at: string;
  tokens_estimated?: number | null;
  source: string;
  content_sha256?: string;
  prompt_sha256?: string;
  skill_id?: string;
  container_settings?: {
    model: 'sora_2';
    seconds: 12;
    size: '1280x720';
    aspect_ratio: '16:9';
    input: 'text';
  };
  // Runtime UI status, not persisted in schema
  ui_status?: 'captured' | 'pending' | 'missing';
}

export type ConceptDecisionValue = 'approved' | 'rejected';

export interface ConceptDecision {
  decision_id: string;
  run_id: string;
  answer_id: string;
  decision: ConceptDecisionValue;
  note?: string;
  decided_at: string;
  prompt_sha256?: string;
  source: 'directors_cut_ui' | 'bridge' | string;
}

export type ArtifactType =
  | 'shot_grid'
  | 'image_result'
  | 'video_result'
  | 'end_video'
  | 'reference_image'
  | 'prompt_revision';

export type ArtifactProvider =
  | 'nano_banana_pro'
  | 'sora'
  | 'seedance'
  | 'manual_upload'
  | 'raycast'
  | 'higgsfield'
  | 'direct_sora'
  | 'unknown';

export type ArtifactSource = 'generated' | 'uploaded' | 'captured' | 'manual';

export type ReferencePlatform = 'pinterest' | 'upload' | 'generated' | 'web' | 'manual';
export type ReferenceRole = 'style' | 'composition' | 'character' | 'product' | 'lighting' | 'environment' | 'mood';
export type RightsStatus = 'unknown' | 'mood_reference_only' | 'owned' | 'licensed' | 'generated';
export type ArtifactStatus = 'pending' | 'generated' | 'failed' | 'selected' | 'rejected';

export interface GenerationPrompt {
  prompt_id: string;
  run_id: string;
  answer_id?: string;
  slot_type: ArtifactType;
  prompt_text: string;
  model: string;
  provider: ArtifactProvider;
  created_at: string;
  source: ArtifactSource;
  artifact_ids?: string[];
  notes?: string;
  prompt_sha256?: string;
  response_sha256?: string;
  source_model_label?: string;
  skill_id?: string;
  generation_id?: string;
  quote_id?: string;
  duration_seconds?: 12;
  aspect_ratio?: '16:9';
}

export interface ComparisonArtifact {
  artifact_id: string;
  ownership?: 'server' | 'external';
  source_app?: string;
  source_asset_id?: string;
  source_version_id?: string;
  consent_generation?: number;
  version_number?: number;
  version_prompt?: string;
  video_model?: string;
  shot_grid_url?: string | null;
  shot_grid_artifact_id?: string | null;
  context_revision?: number;
  run_id: string;
  answer_id?: string;
  revision_id?: string;
  prompt_id?: string;
  artifact_type: ArtifactType;
  provider: ArtifactProvider;
  title: string;
  target_model?: string;
  prompt_text?: string;
  media_url?: string;
  local_path?: string;
  thumbnail_url?: string;
  reference_image_ids?: string[];
  created_at: string;
  source: ArtifactSource;
  status?: ArtifactStatus;
  model?: string;
  job_id?: string;
  generation_id?: string;
  quote_id?: string;
  prompt_sha256?: string;
  response_sha256?: string;
  source_model_label?: string;
  skill_id?: string;
  result_url?: string;
  width?: number;
  height?: number;
  duration_seconds?: 12;
  aspect_ratio?: '16:9';
  credit_cost?: number;
  submitted_at?: string;
  completed_at?: string;
  notes?: string;
}

export interface ReferenceImageArtifact extends ComparisonArtifact {
  artifact_type: 'reference_image';
  source_platform: ReferencePlatform;
  reference_role: ReferenceRole;
  rights_status: RightsStatus;
}

export interface VersionedArtifactSlot {
  slot_type: ArtifactType;
  active_artifact_id: string | null;
  versions: ComparisonArtifact[];
}

export interface ComparisonRow {
  run_id: string;
  answer: ModelAnswer;
  promptOnlyImageSlot: VersionedArtifactSlot;
  promptOnlyVideoSeedanceSlot: VersionedArtifactSlot;
  promptOnlyVideoSoraSlot: VersionedArtifactSlot;
  referenceImages: ReferenceImageArtifact[];
  referenceAssistedImageSlot: VersionedArtifactSlot;
  referenceAssistedVideoSeedanceSlot: VersionedArtifactSlot;
  referenceAssistedVideoSoraSlot: VersionedArtifactSlot;
  notes?: string;
  conceptDecision?: ConceptDecision;
  reviewStatus?: 'approved' | 'rejected' | 'pending';
  canApprove?: boolean;
  canGenerate?: boolean;
  visionScores?: { model: string; score: number | null; note?: string }[];
}

export interface VisionScore {
  model: string;
  score: number | null;
  note?: string;
  scored_at?: string;
}

export interface ComparisonRunDetail extends ComparisonRun {
  answers: ModelAnswer[];
  artifacts: ComparisonArtifact[];
  prompts: GenerationPrompt[];
  decisions: ConceptDecision[];
  rows: ComparisonRow[];
}

export interface ComparisonRunSummary {
  logline?: string;
  project_thumbnail_url?: string;
  run_id: string;
  title: string;
  status: ComparisonRun['status'];
  answer_count: number;
  artifact_count: number;
  approved_concept_count?: number;
  model_labels: string[];
  created: string;
}
