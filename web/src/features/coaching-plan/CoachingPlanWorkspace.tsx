import { AlertTriangle, ClipboardCheck, ImageOff, ShieldCheck } from "lucide-react";

import { deleteAnalysis, type AnalysisJob, type CoachingPlanReport } from "../../api/client";
import { VideoLessonCard } from "../demonstration/DemonstrationWorkspace";
import { evidenceTokenLabel } from "../workspace/rallyModel";

interface CoachingPlanWorkspaceProps {
  job: AnalysisJob;
  report: CoachingPlanReport;
  onBack: () => void;
}

export function CoachingPlanWorkspace({ job, report, onBack }: CoachingPlanWorkspaceProps) {
  async function close(): Promise<void> {
    await deleteAnalysis(job).catch(() => undefined);
    onBack();
  }

  return (
    <main className="demo-workspace coaching-plan-workspace">
      <header className="demo-header">
        <div><p className="eyebrow">Structured coaching plan</p><h1>{report.coach_name} · {report.query.action}</h1><p>{report.notice}</p></div>
        <button className="secondary-button" type="button" onClick={() => void close()}>返回结构化输入</button>
      </header>

      <section className="teaching-route-section">
        <div className="section-heading"><div><p className="eyebrow">教学顺序</p><h2>先改最影响动作链的一个瓶颈</h2></div><span className="evidence-chip"><ClipboardCheck size={15} />结构化观察输入</span></div>
        {report.teaching_sequence.length ? <div className="teaching-sequence">{report.teaching_sequence.map((step) => <article key={step.issue_id} className="teaching-sequence-card"><span>{String(step.rank).padStart(2, "0")}</span><div><h3>{step.issue}</h3><p>{step.correction_principle}</p>{step.drills.length ? <ul>{step.drills.map((drill) => <li key={drill.drill_id ?? drill.name}><b>{drill.name}</b> · {drill.dosage}</li>)}</ul> : null}<small>复测：{step.retest_metrics.join("；") || "等待补充可复测条件"}</small></div></article>)}</div> : <div className="demo-empty"><AlertTriangle size={30} /><h3>当前观察没有确定性问题</h3><p>Skill 不会强行归因。请补充可见阶段、机位或由视频 Agent 提供的结构化观察。</p></div>}
      </section>

      <section className="teaching-route-section">
        <div className="section-heading"><div><p className="eyebrow">教练体系</p><h2>用选定体系解释与练习</h2></div><span className="evidence-chip"><ShieldCheck size={15} />非官方公开资料研究整理</span></div>
        <div className="teaching-route-grid">{report.teaching_routes.map((route, index) => <article key={route.framework_id} className="teaching-route-card"><span>{String(index + 1).padStart(2, "0")}</span><h3>{route.name}</h3><p>{route.summary}</p><small>{route.framework_id} · {route.confidence}</small></article>)}</div>
      </section>

      {report.video_lesson_status === "available" ? <section className="demo-reference-section video-lesson-section"><div className="section-heading"><div><p className="eyebrow">正确动作连续示范</p><h2>先看完整动作，再按阶段练习</h2></div></div><div className="video-lesson-list">{report.video_lessons.map((lesson) => <VideoLessonCard key={lesson.lesson_id} job={job} lesson={lesson} />)}</div></section> : <section className="demo-reference-section"><div className="demo-empty"><ImageOff size={30} /><h3>该体系没有可靠的连续动作课</h3><p>系统仍提供体系、练习与复测，但不会用比赛、战术讲解、手势或不连续画面伪造正确动作示范。</p></div></section>}

      {report.diagnosis.missing_evidence.length ? <section className="demo-boundary"><h2>仍需补充的观察</h2><ul>{report.diagnosis.missing_evidence.map((item) => <li key={item}>{evidenceTokenLabel(item)}</li>)}</ul></section> : null}
      <section className="demo-boundary"><h2>证据边界</h2><ul>{report.limitations.map((item) => <li key={item}>{evidenceTokenLabel(item)}</li>)}</ul></section>
    </main>
  );
}
