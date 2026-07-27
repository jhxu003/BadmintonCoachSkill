import { useState } from "react";
import { ExternalLink, Film, ImageOff, PlayCircle, ShieldCheck } from "lucide-react";

import { coachReferenceClipUrl, coachReferenceUrl, deleteAnalysis, type AnalysisJob, type CoachDemonstrationReport, type CoachReference, type VideoLessonPackage } from "../../api/client";
import { evidenceTokenLabel } from "../workspace/rallyModel";

interface DemonstrationWorkspaceProps {
  job: AnalysisJob;
  report: CoachDemonstrationReport;
  onBack: () => void;
}

const phaseLabels: Record<string, string> = {
  preparation: "准备与启动姿态",
  start: "启动与动作建立",
  arrival: "到位与支撑",
  top_elbow: "架拍与顶肘阶段",
  contact_window: "加速与近似击球窗口",
  follow_through: "随挥、落地与衔接",
  recovery: "回位与下一拍准备",
};

const completenessLabels: Record<VideoLessonPackage["completeness"], string> = {
  complete_demonstration: "完整连续示范",
  partial_demonstration: "部分动作示范",
  static_explanation: "静态姿势讲解",
  concept_only: "原理讲解",
};

export function DemonstrationWorkspace({ job, report, onBack }: DemonstrationWorkspaceProps) {
  const lessons = report.video_lessons ?? [];
  async function close(): Promise<void> {
    await deleteAnalysis(job).catch(() => undefined);
    onBack();
  }

  return (
    <main className="demo-workspace">
      <header className="demo-header">
        <div><p className="eyebrow">Coach video lesson</p><h1>{report.coach_name} · {lessons.length ? "完整视频教学" : phaseLabels[report.query.phase ?? ""] ?? report.query.phase}</h1><p>{report.notice}</p></div>
        <button className="secondary-button" type="button" onClick={() => void close()}>返回示范库</button>
      </header>

      <section className="teaching-route-section">
        <div className="section-heading"><div><p className="eyebrow">Skill 教学路线</p><h2>先理解原则，再看动作画面</h2></div><span className="evidence-chip"><ShieldCheck size={15} />非官方公开资料研究整理</span></div>
        <div className="teaching-route-grid">
          {report.teaching_routes.map((route, index) => <article key={route.framework_id} className="teaching-route-card"><span>{String(index + 1).padStart(2, "0")}</span><h3>{route.name}</h3><p>{route.summary}</p><small>{route.framework_id} · {route.confidence}</small></article>)}
        </div>
      </section>

      {lessons.length ? <section className="demo-reference-section video-lesson-section"><div className="section-heading"><div><p className="eyebrow">每视频一个教学包</p><h2>先看完整动作，再按阶段学习</h2></div></div><div className="video-lesson-list">{lessons.map((lesson) => <VideoLessonCard key={lesson.lesson_id} job={job} lesson={lesson} />)}</div></section> : <section className="demo-reference-section"><div className="section-heading"><div><p className="eyebrow">同阶段教练参考</p><h2>关键帧看姿态，短片看过程</h2></div></div>{report.coach_references.length ? <div className="demo-reference-grid">{report.coach_references.map((reference) => <ReferenceCard key={reference.reference_id} job={job} reference={reference} />)}</div> : <div className="demo-empty"><ImageOff size={30} /><h3>当前目录没有可靠的视频教学包</h3><p>视频只包含部分或静态内容时不会拼接成完整动作。需要等待该动作完成连续示范复核。</p></div>}</section>}

      <section className="demo-boundary"><h2>证据边界</h2><ul>{report.limitations.map((item) => <li key={item}>{evidenceTokenLabel(item)}</li>)}</ul></section>
    </main>
  );
}

export function VideoLessonCard({ job, lesson }: { job: AnalysisJob; lesson: VideoLessonPackage }) {
  const [selectedStageId, setSelectedStageId] = useState(lesson.stages[0]?.stage_id ?? "");
  const selectedStage = lesson.stages.find((stage) => stage.stage_id === selectedStageId) ?? lesson.stages[0];
  const full = lesson.full_reference;
  return <article className="video-lesson-card">
    <div className="video-lesson-head"><div><div className="lesson-badges"><span>{completenessLabels[lesson.completeness]}</span><span className={lesson.review_status === "agent_reviewed" ? "reviewed" : "candidate"}>{lesson.review_status === "agent_reviewed" ? "动作包已复核" : "动作包待复核"}</span><span className={lesson.semantic_review_status === "agent_reviewed" ? "reviewed" : "candidate"}>{lesson.semantic_review_status === "agent_reviewed" ? "技术语义已复核" : "技术语义待复核"}</span></div><h3>{lesson.lesson_topic}</h3><div className="lesson-semantic-row"><span>技术：{lesson.action}</span><span>体系：{lesson.family_id}</span><span>路线：{lesson.taxonomy_path.join(" → ")}</span></div><p>{lesson.teaching_summary}</p><small className="lesson-source-title">来源标题：{lesson.title}</small></div>{full.source_jump_url && <a href={full.source_jump_url} target="_blank" rel="noreferrer">原视频 <ExternalLink size={13} /></a>}</div>
    <div className="lesson-full-media">{full.clip_media_url ? <video controls playsInline preload="metadata" src={coachReferenceClipUrl(full.clip_media_url, job)} /> : <div className="demo-empty"><ImageOff size={28} /><span>完整动作片段尚未生成</span></div>}<div><p className="eyebrow"><PlayCircle size={14} /> 连续动作</p><strong>动作 {(lesson.action_start_ms / 1000).toFixed(2)}–{(lesson.action_end_ms / 1000).toFixed(2)}s</strong><small>播放 {(lesson.clip_start_ms / 1000).toFixed(2)}–{(lesson.clip_end_ms / 1000).toFixed(2)}s，保留球路结果段</small><small>{lesson.limitations.map(evidenceTokenLabel).join("；")}</small></div></div>
    {lesson.stages.length ? <><div className="lesson-stage-rail">{lesson.stages.map((stage, index) => <button key={stage.stage_id} type="button" className={stage.stage_id === selectedStage?.stage_id ? "active" : ""} onClick={() => setSelectedStageId(stage.stage_id)}>{stage.reference.media_url ? <img src={coachReferenceUrl(stage.reference.media_url, job)} alt={`${stage.label}关键帧`} /> : <span className="stage-placeholder"><ImageOff size={20} /></span>}<b>{String(index + 1).padStart(2, "0")} · {stage.label}</b><small>{(stage.reference.timestamp_ms / 1000).toFixed(2)}s</small></button>)}</div>{selectedStage && <div className="lesson-stage-detail"><div>{selectedStage.reference.clip_media_url ? <video controls playsInline preload="metadata" src={coachReferenceClipUrl(selectedStage.reference.clip_media_url, job)} /> : selectedStage.reference.media_url ? <img src={coachReferenceUrl(selectedStage.reference.media_url, job)} alt={`${selectedStage.label}阶段`} /> : <div className="demo-empty"><ImageOff size={24} /></div>}</div><div><p className="eyebrow">{phaseLabels[selectedStage.phase] ?? selectedStage.phase}</p><h4>{selectedStage.label}</h4><ul>{selectedStage.teaching_points.map((point) => <li key={point}>{point}</li>)}</ul><p><b>可见事实：</b>{selectedStage.reference.visible_facts.map(evidenceTokenLabel).join("；") || "未记录"}</p><small>{selectedStage.reference.limitations.map(evidenceTokenLabel).join("；")}</small></div></div>}</> : <div className="demo-empty"><ImageOff size={28} /><span>该视频属于讲解型内容，没有可用的连续阶段</span></div>}
  </article>;
}

function ReferenceCard({ job, reference }: { job: AnalysisJob; reference: CoachReference }) {
  const hasFrame = Boolean(reference.media_url);
  const hasClip = Boolean(reference.clip_media_url);
  return <article className="demo-reference-card">
    <div className="demo-media">
      {reference.media_url && <figure><figcaption>关键帧 · 姿态导航</figcaption><img src={coachReferenceUrl(reference.media_url, job)} alt="教练公开视频动作参考关键帧" /></figure>}
      {reference.clip_media_url && <figure><figcaption>0.8 秒短片 · 过程上下文</figcaption><video controls playsInline preload="metadata" src={coachReferenceClipUrl(reference.clip_media_url, job)} /></figure>}
      {!hasFrame && !hasClip && <div className="empty-frame"><ImageOff size={28} /><span>来源素材暂不可用</span></div>}
    </div>
    <div className="demo-reference-copy"><div className="reference-title"><span><Film size={15} />{(reference.timestamp_ms / 1000).toFixed(2)}s</span>{reference.source_jump_url && <a href={reference.source_jump_url} target="_blank" rel="noreferrer">原平台定位 <ExternalLink size={13} /></a>}</div><div className={`review-badge ${reference.review_status === "agent_reviewed" ? "reviewed" : "candidate"}`}>{reference.review_status === "agent_reviewed" ? "Agent 已视觉复核" : "模型定位候选 · 待复核"}</div><h3>{reference.title || reference.source_id}</h3>{reference.teaching_use && <p><b>教学用途：</b>{reference.teaching_use}</p>}<p><b>可见事实：</b>{reference.visible_facts.map(evidenceTokenLabel).join("；") || "未提供额外可见事实"}</p><small>{reference.limitations.map(evidenceTokenLabel).join("；")}</small></div>
  </article>;
}
