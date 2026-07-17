export type JobState =
  | "uploaded"
  | "queued"
  | "normalizing"
  | "tracking"
  | "phase_candidates"
  | "visual_review"
  | "diagnosing"
  | "matching_references"
  | "needs_player_selection"
  | "completed"
  | "failed"
  | "deleting"
  | "expired";

export interface AnalysisJob {
  analysis_id: string;
  state: JobState;
  progress: number;
  expires_at: string;
  action_hint?: string | null;
  failure_code?: string | null;
  access_token: string;
}

export interface FrameRef {
  frame_id: string;
  owner: "student" | "coach";
  phase: string;
  timestamp_ms: number;
  confidence: "low" | "medium" | "high";
  visible_facts: string[];
  limitations: string[];
  media_url?: string;
  source_url?: string;
  source_jump_url?: string;
  title?: string;
}

export interface CoachReference {
  reference_id: string;
  coach_id: string;
  source_id: string;
  phase: string;
  timestamp_ms: number;
  confidence: "low" | "medium" | "high";
  availability: "indexed" | "cached" | "unavailable" | "removed";
  visible_facts: string[];
  limitations: string[];
  media_url?: string;
  clip_media_url?: string;
  clip_start_ms?: number | null;
  clip_end_ms?: number | null;
  source_url?: string;
  source_jump_url?: string;
  title?: string;
}

export interface ActionPackageSegment {
  segment_id: string;
  phase: string;
  anchor_ms: number;
  start_ms: number;
  end_ms: number;
  confidence: "low" | "medium" | "high";
  caption: string;
  limitations: string[];
  media_url?: string;
}

export function indexCoachReferences(references: CoachReference[]): Map<string, CoachReference> {
  return new Map(references.map((reference) => [reference.reference_id, reference]));
}

export interface IssueEvidence {
  issue_id: string;
  comparison_phase: string;
  student_frame_ids: string[];
  coach_reference_ids: string[];
  correction_target: string;
  confidence_boundary: string;
  status: "matched" | "insufficient_evidence" | "coach_reference_unavailable";
}

export interface CoachingIssue {
  issue_id: string;
  issue: string;
  evidence: string[];
  correction_principle: string;
  drills: Array<{ name: string; dosage: string }>;
  retest_metrics: string[];
}

export interface CoachingReport {
  coach_name: string;
  primary_framework: string;
  confidence: string;
  issues: CoachingIssue[];
  issue_evidence: IssueEvidence[];
  frame_refs: FrameRef[];
  action_package: ActionPackageSegment[];
  action_package_missing_phases?: string[];
  coach_references: CoachReference[];
  missing_evidence: string[];
  retake_guidance?: string;
  participants?: {
    learner_track_id: string;
    partner_track_id: string;
    opponent_track_ids: string[];
    candidate_track_ids: string[];
  };
  multiplayer_evidence?: {
    tracked_player_count: number;
    shuttle_candidate_count: number;
    player_tracks: Array<{ track_id: string; role: "learner" | "partner" | "opponent"; sample_count: number; mean_confidence: number }>;
    contact_candidates: Array<{ candidate_id: string; start_ms: number; end_ms: number; anchor_ms: number; contact_time_ms: null; possible_track_ids: string[]; confidence: "low" | "medium" | "high"; limitations: string[] }>;
    rallies: Array<{ rally_id: string; start_ms: number; end_ms: number; shuttle_candidate_ids: string[] }>;
    limitations: string[];
  };
  rally_frames?: RallyFrame[];
}

export interface SetupPlayer {
  track_id: string;
  bbox: { x: number; y: number; width: number; height: number };
  confidence: number;
  visible_sample_count: number;
}

export interface MixedDoublesSetup {
  analysis_id: string;
  state: JobState;
  candidate_frame: { asset_id: string; timestamp_ms: number; width: number; height: number; media_url?: string };
  players: SetupPlayer[];
  selection: null | {
    learner_track_id: string;
    partner_track_id: string;
    court_corners: Record<string, { x: number; y: number }>;
  };
}

export interface RallyFrame {
  frame_id: string;
  module: string;
  timestamp_ms: number;
  caption: string;
  confidence: "low" | "medium" | "high";
  visible_facts: string[];
  limitations: string[];
  media_url: string;
}

export interface JobEvent {
  sequence: number;
  state: JobState;
  progress: number;
  message: string;
  created_at: string;
}

const apiBase = (import.meta.env.VITE_API_BASE ?? "").replace(/\/$/, "");

function apiPath(path: string): string {
  return `${apiBase}${path}`;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(apiPath(path), init);
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error(payload.detail || `Request failed (${response.status})`);
  }
  return response.json() as Promise<T>;
}

function accessToken(job: AnalysisJob): string {
  if (!job.access_token) throw new Error("This analysis session is no longer available in this browser.");
  return job.access_token;
}

function authorisedRequest<T>(path: string, job: AnalysisJob, init?: RequestInit): Promise<T> {
  return request<T>(path, {
    ...init,
    headers: { ...init?.headers, "X-Analysis-Token": accessToken(job) }
  });
}

function mediaUrl(path: string, job: AnalysisJob): string {
  const endpoint = new URL(apiPath(path), window.location.origin);
  endpoint.searchParams.set("access_token", accessToken(job));
  return endpoint.toString();
}

export async function createAnalysis(form: FormData): Promise<AnalysisJob> {
  return request<AnalysisJob>("/api/analyses", { method: "POST", body: form });
}

export async function getAnalysis(job: AnalysisJob): Promise<AnalysisJob> {
  const updated = await authorisedRequest<AnalysisJob>(`/api/analyses/${job.analysis_id}`, job);
  return { ...updated, access_token: accessToken(job) };
}

export async function getReport(job: AnalysisJob): Promise<CoachingReport> {
  const response = await authorisedRequest<{ report: CoachingReport }>(`/api/analyses/${job.analysis_id}/report`, job);
  return response.report;
}

export async function deleteAnalysis(job: AnalysisJob): Promise<AnalysisJob> {
  return authorisedRequest<AnalysisJob>(`/api/analyses/${job.analysis_id}`, job, { method: "DELETE" });
}

export async function getMixedDoublesSetup(job: AnalysisJob): Promise<MixedDoublesSetup> {
  return authorisedRequest<MixedDoublesSetup>(`/api/analyses/${job.analysis_id}/setup`, job);
}

export async function submitMixedDoublesSetup(
  job: AnalysisJob,
  payload: {
    learner_track_id: string;
    partner_track_id: string;
    court_corners: Record<string, { x: number; y: number }>;
  },
): Promise<AnalysisJob> {
  const updated = await authorisedRequest<AnalysisJob>(`/api/analyses/${job.analysis_id}/setup`, job, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return { ...updated, access_token: accessToken(job) };
}

export function subscribeToJob(
  job: AnalysisJob,
  onEvent: (event: JobEvent) => void,
  onError: (error: Event) => void
): () => void {
  const endpoint = new URL(apiPath(`/api/analyses/${job.analysis_id}/events`), window.location.origin);
  endpoint.protocol = endpoint.protocol === "https:" ? "wss:" : "ws:";
  endpoint.searchParams.set("access_token", accessToken(job));
  const socket = new WebSocket(endpoint.toString());
  socket.onmessage = (message) => onEvent(JSON.parse(message.data) as JobEvent);
  socket.onerror = onError;
  return () => socket.close();
}

export function studentFrameUrl(job: AnalysisJob, frameId: string): string {
  return mediaUrl(`/api/analyses/${job.analysis_id}/frames/${frameId}`, job);
}

export function studentSegmentUrl(job: AnalysisJob, segmentId: string): string {
  return mediaUrl(`/api/analyses/${job.analysis_id}/segments/${segmentId}`, job);
}

export function setupFrameUrl(path: string, job: AnalysisJob): string {
  return mediaUrl(path, job);
}

export function coachReferenceUrl(url: string, job: AnalysisJob): string {
  return mediaUrl(url, job);
}

export function coachReferenceClipUrl(url: string, job: AnalysisJob): string {
  return mediaUrl(url, job);
}
