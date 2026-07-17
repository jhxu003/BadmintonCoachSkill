import { useRef, useState } from "react";
import { FileVideo, Upload, Video } from "lucide-react";

import { createAnalysis, type AnalysisJob } from "../../api/client";

interface UploadPageProps {
  onCreated: (job: AnalysisJob) => void;
}

export function UploadPage({ onCreated }: UploadPageProps) {
  const input = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [coach, setCoach] = useState("liu-hui");
  const [action, setAction] = useState("high_clear");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  async function submit(): Promise<void> {
    if (!file) {
      setError("选择一段羽毛球视频后才能开始分析。");
      return;
    }
    setSubmitting(true);
    setError("");
    const form = new FormData();
    form.set("video", file);
    form.set("coach_id", coach);
    form.set("action_hint", action);
    form.set("player_profile", JSON.stringify({
      level: coach === "zheng-siwei" ? "intermediate" : "beginner",
      training_goal: coach === "zheng-siwei" ? "mixed_doubles_rotation" : "technique_diagnosis",
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
    <main className="upload-page">
      <section className="upload-intro">
        <div className="brand-lockup"><span className="brand-mark" />BadmintonCoach</div>
        <p className="eyebrow">Video evidence coaching</p>
        <h1>让每一次纠正回到动作画面。</h1>
        <p className="upload-lede">上传学员视频后，系统会定位动作阶段或完整回合、匹配教练体系，并把诊断问题绑定到学员与教练的对应证据画面。</p>
        <div className="capture-guide">
          <span><Video size={17} /> 保持全身与持拍侧可见</span>
          <span><FileVideo size={17} /> 后场动作建议使用侧后方机位</span>
        </div>
      </section>
      <section className="upload-surface" aria-label="创建视频分析">
        <div className="form-title"><p className="eyebrow">新建分析</p><h2>上传学员视频</h2></div>
        <button className={`dropzone ${file ? "has-file" : ""}`} type="button" onClick={() => input.current?.click()}>
          <Upload size={30} strokeWidth={1.6} />
          <strong>{file ? file.name : "选择 MP4、MOV 或 MKV 视频"}</strong>
          <span>{file ? `${Math.ceil(file.size / 1024 / 1024)} MB` : "视频与抽取帧将在 24 小时后自动删除"}</span>
        </button>
        <input ref={input} className="sr-only" type="file" accept="video/*" onChange={(event) => setFile(event.target.files?.[0] ?? null)} />
        <label>教练体系<select value={coach} onChange={(event) => { const next = event.target.value; setCoach(next); setAction(next === "zheng-siwei" ? "mixed_doubles" : "high_clear"); }}><option value="liu-hui">刘辉</option><option value="li-yuxuan">李宇轩</option><option value="zheng-siwei">郑思维 · 混双</option></select></label>
        <label>分析内容<select value={action} onChange={(event) => setAction(event.target.value)} disabled={coach === "zheng-siwei"}>{coach === "zheng-siwei" ? <option value="mixed_doubles">混双完整回合</option> : <><option value="high_clear">后场高远球</option><option value="smash">杀球</option><option value="drop">吊球</option><option value="rear_footwork">后场步法</option><option value="drive">平抽挡</option></>}</select></label>
        {error && <p className="form-error" role="alert">{error}</p>}
        <button className="primary-button" type="button" disabled={submitting} onClick={submit}>{submitting ? "正在上传" : "开始分析"}</button>
      </section>
    </main>
  );
}
