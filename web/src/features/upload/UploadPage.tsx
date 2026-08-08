import { useRef, useState } from "react";
import { FileVideo, ShieldCheck, Upload, Video } from "lucide-react";

import { createAnalysis, type AnalysisJob } from "../../api/client";

interface UploadPageProps {
  onCreated: (job: AnalysisJob) => void;
  onShowDemonstrations: () => void;
}

const maximumUploadBytes = 1_500_000_000;

export function UploadPage({ onCreated, onShowDemonstrations }: UploadPageProps) {
  const input = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [level, setLevel] = useState("beginner");
  const [dominantHand, setDominantHand] = useState("");
  const [trainingGoal, setTrainingGoal] = useState("technique_diagnosis");
  const [painRisk, setPainRisk] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  function chooseFile(next: File | null): void {
    setError("");
    if (next && next.size > maximumUploadBytes) {
      setFile(null);
      setError("视频超过 1.5 GB 上限。请先裁剪为一段完整动作或压缩后重试。");
      return;
    }
    setFile(next);
  }

  async function submit(): Promise<void> {
    if (!file) {
      setError("选择一段完整的羽毛球动作视频后才能开始分析。");
      return;
    }
    setSubmitting(true);
    setError("");
    const form = new FormData();
    form.set("video", file);
    form.set("analysis_mode", "agent_video_coaching");
    form.set("coach_id", "auto");
    form.set("player_profile", JSON.stringify({
      level,
      dominant_hand: dominantHand || undefined,
      training_goal: trainingGoal,
      injury_risk: painRisk || undefined,
    }));
    try {
      onCreated(await createAnalysis(form));
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "上传失败，请重试。");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="upload-page agent-upload-page">
      <section className="upload-intro">
        <div className="brand-lockup"><span className="brand-mark" />BadmintonCoach</div>
        <p className="eyebrow">Learner video coaching</p>
        <h1>上传完整动作，再决定怎么练。</h1>
        <p className="upload-lede">系统会先把视频里的动作片段分开，再只依据可看见的过程匹配三位教练的教学体系。看不清的部分会要求补拍，不会编出结论。</p>
        <div className="capture-guide">
          <span><Video size={17} aria-hidden="true" /> 从准备、移动、挥拍、落地到回位连续拍摄</span>
          <span><FileVideo size={17} aria-hidden="true" /> 保持全身与持拍侧可见；后场动作优先侧后方机位</span>
          <span><ShieldCheck size={17} aria-hidden="true" /> 视频、抽取帧和片段 24 小时后自动删除</span>
        </div>
        <button className="text-button" type="button" onClick={onShowDemonstrations}>暂时没有学员视频？先看教练的完整动作示范</button>
      </section>
      <section className="upload-surface" aria-label="创建学员视频教学">
        <div className="form-title"><p className="eyebrow">新建教学</p><h2>上传学员视频</h2><p>系统自动识别视频中的多个动作片段；只发布高置信、可复核的教学结果。</p></div>
        <button className={`dropzone ${file ? "has-file" : ""}`} type="button" onClick={() => input.current?.click()} aria-describedby="upload-privacy-note">
          <Upload size={30} strokeWidth={1.6} aria-hidden="true" />
          <strong>{file ? file.name : "选择 MP4、MOV 或 MKV 视频"}</strong>
          <span>{file ? `${Math.ceil(file.size / 1024 / 1024)} MB` : "单个文件不超过 1.5 GB"}</span>
        </button>
        <input ref={input} className="sr-only" type="file" accept="video/mp4,video/quicktime,video/x-matroska,video/*" onChange={(event) => chooseFile(event.target.files?.[0] ?? null)} />
        <p id="upload-privacy-note" className="upload-privacy-note">学员媒体只在受保护会话中访问；不会进入公开页面、代码仓库或模型训练数据。</p>
        <details className="profile-details">
          <summary>可选：补充练习背景</summary>
          <div className="profile-fields">
            <label>当前水平<select value={level} onChange={(event) => setLevel(event.target.value)}><option value="beginner">初学</option><option value="intermediate">进阶</option><option value="advanced">高级</option><option value="competitive">竞赛</option></select></label>
            <label>持拍手<select value={dominantHand} onChange={(event) => setDominantHand(event.target.value)}><option value="">不确定</option><option value="right">右手</option><option value="left">左手</option></select></label>
            <label>本次目标<select value={trainingGoal} onChange={(event) => setTrainingGoal(event.target.value)}><option value="technique_diagnosis">纠正动作</option><option value="stable_rear_court">后场稳定性</option><option value="smash_power">进攻衔接</option><option value="match_transfer">实战迁移</option></select></label>
            <label>疼痛或伤病风险<select value={painRisk} onChange={(event) => setPainRisk(event.target.value)}><option value="">未填写</option><option value="none_reported">无</option><option value="present">有，请降低强度</option></select></label>
          </div>
        </details>
        {error && <p className="form-error" role="alert">{error}</p>}
        <button className="primary-button" type="button" disabled={submitting} onClick={() => void submit()}>{submitting ? "正在安全上传" : "开始分段与教学匹配"}</button>
      </section>
    </main>
  );
}
