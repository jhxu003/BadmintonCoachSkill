import { useState } from "react";
import { AlertTriangle, CheckCircle2, ChevronRight, ClipboardCheck, ImageOff, ShieldCheck, Target } from "lucide-react";

import { deleteAnalysis, type AnalysisJob, type CoachLens, type CoachingPlanReport, type LessonFocusItem } from "../../api/client";
import { VideoLessonCard } from "../demonstration/DemonstrationWorkspace";
import { evidenceTokenLabel } from "../workspace/rallyModel";

interface CoachingPlanWorkspaceProps {
  job: AnalysisJob;
  report: CoachingPlanReport;
  onBack: () => void;
  onSwitchCoach: (coachId: string) => Promise<void>;
}

function FocusItem({ item, later = false }: { item: LessonFocusItem; later?: boolean }) {
  return (
    <article className={`focus-item${later ? " later" : ""}`}>
      <div className="focus-item-mark">{later ? <ChevronRight size={18} /> : <Target size={18} />}</div>
      <div>
        <p className="eyebrow">{later ? "下一项" : "现在先练"}</p>
        <h3>{item.title_zh}</h3>
        <p className="focus-observation"><b>本次依据</b>{item.visible_evidence_zh.join("；")}</p>
        <p className="focus-correction">{item.correction_zh}</p>
        {item.drill ? <div className="focus-drill"><b>{item.drill.title_zh}</b><span>{item.drill.dosage_zh}</span></div> : null}
        <p className="focus-retest"><CheckCircle2 size={15} />复测：{item.retest_zh}</p>
      </div>
    </article>
  );
}

function LensButton({ lens, onSwitch, switching }: { lens: CoachLens; onSwitch: (coachId: string) => void; switching: boolean }) {
  return (
    <button
      className={`coach-lens${lens.selected ? " selected" : ""}`}
      type="button"
      disabled={lens.selected || switching}
      onClick={() => onSwitch(lens.coach_id)}
      aria-current={lens.selected ? "true" : undefined}
    >
      <span>{lens.selected ? "当前视角" : "切换视角"}</span>
      <b>{lens.coach_name}</b>
      <small>{lens.reason_zh}</small>
    </button>
  );
}

export function CoachingPlanWorkspace({ job, report, onBack, onSwitchCoach }: CoachingPlanWorkspaceProps) {
  const [switching, setSwitching] = useState(false);

  async function close(): Promise<void> {
    await deleteAnalysis(job).catch(() => undefined);
    onBack();
  }

  async function switchCoach(coachId: string): Promise<void> {
    setSwitching(true);
    try {
      await onSwitchCoach(coachId);
    } finally {
      setSwitching(false);
    }
  }

  const focus = report.lesson_focus;
  const topic = focus?.now.topic_unit;

  return (
    <main className="demo-workspace coaching-plan-workspace">
      <header className="demo-header coaching-plan-header">
        <div>
          <p className="eyebrow">这一节怎么练</p>
          <h1>{report.coach_name}的教学视角</h1>
          <p>{report.recommendation_mode === "auto_recommended_teaching_lens" ? "系统已根据当前可见观察推荐这一视角；它不是对教练的排名。你可以切换到其他兼容视角比较。" : "这是你指定的教学视角；下方仍保留当前动作可用的其他视角。"}</p>
        </div>
        <button className="secondary-button" type="button" onClick={() => void close()}>返回结构化输入</button>
      </header>

      <section className="coaching-focus-section" aria-labelledby="focus-title">
        <div className="section-heading">
          <div><p className="eyebrow">练习优先级</p><h2 id="focus-title">不要同时改完所有问题</h2></div>
          <span className="evidence-chip"><ClipboardCheck size={15} />结构化观察输入</span>
        </div>
        {focus ? <>
          <FocusItem item={focus.now} />
          {focus.next.length ? <div className="later-queue"><div><p className="eyebrow">等这一项稳定后</p><h3>再依次加入下面两项</h3></div>{focus.next.map((item) => <FocusItem key={item.issue_id} item={item} later />)}</div> : null}
        </> : <div className="demo-empty coaching-retake"><AlertTriangle size={30} /><h3>先补齐可见过程，再安排练习</h3><p>{report.retake_guidance_zh ?? "Skill 不会在证据不足时强行归因。请补拍准备、移动、击球后收拍与回位的连续过程。"}</p></div>}
      </section>

      <section className="coaching-topic-section" aria-labelledby="topic-title">
        <div className="section-heading"><div><p className="eyebrow">教练知识与示范边界</p><h2 id="topic-title">{topic ? topic.topic_name_zh : "当前没有可确认的主题单元"}</h2></div><span className="evidence-chip"><ShieldCheck size={15} />主题绑定</span></div>
        {topic ? <div className="topic-copy"><p>{topic.learning_goal_zh}</p><small>{topic.media_notice_zh}</small></div> : <p className="topic-copy muted">当前只能保留证据不足的结论，不借用其他动作、其他来源的片段来补示范。</p>}
      </section>

      <section className="coach-lens-section" aria-labelledby="lens-title">
        <div className="section-heading"><div><p className="eyebrow">教练视角</p><h2 id="lens-title">推荐一个，也可以切换比较</h2></div></div>
        <div className="coach-lens-list">{report.coach_lenses.map((lens) => <LensButton key={lens.coach_id} lens={lens} switching={switching} onSwitch={(coachId) => void switchCoach(coachId)} />)}</div>
      </section>

      {report.video_lesson_status === "available" ? <section className="demo-reference-section video-lesson-section"><div className="section-heading"><div><p className="eyebrow">同主题的正确动作连续示范</p><h2>先看全程，再按阶段练习</h2></div></div><div className="video-lesson-list">{report.video_lessons.map((lesson) => <VideoLessonCard key={lesson.lesson_id} job={job} lesson={lesson} />)}</div></section> : focus ? <section className="demo-reference-section"><div className="demo-empty"><ImageOff size={30} /><h3>这个主题暂时没有可用的连续示范</h3><p>系统仍可给出主题内的练习与复测；但没有经过该主题审核的完整教练示范，就不会拿别的动作或错误示范替代。</p></div></section> : null}

      {report.diagnosis.missing_evidence.length ? <section className="demo-boundary"><h2>仍需补充的观察</h2><ul>{report.diagnosis.missing_evidence.map((item) => <li key={item}>{evidenceTokenLabel(item)}</li>)}</ul></section> : null}
      <section className="demo-boundary"><h2>证据边界</h2><ul>{report.limitations.map((item) => <li key={item}>{evidenceTokenLabel(item)}</li>)}</ul></section>
      <details className="diagnostic-trace"><summary>完整匹配轨迹（{report.teaching_sequence.length} 项技术标识）</summary><ol>{report.teaching_sequence.map((step) => <li key={step.issue_id}>{step.issue_id}</li>)}</ol></details>
    </main>
  );
}
