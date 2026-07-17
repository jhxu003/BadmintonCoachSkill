import { useEffect, useMemo, useState, type MouseEvent } from "react";
import { ChevronLeft, Crosshair, LoaderCircle, RotateCcw, ShieldCheck, Users } from "lucide-react";

import {
  getMixedDoublesSetup,
  setupFrameUrl,
  submitMixedDoublesSetup,
  type AnalysisJob,
  type MixedDoublesSetup,
  type SetupPlayer,
} from "../../api/client";
import {
  COURT_CORNER_ORDER,
  canSubmitSetup,
  nextCourtCorner,
  normalizedPointFromPointer,
  type CourtCornerName,
  type CourtCorners,
} from "./setupModel";


const cornerLabels: Record<CourtCornerName, string> = {
  far_left: "远端左角",
  far_right: "远端右角",
  near_right: "近端右角",
  near_left: "近端左角",
};

interface PlayerSetupPageProps {
  job: AnalysisJob;
  onSubmitted: (job: AnalysisJob) => void;
  onBack: () => void;
}

export function PlayerSetupPage({ job, onSubmitted, onBack }: PlayerSetupPageProps) {
  const [setup, setSetup] = useState<MixedDoublesSetup | null>(null);
  const [learner, setLearner] = useState("");
  const [partner, setPartner] = useState("");
  const [activeRole, setActiveRole] = useState<"learner" | "partner">("learner");
  const [corners, setCorners] = useState<CourtCorners>({});
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    getMixedDoublesSetup(job).then((loaded) => {
      setSetup(loaded);
      if (loaded.selection) {
        setLearner(loaded.selection.learner_track_id);
        setPartner(loaded.selection.partner_track_id);
        setCorners(loaded.selection.court_corners as CourtCorners);
      }
    }).catch((requestError) => {
      setError(requestError instanceof Error ? requestError.message : "球员候选读取失败。" );
    }).finally(() => setLoading(false));
  }, [job.analysis_id]);

  const nextCorner = nextCourtCorner(corners);
  const polygon = useMemo(() => COURT_CORNER_ORDER
    .map((name) => corners[name])
    .filter((point): point is { x: number; y: number } => Boolean(point))
    .map((point) => `${point.x * 100},${point.y * 100}`)
    .join(" "), [corners]);

  function choosePlayer(player: SetupPlayer): void {
    if (activeRole === "learner") {
      setLearner(player.track_id);
      if (partner === player.track_id) setPartner("");
      setActiveRole("partner");
    } else {
      setPartner(player.track_id);
      if (learner === player.track_id) setLearner("");
      setActiveRole("learner");
    }
  }

  function markCorner(event: MouseEvent<HTMLDivElement>): void {
    if (!nextCorner) return;
    const point = normalizedPointFromPointer(event, event.currentTarget.getBoundingClientRect());
    setCorners((previous) => ({ ...previous, [nextCorner]: point }));
  }

  async function submit(): Promise<void> {
    if (!canSubmitSetup(learner, partner, corners)) return;
    setSubmitting(true);
    setError("");
    try {
      const courtCorners = Object.fromEntries(
        COURT_CORNER_ORDER.map((name) => [name, corners[name]]),
      ) as Record<string, { x: number; y: number }>;
      onSubmitted(await submitMixedDoublesSetup(job, {
        learner_track_id: learner,
        partner_track_id: partner,
        court_corners: courtCorners,
      }));
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "设置提交失败，请检查球员与场地标记。" );
    } finally {
      setSubmitting(false);
    }
  }

  if (loading) return <main className="progress-page"><section className="progress-card"><LoaderCircle className="spin" /><h1>正在准备战术板</h1><p>读取四名球员候选与场地画面。</p></section></main>;

  const imagePath = setup?.candidate_frame.media_url;
  return (
    <main className="setup-page">
      <header className="workspace-topbar">
        <button className="icon-text-button" type="button" onClick={onBack}><ChevronLeft size={17} /> 返回</button>
        <div className="brand-lockup"><span className="brand-mark" />BadmintonCoach</div>
        <span className="setup-expiry">24 小时私有媒体</span>
      </header>
      <section className="setup-heading">
        <div><p className="eyebrow">郑思维混双 / 人工确认</p><h1>先确认人，再判断轮转。</h1></div>
        <p>系统已找出四条候选轨迹。你决定谁是学员、谁是搭档，并依次标出场地四角；系统不会用性别或站位替你猜角色。</p>
      </section>
      <div className="setup-layout">
        <section className="tactics-board" aria-label="球员和场地标记画面">
          <div className="board-head"><div><p className="eyebrow">候选帧</p><h2>{((setup?.candidate_frame.timestamp_ms ?? 0) / 1000).toFixed(2)}s</h2></div><span>{nextCorner ? `下一点：${cornerLabels[nextCorner]}` : "四角已完成"}</span></div>
          {imagePath ? (
            <div className="setup-frame" onClick={markCorner} role="button" tabIndex={0} aria-label={nextCorner ? `点击标记${cornerLabels[nextCorner]}` : "场地四角已标记"}>
              <img src={setupFrameUrl(imagePath, job)} alt="四名球员候选与场地标记帧" draggable={false} />
              <svg className="court-overlay" viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">
                {polygon && <polyline points={polygon} fill={COURT_CORNER_ORDER.every((name) => corners[name]) ? "rgba(31,157,104,.14)" : "none"} stroke="currentColor" strokeWidth="0.65" vectorEffect="non-scaling-stroke" />}
                {COURT_CORNER_ORDER.map((name, index) => corners[name] && <g key={name}><circle cx={corners[name]!.x * 100} cy={corners[name]!.y * 100} r="1.25" vectorEffect="non-scaling-stroke" /><text x={corners[name]!.x * 100 + 1.8} y={corners[name]!.y * 100 - 1.8}>{index + 1}</text></g>)}
              </svg>
              {setup?.players.map((player, index) => <button key={player.track_id} type="button" className={`player-box ${player.track_id === learner ? "learner" : player.track_id === partner ? "partner" : ""}`} style={{ left: `${player.bbox.x * 100}%`, top: `${player.bbox.y * 100}%`, width: `${player.bbox.width * 100}%`, height: `${player.bbox.height * 100}%` }} onClick={(event) => { event.stopPropagation(); choosePlayer(player); }} aria-label={`选择球员 ${index + 1}`}><span>{index + 1}</span></button>)}
            </div>
          ) : <div className="video-empty">候选帧暂不可用</div>}
          <div className="board-legend"><span className="learner-dot" />学员 <span className="partner-dot" />搭档 <span className="court-line-key" />场地边界</div>
        </section>
        <aside className="setup-controls">
          <section className="setup-step">
            <div className="step-title"><Users size={18} /><div><span>角色</span><h2>选择学员与搭档</h2></div></div>
            <div className="role-switch" role="group" aria-label="当前选择角色"><button type="button" className={activeRole === "learner" ? "active learner" : ""} onClick={() => setActiveRole("learner")}>选择学员</button><button type="button" className={activeRole === "partner" ? "active partner" : ""} onClick={() => setActiveRole("partner")}>选择搭档</button></div>
            <div className="candidate-list">{setup?.players.map((player, index) => <button key={player.track_id} type="button" className={player.track_id === learner ? "learner" : player.track_id === partner ? "partner" : ""} onClick={() => choosePlayer(player)}><b>球员 {index + 1}</b><span>{player.track_id === learner ? "学员" : player.track_id === partner ? "搭档" : `${Math.round(player.confidence * 100)}% 轨迹可信度`}</span></button>)}</div>
          </section>
          <section className="setup-step">
            <div className="step-title"><Crosshair size={18} /><div><span>场地</span><h2>依次点击四角</h2></div></div>
            <ol className="corner-list">{COURT_CORNER_ORDER.map((name, index) => <li key={name} className={corners[name] ? "done" : name === nextCorner ? "active" : ""}><span>{index + 1}</span>{cornerLabels[name]}{corners[name] && <ShieldCheck size={15} />}</li>)}</ol>
            <button type="button" className="reset-corners" onClick={() => setCorners({})}><RotateCcw size={14} /> 重新标四角</button>
          </section>
          {error && <p className="form-error" role="alert">{error}</p>}
          <button className="primary-button setup-submit" type="button" disabled={!canSubmitSetup(learner, partner, corners) || submitting} onClick={() => void submit()}>{submitting ? "正在继续分析" : "确认并继续 GPU 分析"}</button>
        </aside>
      </div>
    </main>
  );
}
