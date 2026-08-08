import { useEffect, useState } from "react";
import { CheckCircle2, CircleAlert, LoaderCircle } from "lucide-react";

import { getAnalysis, subscribeToJob, type AnalysisJob, type JobEvent } from "../../api/client";

const labels: Record<string, string> = {
  uploaded: "已接收视频",
  queued: "等待分析",
  normalizing: "准备视频",
  segmenting: "分开视频中的动作",
  tracking: "追踪学员动作",
  phase_candidates: "选择动作阶段帧",
  visual_review: "审阅可见动作",
  observing: "核验可见动作证据",
  diagnosing: "生成技术诊断",
  matching_references: "匹配教练参考画面",
  needs_player_selection: "确认球员与场地",
  completed: "分析完成",
  failed: "分析未完成",
  expired: "分析已过期"
};

interface AnalysisProgressProps {
  job: AnalysisJob;
  onComplete: () => void;
  onNeedsSetup: () => void;
  onExpired: () => void;
  variant?: "video" | "agent-video" | "demonstration" | "coaching-plan";
}

export function AnalysisProgress({ job, onComplete, onNeedsSetup, onExpired, variant = "video" }: AnalysisProgressProps) {
  const [current, setCurrent] = useState(job);
  const [message, setMessage] = useState("正在建立分析任务。");

  useEffect(() => {
    const unsubscribe = subscribeToJob(job, (event: JobEvent) => {
      setCurrent((previous) => ({ ...previous, state: event.state, progress: event.progress }));
      setMessage(event.message);
      if (event.state === "completed") onComplete();
      if (event.state === "needs_player_selection") onNeedsSetup();
      if (event.state === "expired") onExpired();
    }, () => undefined);
    const timer = window.setInterval(() => {
      getAnalysis(job).then((updated) => {
        setCurrent(updated);
        if (updated.state === "completed") onComplete();
        if (updated.state === "needs_player_selection") onNeedsSetup();
        if (updated.state === "expired") onExpired();
      }).catch(() => undefined);
    }, 3000);
    return () => { unsubscribe(); window.clearInterval(timer); };
  }, [job.analysis_id, onComplete, onNeedsSetup, onExpired]);

  const failed = current.state === "failed";
  const heading = (variant === "demonstration" || variant === "coaching-plan") && current.state === "matching_references" ? "准备连续教练课程" : labels[current.state] ?? current.state;
  const title = variant === "demonstration" ? "教练示范 Skill" : variant === "coaching-plan" ? "结构化教学方案" : variant === "agent-video" ? "学员视频教学" : "视频证据分析";
  const retry = variant === "video" || variant === "agent-video" ? "返回重新上传" : variant === "coaching-plan" ? "返回教学方案" : "返回示范库";
  return <main className="progress-page"><section className="progress-card"><div className="progress-icon">{current.state === "completed" ? <CheckCircle2 /> : failed ? <CircleAlert /> : <LoaderCircle className="spin" />}</div><p className="eyebrow">{title}</p><h1>{heading}</h1><p>{message}</p><div className="progress-track"><span style={{ width: `${current.progress}%` }} /></div><div className="progress-meta"><span>{current.progress}%</span><span>访问权限将在 {new Date(current.expires_at).toLocaleString("zh-CN")} 过期</span></div>{failed && <button className="primary-button" type="button" onClick={onExpired}>{retry}</button>}</section></main>;
}
