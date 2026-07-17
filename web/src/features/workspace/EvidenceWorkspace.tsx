import { useMemo, useState } from "react";
import { ChevronLeft, CircleAlert, Gauge, Trash2 } from "lucide-react";

import { deleteAnalysis, indexCoachReferences, studentFrameUrl, type AnalysisJob, type CoachingReport, type FrameRef } from "../../api/client";
import { ActionPackageTimeline } from "./ActionPackageTimeline";
import { FrameComparison } from "./FrameComparison";
import { PhaseRail } from "./PhaseRail";
import { RallyEvidenceTimeline } from "./RallyEvidenceTimeline";
import { evidenceTokenLabel, rallyModuleTitle } from "./rallyModel";

interface EvidenceWorkspaceProps {
  job: AnalysisJob;
  report: CoachingReport;
  onBack: () => void;
  onDeleted: () => void;
}

export function EvidenceWorkspace({ job, report, onBack, onDeleted }: EvidenceWorkspaceProps) {
  const [selectedIssueId, setSelectedIssueId] = useState(report.issues[0]?.issue_id);
  const [activeFrameId, setActiveFrameId] = useState(report.frame_refs[0]?.frame_id);
  const [activeSegmentId, setActiveSegmentId] = useState(report.action_package?.[0]?.segment_id);
  const selectedIssue = report.issues.find((issue) => issue.issue_id === selectedIssueId);
  const evidence = report.issue_evidence.find((item) => item.issue_id === selectedIssueId);
  const studentFrames = useMemo(() => new Map(report.frame_refs.map((frame) => [frame.frame_id, frame])), [report.frame_refs]);
  const coachFrames = useMemo(() => indexCoachReferences(report.coach_references), [report.coach_references]);
  const framesForIssue = evidence?.student_frame_ids.map((id) => studentFrames.get(id)).filter(Boolean) as FrameRef[] | undefined;
  const isMixedDoubles = Boolean(report.rally_frames?.length);
  const visibleFrames = isMixedDoubles ? report.frame_refs : framesForIssue?.length ? framesForIssue : report.frame_refs;
  const activeFrame = visibleFrames.find((frame) => frame.frame_id === activeFrameId) ?? visibleFrames[0];
  const activeRallyFrame = report.rally_frames?.find((frame) => frame.frame_id === activeFrame?.frame_id);
  const comparisonRallyFrame = report.rally_frames?.find((frame) => evidence?.student_frame_ids.includes(frame.frame_id));
  const retakeMessage = report.retake_guidance ?? (report.missing_evidence.length ? `仍需补拍：${report.missing_evidence.join("、")}` : undefined);

  async function remove(): Promise<void> {
    await deleteAnalysis(job);
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
        <div><p className="eyebrow">{report.coach_name}体系 / 视频证据诊断</p><h1>{job.action_hint === "mixed_doubles" ? "混双完整回合" : job.action_hint ?? "羽毛球动作"}</h1></div>
        <div className="case-stat"><Gauge size={17} /><span>诊断可信度：{report.confidence}</span></div>
      </section>
      {isMixedDoubles ? <RallyEvidenceTimeline job={job} report={report} activeFrameId={activeFrame?.frame_id} onSelect={(frame) => setActiveFrameId(frame.frame_id)} /> : <><PhaseRail job={job} frames={report.frame_refs} activeFrameId={activeFrame?.frame_id} onSelect={(frame) => setActiveFrameId(frame.frame_id)} /><ActionPackageTimeline job={job} segments={report.action_package ?? []} missingPhases={report.action_package_missing_phases} activeSegmentId={activeSegmentId} onSelect={(segment) => setActiveSegmentId(segment.segment_id)} /></>}
      <div className="workspace-grid">
        <section className="student-review">
          <div className="panel-top"><div><p className="eyebrow">{isMixedDoubles ? "当前回合模块" : "当前学员帧"}</p><h2>{activeRallyFrame ? rallyModuleTitle(activeRallyFrame.module) : activeFrame?.phase ?? "等待关键帧"}</h2></div>{activeFrame && <span>{(activeFrame.timestamp_ms / 1000).toFixed(2)}s</span>}</div>
          {activeFrame ? <img className="student-image" src={activeFrame.media_url ?? studentFrameUrl(job, activeFrame.frame_id)} alt="学员当前阶段关键帧" /> : <div className="video-empty">当前视频没有可用关键帧</div>}
          <p className="student-limits">{activeRallyFrame?.caption}{activeRallyFrame && activeFrame?.limitations.length ? " · " : ""}{activeFrame?.limitations.map(evidenceTokenLabel).join("；")}</p>
        </section>
        <aside className="issue-panel">
          <p className="eyebrow">优先纠正项</p>
          {report.issues.map((issue) => <button key={issue.issue_id} className={`issue-row ${issue.issue_id === selectedIssueId ? "selected" : ""}`} onClick={() => { setSelectedIssueId(issue.issue_id); const first = report.issue_evidence.find((item) => item.issue_id === issue.issue_id)?.student_frame_ids[0]; if (first) setActiveFrameId(first); }}><b>{issue.issue}</b><span>{issue.evidence[0] ?? "等待可见证据"}</span></button>)}
          {retakeMessage && <div className="retake-note"><CircleAlert size={16} />{retakeMessage}</div>}
          <div className="drill-card"><p className="eyebrow">本次训练</p><b>{selectedIssue?.drills[0]?.name ?? "暂无训练动作"}</b><span>{selectedIssue?.drills[0]?.dosage}</span><p>{selectedIssue?.retest_metrics[0]}</p></div>
        </aside>
      </div>
      <FrameComparison job={job} evidence={evidence} studentFrames={studentFrames} coachFrames={coachFrames} actionPackage={report.action_package ?? []} comparisonLabel={comparisonRallyFrame ? rallyModuleTitle(comparisonRallyFrame.module) : undefined} />
    </main>
  );
}
