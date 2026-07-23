import { useState } from "react";
import { BookOpenCheck, Film, Images, Sparkles } from "lucide-react";

import { createDemonstration, type AnalysisJob } from "../../api/client";

interface DemonstrationPageProps {
  onCreated: (job: AnalysisJob) => void;
  onShowVideoAnalysis: () => void;
}

const actionOptions: Record<string, Array<{ value: string; label: string }>> = {
  "liu-hui": [
    { value: "high_clear", label: "后场高远球" },
    { value: "smash", label: "杀球" },
    { value: "drop", label: "吊球与变化" },
    { value: "rear_footwork", label: "后场步法" },
    { value: "drive", label: "平抽挡" },
    { value: "backhand", label: "反手" },
    { value: "serve_receive", label: "发接发" },
  ],
  "li-yuxuan": [
    { value: "high_clear", label: "后场高远球" },
    { value: "smash", label: "杀球" },
    { value: "drop", label: "吊球与变化" },
    { value: "rear_footwork", label: "后场步法" },
    { value: "drive", label: "平抽挡" },
    { value: "backhand", label: "反手" },
    { value: "serve_receive", label: "发接发" },
  ],
  "zheng-siwei": [{ value: "mixed_doubles", label: "混双衔接与轮转" }],
};

const phases = [
  { value: "preparation", label: "准备与启动姿态" },
  { value: "arrival", label: "到位与支撑" },
  { value: "top_elbow", label: "架拍与顶肘阶段" },
  { value: "follow_through", label: "随挥、落地与衔接" },
];

function defaultPhase(coach: string, action: string): string {
  if (coach === "zheng-siwei") return "follow_through";
  if (action.includes("footwork")) return "arrival";
  return "top_elbow";
}

function trainingGoal(action: string, phase: string): string {
  if (phase === "top_elbow") return "racket_frame";
  if (phase === "arrival") return "stable_rear_court";
  if (phase === "follow_through") return "match_transfer";
  if (action === "smash") return "smash_power";
  return "stable_rear_court";
}

export function DemonstrationPage({ onCreated, onShowVideoAnalysis }: DemonstrationPageProps) {
  const [coach, setCoach] = useState("liu-hui");
  const [action, setAction] = useState("high_clear");
  const [phase, setPhase] = useState("top_elbow");
  const [level, setLevel] = useState("beginner");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  async function submit(): Promise<void> {
    setSubmitting(true);
    setError("");
    try {
      onCreated(await createDemonstration({
        coach_id: coach,
        action,
        phase,
        training_goal: trainingGoal(action, phase),
        level,
        limit: 2,
      }));
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "示范素材准备失败，请重试。");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="upload-page demonstration-page">
      <section className="upload-intro">
        <div className="brand-lockup"><span className="brand-mark" />BadmintonCoach</div>
        <p className="eyebrow">Coach demonstration skill</p>
        <h1>先看教练怎么做，再理解动作阶段。</h1>
        <p className="upload-lede">无需上传学员视频。选择动作和阶段后，Skill 会匹配教学框架，从已索引的教练公开视频时间点提取关键帧与短片，并保留来源和证据边界。</p>
        <div className="capture-guide">
          <span><Images size={17} /> 关键帧用于观察姿态</span>
          <span><Film size={17} /> 短片用于理解连续动作</span>
        </div>
        <button className="text-button" type="button" onClick={onShowVideoAnalysis}>已有学员视频？进入视频分析</button>
      </section>
      <section className="upload-surface" aria-label="创建教练动作示范">
        <div className="form-title"><p className="eyebrow">教练示范库</p><h2>选择要学习的动作</h2></div>
        <div className="demo-promise"><Sparkles size={22} /><span>只返回同动作、同阶段的公开教练示范候选；没有可靠画面时明确留空。</span></div>
        <label>教练体系<select value={coach} onChange={(event) => {
          const nextCoach = event.target.value;
          const nextAction = actionOptions[nextCoach][0].value;
          setCoach(nextCoach);
          setAction(nextAction);
          setPhase(defaultPhase(nextCoach, nextAction));
        }}><option value="liu-hui">刘辉</option><option value="li-yuxuan">李宇轩</option><option value="zheng-siwei">郑思维 · 混双</option></select></label>
        <label>动作主题<select value={action} onChange={(event) => { const next = event.target.value; setAction(next); setPhase(defaultPhase(coach, next)); }}>{actionOptions[coach].map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}</select></label>
        <label>观察阶段<select value={phase} onChange={(event) => setPhase(event.target.value)}>{phases.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}</select></label>
        <label>学习阶段<select value={level} onChange={(event) => setLevel(event.target.value)}><option value="beginner">初学</option><option value="intermediate">进阶</option><option value="advanced">高级</option>{coach === "zheng-siwei" && <option value="competitive">竞赛</option>}</select></label>
        {error && <p className="form-error" role="alert">{error}</p>}
        <button className="primary-button" type="button" disabled={submitting} onClick={submit}><BookOpenCheck size={18} />{submitting ? "正在建立示范" : "查看教练示范"}</button>
      </section>
    </main>
  );
}
