import { ExternalLink, Film, ImageOff, ShieldCheck } from "lucide-react";

import { coachReferenceClipUrl, coachReferenceUrl, deleteAnalysis, type AnalysisJob, type CoachDemonstrationReport, type CoachReference } from "../../api/client";
import { evidenceTokenLabel } from "../workspace/rallyModel";

interface DemonstrationWorkspaceProps {
  job: AnalysisJob;
  report: CoachDemonstrationReport;
  onBack: () => void;
}

const phaseLabels: Record<string, string> = {
  preparation: "准备与启动姿态",
  arrival: "到位与支撑",
  top_elbow: "架拍与顶肘阶段",
  follow_through: "随挥、落地与衔接",
};

export function DemonstrationWorkspace({ job, report, onBack }: DemonstrationWorkspaceProps) {
  async function close(): Promise<void> {
    await deleteAnalysis(job).catch(() => undefined);
    onBack();
  }

  return (
    <main className="demo-workspace">
      <header className="demo-header">
        <div><p className="eyebrow">Coach demonstration</p><h1>{report.coach_name} · {phaseLabels[report.query.phase] ?? report.query.phase}</h1><p>{report.notice}</p></div>
        <button className="secondary-button" type="button" onClick={() => void close()}>返回示范库</button>
      </header>

      <section className="teaching-route-section">
        <div className="section-heading"><div><p className="eyebrow">Skill 教学路线</p><h2>先理解原则，再看动作画面</h2></div><span className="evidence-chip"><ShieldCheck size={15} />非官方公开资料研究整理</span></div>
        <div className="teaching-route-grid">
          {report.teaching_routes.map((route, index) => <article key={route.framework_id} className="teaching-route-card"><span>{String(index + 1).padStart(2, "0")}</span><h3>{route.name}</h3><p>{route.summary}</p><small>{route.framework_id} · {route.confidence}</small></article>)}
        </div>
      </section>

      <section className="demo-reference-section">
        <div className="section-heading"><div><p className="eyebrow">同阶段教练参考</p><h2>关键帧看姿态，短片看过程</h2></div></div>
        {report.coach_references.length ? <div className="demo-reference-grid">{report.coach_references.map((reference) => <ReferenceCard key={reference.reference_id} job={job} reference={reference} />)}</div> : <div className="demo-empty"><ImageOff size={30} /><h3>当前目录没有可靠的同阶段示范帧</h3><p>Skill 没有跨阶段借图。可以切换动作阶段，或等待该来源完成更细的人工时间点审核。</p></div>}
      </section>

      <section className="demo-boundary"><h2>证据边界</h2><ul>{report.limitations.map((item) => <li key={item}>{evidenceTokenLabel(item)}</li>)}</ul></section>
    </main>
  );
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
