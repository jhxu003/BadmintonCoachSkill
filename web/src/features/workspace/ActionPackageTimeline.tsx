import { Clapperboard, PlayCircle } from "lucide-react";

import { studentSegmentUrl, type ActionPackageSegment, type AnalysisJob } from "../../api/client";

const phaseLabels: Record<string, string> = {
  preparation: "启动与后退",
  start: "最后两步与制动",
  arrival: "引拍、侧身与起跳准备",
  top_elbow: "架拍",
  contact_window: "腾空与击球附近",
  follow_through: "随挥与落地",
  recovery: "回位",
};

const phaseOrder = ["preparation", "start", "arrival", "top_elbow", "contact_window", "follow_through", "recovery"];

interface ActionPackageTimelineProps {
  job: AnalysisJob;
  segments: ActionPackageSegment[];
  missingPhases?: string[];
  activeSegmentId?: string;
  onSelect: (segment: ActionPackageSegment) => void;
}

export function ActionPackageTimeline({ job, segments, missingPhases = [], activeSegmentId, onSelect }: ActionPackageTimelineProps) {
  const active = segments.find((segment) => segment.segment_id === activeSegmentId) ?? segments[0];
  const byPhase = new Map(segments.map((segment) => [segment.phase, segment]));

  return (
    <section className="action-package" aria-labelledby="action-package-title">
      <div className="action-package-head">
        <div><p className="eyebrow">完整动作包</p><h2 id="action-package-title">从启动到回位，按顺序看一次动作</h2></div>
        <span><Clapperboard size={16} /> 每段约 0.8 秒</span>
      </div>
      <div className="action-track" role="list" aria-label="动作包阶段">
        {phaseOrder.map((phase, index) => {
          const segment = byPhase.get(phase);
          const isActive = segment?.segment_id === active?.segment_id;
          return segment ? (
            <button key={phase} className={`action-stage ${isActive ? "active" : ""}`} onClick={() => onSelect(segment)} role="listitem">
              <span className="stage-number">{String(index + 1).padStart(2, "0")}</span><b>{phaseLabels[phase]}</b>
              <time>{(segment.anchor_ms / 1000).toFixed(2)}s</time>
            </button>
          ) : (
            <div key={phase} className="action-stage missing" role="listitem">
              <span className="stage-number">{String(index + 1).padStart(2, "0")}</span><b>{phaseLabels[phase]}</b>
              <small>{missingPhases.includes(phase) ? "证据不足，请重拍" : "本次未提取"}</small>
            </div>
          );
        })}
      </div>
      {active ? (
        <div className="action-playback">
          <video className="action-video" controls playsInline preload="metadata" src={active.media_url ?? studentSegmentUrl(job, active.segment_id)} />
          <div className="action-caption"><p className="eyebrow"><PlayCircle size={14} /> 正在查看</p><h3>{phaseLabels[active.phase] ?? active.phase}</h3><p>{active.caption}</p><span>{(active.start_ms / 1000).toFixed(2)}–{(active.end_ms / 1000).toFixed(2)}s · {active.limitations.join("；")}</span></div>
        </div>
      ) : (
        <div className="action-package-empty">本次没有足够的连续动作画面。请从启动、后退、挥拍到回位连续重拍。</div>
      )}
    </section>
  );
}
