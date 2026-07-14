import { studentFrameUrl, type AnalysisJob, type FrameRef } from "../../api/client";

const phaseLabels: Record<string, string> = { preparation: "准备", start: "启动", arrival: "到位", top_elbow: "顶肘与架拍", contact_window: "击球窗口", follow_through: "随挥", recovery: "回位" };

interface PhaseRailProps { job: AnalysisJob; frames: FrameRef[]; activeFrameId?: string; onSelect: (frame: FrameRef) => void; }

export function PhaseRail({ job, frames, activeFrameId, onSelect }: PhaseRailProps) {
  return <section className="phase-rail"><div className="phase-rail-head"><strong>三帧动作总览</strong><span>用于定位；完整教学请看下方连续片段</span></div><div className="phase-list summary-list">{frames.map((frame) => <button key={frame.frame_id} className={`phase-chip summary-chip ${activeFrameId === frame.frame_id ? "active" : ""}`} onClick={() => onSelect(frame)}><img src={frame.media_url ?? studentFrameUrl(job, frame.frame_id)} alt={`${phaseLabels[frame.phase] ?? frame.phase}学员摘要帧`} /><b>{phaseLabels[frame.phase] ?? frame.phase}</b><time>{(frame.timestamp_ms / 1000).toFixed(2)}s</time></button>)}</div></section>;
}
