import { useMemo, useState } from "react";
import { AlertTriangle, CheckCircle2, ChevronLeft, Clock3, ImageOff, ShieldCheck, Target, Trash2 } from "lucide-react";

import { deleteAnalysis, studentFrameUrl, type AgentActionUnit, type AgentVideoCoachingReport, type AnalysisJob, type LessonFocusItem } from "../../api/client";
import { VideoLessonCard } from "../demonstration/DemonstrationWorkspace";
import { ActionPackageTimeline } from "./ActionPackageTimeline";
import { evidenceTokenLabel } from "./rallyModel";

interface AgentVideoWorkspaceProps {
  job: AnalysisJob;
  report: AgentVideoCoachingReport;
  onBack: () => void;
  onDeleted: () => void;
}

const actionLabels: Record<string, string> = {
  high_clear: "后场高远球",
  smash: "杀球",
  drop: "吊球",
  drive: "平抽挡",
  net: "网前技术",
  rear_footwork: "后场步法",
  front_footwork: "前场步法",
  backhand: "反手",
  serve_receive: "发接发",
  doubles: "双打回合",
  match_transfer: "实战迁移",
};

const statusLabels: Record<AgentActionUnit["status"], string> = {
  teaching_ready: "可开始练习",
  needs_retake: "需要补拍",
  unsupported_action: "当前没有对应教学",
  requires_dedicated_setup: "需要多人回合设置",
};

function formatWindow(startMs: number, endMs: number): string {
  return `${(startMs / 1000).toFixed(1)}–${(endMs / 1000).toFixed(1)} 秒`;
}

function FocusCard({ item, later = false }: { item: LessonFocusItem; later?: boolean }) {
  return <article className={`agent-focus-card${later ? " later" : ""}`}>
    <div className="agent-focus-icon">{later ? <CheckCircle2 size={16} /> : <Target size={18} />}</div>
    <div>
      <p className="eyebrow">{later ? "下一步" : "现在先练"}</p>
      <h3>{item.title_zh}</h3>
      <p className="agent-focus-evidence"><b>画面依据</b>{item.visible_evidence_zh.join("；") || "已验证的连续阶段证据"}</p>
      <p className="agent-focus-correction">{item.correction_zh}</p>
      {item.drill ? <p className="agent-focus-drill"><b>{item.drill.title_zh}</b><span>{item.drill.dosage_zh}</span></p> : null}
      <p className="agent-focus-retest">复测：{item.retest_zh}</p>
    </div>
  </article>;
}

function RetakeCard({ unit }: { unit: AgentActionUnit }) {
  const reason = unit.reasons.map(evidenceTokenLabel).filter(Boolean).join("；");
  return <article className="agent-retake-card">
    <AlertTriangle size={19} aria-hidden="true" />
    <div><div><b>{actionLabels[unit.action] ?? unit.action}</b><span>{formatWindow(unit.start_ms, unit.end_ms)}</span></div><p>{unit.retake_guidance_zh ?? "当前片段无法安全给出教学结论。"}</p>{reason && <small>{reason}</small>}</div>
  </article>;
}

export function AgentVideoWorkspace({ job, report, onBack, onDeleted }: AgentVideoWorkspaceProps) {
  const readyUnits = useMemo(() => report.action_units.filter((unit) => unit.status === "teaching_ready" && unit.coaching_plan), [report.action_units]);
  const [selectedId, setSelectedId] = useState(readyUnits[0]?.segment_id ?? "");
  const [activeSegmentId, setActiveSegmentId] = useState(readyUnits[0]?.action_package[0]?.segment_id ?? "");
  const selected = readyUnits.find((unit) => unit.segment_id === selectedId) ?? readyUnits[0];
  const retakeUnits = report.action_units.filter((unit) => unit.status !== "teaching_ready");
  const focus = selected?.coaching_plan?.lesson_focus;
  const activeFrame = selected?.student_frames[0];
  const selectedPackage = selected?.action_package ?? [];

  async function remove(): Promise<void> {
    await deleteAnalysis(job);
    onDeleted();
  }

  return <main className="agent-workspace">
    <header className="agent-workspace-header">
      <button className="icon-text-button" type="button" onClick={onBack}><ChevronLeft size={17} aria-hidden="true" /> 返回上传</button>
      <div className="brand-lockup"><span className="brand-mark" />BadmintonCoach</div>
      <button className="danger-button" type="button" onClick={() => void remove()}><Trash2 size={15} aria-hidden="true" /> 删除本次视频</button>
    </header>

    <section className="agent-case-head">
      <div><p className="eyebrow">Learner video coaching</p><h1>把可看见的过程，变成下一次练习。</h1><p>系统只展示已通过连续画面与教练规则验证的片段；其余内容会保留为补拍建议。</p></div>
      <div className="agent-privacy"><ShieldCheck size={17} aria-hidden="true" /><span>私有媒体仅本次会话可见，24 小时后删除</span></div>
    </section>

    {readyUnits.length ? <section className="agent-unit-rail" aria-labelledby="agent-unit-title">
      <div className="agent-section-head"><div><p className="eyebrow">已验证动作片段</p><h2 id="agent-unit-title">选择一个片段，逐项练习</h2></div><span><Clock3 size={15} aria-hidden="true" />{readyUnits.length} 个可教学片段</span></div>
      <div className="agent-unit-buttons" role="list" aria-label="可教学动作片段">
        {readyUnits.map((unit, index) => <button key={unit.segment_id} type="button" role="listitem" className={unit.segment_id === selected?.segment_id ? "selected" : ""} aria-current={unit.segment_id === selected?.segment_id ? "true" : undefined} onClick={() => { setSelectedId(unit.segment_id); setActiveSegmentId(unit.action_package[0]?.segment_id ?? ""); }}><span>{String(index + 1).padStart(2, "0")}</span><b>{actionLabels[unit.action] ?? unit.action}</b><small>{formatWindow(unit.start_ms, unit.end_ms)}</small><em>{statusLabels[unit.status]}</em></button>)}
      </div>
    </section> : <section className="agent-empty-state"><AlertTriangle size={32} aria-hidden="true" /><h2>先补齐完整动作，再安排练习</h2><p>{report.retake_guidance_zh ?? "这段视频没有通过高置信动作分段与连续证据检查。请连续拍下准备、移动、挥拍、落地和回位。"}</p></section>}

    {selected && selected.coaching_plan ? <>
      <section className="agent-focus-section" aria-labelledby="agent-focus-title">
        <div className="agent-section-head"><div><p className="eyebrow">本段练习</p><h2 id="agent-focus-title">{actionLabels[selected.action] ?? selected.action} · 先完成一件事</h2></div><span>教练视角：{selected.coaching_plan.coach_name}</span></div>
        {focus ? <><FocusCard item={focus.now} />{focus.next.length ? <div className="agent-next-steps">{focus.next.slice(0, 2).map((item) => <FocusCard key={item.issue_id} item={item} later />)}</div> : null}</> : <div className="agent-empty-state compact"><ImageOff size={25} aria-hidden="true" /><p>没有可发布的练习重点；请依据补拍建议重新录制。</p></div>}
      </section>

      <section className="agent-evidence-grid" aria-label="本段学员连续证据">
        <article className="agent-student-frame"><div className="agent-panel-head"><p className="eyebrow">本段学员画面</p><span>{selected.observation_confidence === "high" ? "已通过可见性验证" : "证据有限"}</span></div>{activeFrame ? <img src={activeFrame.media_url ?? studentFrameUrl(job, activeFrame.frame_id)} alt={`${actionLabels[selected.action] ?? selected.action}的学员阶段画面`} /> : <div className="agent-empty-state compact"><ImageOff size={25} aria-hidden="true" /><p>本段没有可展示的阶段画面。</p></div>}</article>
        <article className="agent-boundary-card"><ShieldCheck size={20} aria-hidden="true" /><h3>本段不会猜测</h3><p>精确触球、拍面角度、握拍压力、力量、真实内旋、三维运动学与对手意图；画面不足时只建议补拍。</p></article>
      </section>
      <ActionPackageTimeline job={job} segments={selectedPackage} missingPhases={selected.action_package_missing_phases} activeSegmentId={activeSegmentId} onSelect={(segment) => setActiveSegmentId(segment.segment_id)} />

      {selected.coaching_plan.video_lessons.length ? <section className="demo-reference-section agent-coach-media"><div className="section-heading"><div><p className="eyebrow">同主题正确示范</p><h2>只看与当前训练重点绑定的教练动作</h2></div></div><div className="video-lesson-list">{selected.coaching_plan.video_lessons.map((lesson) => <VideoLessonCard key={lesson.lesson_id} job={job} lesson={lesson} />)}</div></section> : <section className="agent-media-gap"><ImageOff size={22} aria-hidden="true" /><p>这个训练重点当前没有可用的同主题连续教练示范；不会用其他动作或来源替代。</p></section>}
    </> : null}

    {retakeUnits.length ? <section className="agent-recapture-section" aria-labelledby="recapture-title"><div className="agent-section-head"><div><p className="eyebrow">未发布教学的片段</p><h2 id="recapture-title">这些片段需要补拍或单独设置</h2></div><span>不把不确定当结论</span></div><div className="agent-retake-list">{retakeUnits.map((unit) => <RetakeCard key={unit.segment_id} unit={unit} />)}</div></section> : null}

    <section className="agent-limitations"><h2>证据边界</h2><ul>{report.limitations.map((item) => <li key={item}>{evidenceTokenLabel(item)}</li>)}</ul></section>
  </main>;
}
