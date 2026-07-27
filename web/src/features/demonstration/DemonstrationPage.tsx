import { useState } from "react";
import { BookOpenCheck, Film, Images, Sparkles } from "lucide-react";

import { createDemonstration, type AnalysisJob } from "../../api/client";

interface DemonstrationPageProps {
  onCreated: (job: AnalysisJob) => void;
  onShowVideoAnalysis: () => void;
  onShowCoachingPlan: () => void;
}

const actionOptions: Record<string, Array<{ value: string; label: string }>> = {
  "liu-hui": [
    { value: "smash", label: "杀球" },
    { value: "high_clear", label: "后场高远球" },
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

function trainingGoal(action: string): string {
  if (action === "smash") return "smash_power";
  if (action.includes("footwork")) return "stable_rear_court";
  if (action === "serve_receive") return "match_transfer";
  if (action === "high_clear") return "racket_frame";
  return "stable_rear_court";
}

export function DemonstrationPage({ onCreated, onShowVideoAnalysis, onShowCoachingPlan }: DemonstrationPageProps) {
  const [coach, setCoach] = useState("liu-hui");
  const [action, setAction] = useState(actionOptions["liu-hui"][0].value);
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
        training_goal: trainingGoal(action),
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
        <h1>从一条教练视频，理解一项完整技术。</h1>
        <p className="upload-lede">无需上传学员视频。选择动作后，Skill 会优先返回同一条公开视频中的连续示范、按顺序排列的阶段关键帧、教学路线与证据边界。</p>
        <div className="capture-guide">
          <span><Film size={17} /> 完整片段保留动作连续性</span>
          <span><Images size={17} /> 阶段关键帧用于逐步导航</span>
        </div>
        <button className="text-button" type="button" onClick={onShowCoachingPlan}>已有结构化学员问题？生成教学方案</button>
        <button className="text-button" type="button" onClick={onShowVideoAnalysis}>已有学员视频？进入视频分析</button>
      </section>
      <section className="upload-surface" aria-label="创建教练动作示范">
        <div className="form-title"><p className="eyebrow">教练示范库</p><h2>选择要学习的动作</h2></div>
        <div className="demo-promise"><Sparkles size={22} /><span>优先返回经过复核的完整视频教学包；视频只包含静态或部分示范时会明确标注，不拼接不连续画面。</span></div>
        <label>教练体系<select value={coach} onChange={(event) => {
          const nextCoach = event.target.value;
          const nextAction = actionOptions[nextCoach][0].value;
          setCoach(nextCoach);
          setAction(nextAction);
        }}><option value="liu-hui">刘辉</option><option value="li-yuxuan">李宇轩</option><option value="zheng-siwei">郑思维 · 混双</option></select></label>
        <label>动作主题<select value={action} onChange={(event) => setAction(event.target.value)}>{actionOptions[coach].map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}</select></label>
        <label>学习阶段<select value={level} onChange={(event) => setLevel(event.target.value)}><option value="beginner">初学</option><option value="intermediate">进阶</option><option value="advanced">高级</option>{coach === "zheng-siwei" && <option value="competitive">竞赛</option>}</select></label>
        {error && <p className="form-error" role="alert">{error}</p>}
        <button className="primary-button" type="button" disabled={submitting} onClick={submit}><BookOpenCheck size={18} />{submitting ? "正在建立教学包" : "查看完整视频教学"}</button>
      </section>
    </main>
  );
}
