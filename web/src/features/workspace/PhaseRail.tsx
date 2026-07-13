import type { FrameRef } from "../../api/client";

const phaseLabels: Record<string, string> = { preparation: "准备", start: "启动", arrival: "到位", top_elbow: "顶肘与架拍", contact_window: "击球窗口", follow_through: "随挥", recovery: "回位" };

interface PhaseRailProps { frames: FrameRef[]; activeFrameId?: string; onSelect: (frame: FrameRef) => void; }

export function PhaseRail({ frames, activeFrameId, onSelect }: PhaseRailProps) {
  return <section className="phase-rail"><div className="phase-rail-head"><strong>动作阶段轨</strong><span>只显示有可见证据的阶段</span></div><div className="phase-list">{frames.map((frame) => <button key={frame.frame_id} className={`phase-chip ${activeFrameId === frame.frame_id ? "active" : ""}`} onClick={() => onSelect(frame)}><b>{phaseLabels[frame.phase] ?? frame.phase}</b><time>{(frame.timestamp_ms / 1000).toFixed(2)}s</time></button>)}</div></section>;
}
