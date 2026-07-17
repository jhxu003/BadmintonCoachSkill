import { CircleDotDashed, Orbit, UsersRound } from "lucide-react";

import { studentFrameUrl, type AnalysisJob, type CoachingReport, type RallyFrame } from "../../api/client";
import { contactWindowLabel, RALLY_MODULES } from "./rallyModel";


interface RallyEvidenceTimelineProps {
  job: AnalysisJob;
  report: CoachingReport;
  activeFrameId?: string;
  onSelect: (frame: RallyFrame) => void;
}

export function RallyEvidenceTimeline({ job, report, activeFrameId, onSelect }: RallyEvidenceTimelineProps) {
  const frames = new Map((report.rally_frames ?? []).map((frame) => [frame.module, frame]));
  const contacts = report.multiplayer_evidence?.contact_candidates ?? [];
  return (
    <section className="rally-evidence" aria-label="混双七模块回合证据">
      <header className="rally-evidence-head">
        <div><p className="eyebrow">完整回合证据</p><h2>七个模块，不把一拍当成全部。</h2></div>
        <div className="rally-metrics"><span><UsersRound size={15} />{report.multiplayer_evidence?.tracked_player_count ?? 0} 人轨迹</span><span><Orbit size={15} />{report.multiplayer_evidence?.shuttle_candidate_count ?? 0} 个羽球候选</span><span><CircleDotDashed size={15} />{contacts.length} 个触球窗口</span></div>
      </header>
      <div className="rally-module-track">
        {RALLY_MODULES.map((module, index) => {
          const frame = frames.get(module.id);
          return <button key={module.id} type="button" disabled={!frame} className={`rally-module ${frame?.frame_id === activeFrameId ? "active" : ""} ${frame ? "" : "missing"}`} onClick={() => frame && onSelect(frame)}>{frame ? <img src={studentFrameUrl(job, frame.frame_id)} alt="" /> : <span className="module-placeholder" />}<span className="module-copy"><small>{String(index + 1).padStart(2, "0")}</small><b>{module.short}</b><time>{frame ? `${(frame.timestamp_ms / 1000).toFixed(2)}s` : "证据不足"}</time></span></button>;
        })}
      </div>
      <div className="contact-windows">
        <b>触球候选窗口</b>
        {contacts.length ? contacts.slice(0, 8).map((contact) => <span key={contact.candidate_id}>{contactWindowLabel(contact)}</span>) : <span>当前回合没有足够的羽球方向变化证据，系统不会补造触球点。</span>}
      </div>
    </section>
  );
}
