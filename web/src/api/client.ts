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
  title?: string;
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
  coach_references: FrameRef[];
  missing_evidence: string[];
}

export interface JobEvent {
  sequence: number;
  state: JobState;
  progress: number;
  message: string;
  created_at: string;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, init);
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error(payload.detail || `Request failed (${response.status})`);
  }
  return response.json() as Promise<T>;
}

export async function createAnalysis(form: FormData): Promise<AnalysisJob> {
  return request<AnalysisJob>("/api/analyses", { method: "POST", body: form });
}

export async function getAnalysis(analysisId: string): Promise<AnalysisJob> {
  return request<AnalysisJob>(`/api/analyses/${analysisId}`);
}

export async function getReport(analysisId: string): Promise<CoachingReport> {
  const response = await request<{ report: CoachingReport }>(`/api/analyses/${analysisId}/report`);
  return response.report;
}

export async function deleteAnalysis(analysisId: string): Promise<AnalysisJob> {
  return request<AnalysisJob>(`/api/analyses/${analysisId}`, { method: "DELETE" });
}

export function subscribeToJob(
  analysisId: string,
  onEvent: (event: JobEvent) => void,
  onError: (error: Event) => void
): () => void {
  const protocol = window.location.protocol === "https:" ? "wss" : "ws";
  const socket = new WebSocket(`${protocol}://${window.location.host}/api/analyses/${analysisId}/events`);
  socket.onmessage = (message) => onEvent(JSON.parse(message.data) as JobEvent);
  socket.onerror = onError;
  return () => socket.close();
}

export function studentFrameUrl(analysisId: string, frameId: string): string {
  return `/api/analyses/${analysisId}/frames/${frameId}`;
}
