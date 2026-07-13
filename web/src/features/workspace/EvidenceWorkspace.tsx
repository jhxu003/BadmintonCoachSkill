import { useMemo, useState } from "react";
import { ChevronLeft, CircleAlert, Gauge, Trash2 } from "lucide-react";

import { deleteAnalysis, type AnalysisJob, type CoachingReport, type FrameRef } from "../../api/client";
import { FrameComparison } from "./FrameComparison";
import { PhaseRail } from "./PhaseRail";

interface EvidenceWorkspaceProps {
  job: AnalysisJob;
  report: CoachingReport;
  onBack: () => void;
  onDeleted: () => void;
}

export function EvidenceWorkspace({ job, report, onBack, onDeleted }: EvidenceWorkspaceProps) {
  const [selectedIssueId, setSelectedIssueId] = useState(report.issues[0]?.issue_id);
  const [activeFrameId, setActiveFrameId] = useState(report.frame_refs[0]?.frame_id);
  const selectedIssue = report.issues.find((issue) => issue.issue_id === selectedIssueId);
  const evidence = report.issue_evidence.find((item) => item.issue_id === selectedIssueId);
  const studentFrames = useMemo(() => new Map(report.frame_refs.map((frame) => [frame.frame_id, frame])), [report.frame_refs]);
  const coachFrames = useMemo(() => new Map(report.coach_references.map((frame) => [frame.frame_id, frame])), [report.coach_references]);
  const framesForIssue = evidence?.student_frame_ids.map((id) => studentFrames.get(id)).filter(Boolean) as FrameRef[] | undefined;
  const visibleFrames = framesForIssue?.length ? framesForIssue : report.frame_refs;
  const activeFrame = visibleFrames.find((frame) => frame.frame_id === activeFrameId) ?? visibleFrames[0];
  const retakeMessage = report.retake_guidance ?? (report.missing_evidence.length ? `仍需补拍：${report.missing_evidence.join("、")}` : undefined);

  async function remove(): Promise<void> {
    await deleteAnalysis(job.analysis_id);
    onDeleted();
  }

  return (
    <main className="workspace">
      <header className="workspace-topbar">
        <button className="icon-text-button" onClick={onBack}><ChevronLeft size={17} /> 返回</button>
        <div className="brand-lockup"><span className="brand-mark" />BadmintonCoach</div>
        <button className="danger-button" onClick={remove}><Trash2 size={15} /> 删除本次视频</button>
      </header>
      <section className="case-head">
        <div><p className="eyebrow">{report.coach_name}体系 / 视频证据诊断</p><h1>{job.action_hint ?? "羽毛球动作"}</h1></div>
        <div className="case-stat"><Gauge size={17} /><span>诊断可信度：{report.confidence}</span></div>
      </section>
      <PhaseRail frames={visibleFrames} activeFrameId={activeFrame?.frame_id} onSelect={(frame) => setActiveFrameId(frame.frame_id)} />
      <div className="workspace-grid">
        <section className="student-review">
          <div className="panel-top"><div><p className="eyebrow">当前学员帧</p><h2>{activeFrame?.phase ?? "等待关键帧"}</h2></div>{activeFrame && <span>{(activeFrame.timestamp_ms / 1000).toFixed(2)}s</span>}</div>
          {activeFrame ? <img className="student-image" src={activeFrame.media_url ?? `/api/analyses/${job.analysis_id}/frames/${activeFrame.frame_id}`} alt="学员当前阶段关键帧" /> : <div className="video-empty">当前视频没有可用关键帧</div>}
          <p className="student-limits">{activeFrame?.limitations.join("；")}</p>
        </section>
        <aside className="issue-panel">
          <p className="eyebrow">优先纠正项</p>
          {report.issues.map((issue) => <button key={issue.issue_id} className={`issue-row ${issue.issue_id === selectedIssueId ? "selected" : ""}`} onClick={() => { setSelectedIssueId(issue.issue_id); const first = report.issue_evidence.find((item) => item.issue_id === issue.issue_id)?.student_frame_ids[0]; if (first) setActiveFrameId(first); }}><b>{issue.issue}</b><span>{issue.evidence[0] ?? "等待可见证据"}</span></button>)}
          {retakeMessage && <div className="retake-note"><CircleAlert size={16} />{retakeMessage}</div>}
          <div className="drill-card"><p className="eyebrow">本次训练</p><b>{selectedIssue?.drills[0]?.name ?? "暂无训练动作"}</b><span>{selectedIssue?.drills[0]?.dosage}</span><p>{selectedIssue?.retest_metrics[0]}</p></div>
        </aside>
      </div>
      <FrameComparison analysisId={job.analysis_id} evidence={evidence} studentFrames={studentFrames} coachFrames={coachFrames} />
    </main>
  );
}
