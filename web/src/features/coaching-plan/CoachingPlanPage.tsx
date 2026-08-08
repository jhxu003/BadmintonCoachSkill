import { useState } from "react";
import { ClipboardCheck, FileJson, Sparkles } from "lucide-react";

import { createCoachingPlan, type AnalysisJob } from "../../api/client";

interface CoachingPlanPageProps {
  onCreated: (job: AnalysisJob, draft: CoachingPlanDraft) => void;
  onShowDemonstrations: () => void;
}

type StructuredPayload = {
  player_profile: Record<string, unknown>;
  video_observation: Record<string, unknown>;
};

export type CoachingPlanDraft = StructuredPayload & {
  coach_id: "auto" | string;
  limit: number;
};

const samples: Record<string, { label: string; coach: string; payload: StructuredPayload }> = {
  liu: {
    label: "高远球 · 后场到位偏晚",
    coach: "auto",
    payload: {
      player_profile: { level: "beginner", age_band: "adult", strength: "average", mobility: "limited", coordination: "arm_dominant", injury_risk: [], training_goal: "clear_to_baseline", dominant_hand: "right", available_training_time: "20min_per_day" },
      video_observation: { action: "high_clear", camera_view: "rear_side", fps_quality: "good", phase_observations: {}, contact_point: "behind_head", elbow_height_before_hit: "below_shoulder", wrist_elbow_sequence: "wrist_before_elbow", hip_shoulder_sequence: "late_hip", racket_side_structure: "collapsed", follow_through: "short", footwork_observations: { arrival_timing: "late", recovery: "slow" }, missing_observations: [], keyframes: [{ label: "pre_hit", time_ms: 1840 }] },
    },
  },
  li: {
    label: "高远球 · 后场启动偏晚",
    coach: "auto",
    payload: {
      player_profile: { level: "intermediate", age_band: "adult", strength: "average", mobility: "normal", coordination: "arm_dominant", injury_risk: [], training_goal: "clear_to_baseline", dominant_hand: "right", available_training_time: "20min_per_day" },
      video_observation: { action: "high_clear", camera_view: "rear_side", fps_quality: "good", phase_observations: { first_step: "late" }, contact_point: "unknown", elbow_height_before_hit: "unknown", wrist_elbow_sequence: "unknown", hip_shoulder_sequence: "unknown", racket_side_structure: "unknown", follow_through: "unknown", footwork_observations: { start_timing: "late" }, missing_observations: ["contact_point", "elbow_height_before_hit", "wrist_elbow_sequence", "hip_shoulder_sequence", "racket_side_structure", "follow_through"], keyframes: [{ label: "opponent_contact", time_ms: 900 }] },
    },
  },
  zheng: {
    label: "混双 · 前场没有接入进攻",
    coach: "auto",
    payload: {
      player_profile: { level: "intermediate", age_band: "adult", strength: "average", mobility: "normal", coordination: "balanced", injury_risk: [], training_goal: "doubles_positioning", dominant_hand: "right", available_training_time: "20min_per_day" },
      video_observation: { action: "doubles", camera_view: "full_court_rear", fps_quality: "good", phase_observations: { front_player_state: "watching" }, contact_point: "front_high", elbow_height_before_hit: "missing", wrist_elbow_sequence: "missing", hip_shoulder_sequence: "missing", racket_side_structure: "stable", follow_through: "complete", footwork_observations: { recovery: "normal" }, missing_observations: [], keyframes: [{ label: "front_player_after_partner_attack", time_ms: 1560 }] },
    },
  },
};

export function CoachingPlanPage({ onCreated, onShowDemonstrations }: CoachingPlanPageProps) {
  const [coach, setCoach] = useState("auto");
  const [payloadText, setPayloadText] = useState(JSON.stringify(samples.liu.payload, null, 2));
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  function loadSample(key: string): void {
    const sample = samples[key];
    setCoach(sample.coach);
    setPayloadText(JSON.stringify(sample.payload, null, 2));
    setError("");
  }

  async function submit(): Promise<void> {
    setSubmitting(true);
    setError("");
    try {
      const payload = JSON.parse(payloadText) as StructuredPayload;
      if (!payload.player_profile || !payload.video_observation || typeof payload.player_profile !== "object" || typeof payload.video_observation !== "object") {
        throw new Error("JSON 必须包含 player_profile 与 video_observation 两个对象。");
      }
      const draft: CoachingPlanDraft = {
        coach_id: coach,
        player_profile: payload.player_profile,
        video_observation: payload.video_observation,
        limit: 2,
      };
      onCreated(await createCoachingPlan(draft), draft);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "教学方案创建失败，请检查结构化观察。");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="upload-page coaching-plan-page">
      <section className="upload-intro">
        <div className="brand-lockup"><span className="brand-mark" />BadmintonCoach</div>
        <p className="eyebrow">结构化教学方案</p>
        <h1>把看得见的问题，变成下一次能练的动作。</h1>
        <p className="upload-lede">粘贴人工标注或未来 Video Agent 的结构化观察。系统会推荐一个适合当前观察的教练教学视角，先给一项最值得练的内容，再保留两项后续练习；连续示范只会绑定到同一主题下已审核的教练课程。</p>
        <div className="capture-guide"><span><ClipboardCheck size={17} />观察先于判断</span><span><FileJson size={17} />结构化输入可复查</span></div>
        <button className="text-button" type="button" onClick={onShowDemonstrations}>没有学员问题？进入教练示范库</button>
      </section>
      <section className="upload-surface coaching-plan-surface" aria-label="创建结构化教学方案">
        <div className="form-title"><p className="eyebrow">结构化学员问题</p><h2>导入观察，安排这一节练什么</h2></div>
        <div className="demo-promise"><Sparkles size={22} /><span>不会从文本或单帧推断精确触球、拍面角度、力量、握拍压力、真实内旋或三维运动学；缺失字段会保留为证据不足。</span></div>
        <label>教学视角<select value={coach} onChange={(event) => setCoach(event.target.value)}><option value="auto">自动推荐</option><option value="liu-hui">刘辉</option><option value="li-yuxuan">李宇轩</option><option value="zheng-siwei">郑思维 · 混双</option></select></label>
        <div className="plan-samples">{Object.entries(samples).map(([key, sample]) => <button key={key} type="button" className="secondary-button" onClick={() => loadSample(key)}>{sample.label}</button>)}</div>
        <label>结构化观察 JSON<textarea value={payloadText} onChange={(event) => setPayloadText(event.target.value)} spellCheck={false} rows={17} /></label>
        {error && <p className="form-error" role="alert">{error}</p>}
        <button className="primary-button" type="button" disabled={submitting} onClick={submit}><ClipboardCheck size={18} />{submitting ? "正在匹配教学" : "生成教学方案"}</button>
      </section>
    </main>
  );
}
