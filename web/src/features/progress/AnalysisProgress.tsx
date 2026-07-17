import { useEffect, useState } from "react";
import { CheckCircle2, CircleAlert, LoaderCircle } from "lucide-react";

import { getAnalysis, subscribeToJob, type AnalysisJob, type JobEvent } from "../../api/client";

const labels: Record<string, string> = {
  uploaded: "已接收视频",
  queued: "等待分析",
  normalizing: "准备视频",
  tracking: "追踪学员动作",
  phase_candidates: "选择动作阶段帧",
  visual_review: "审阅可见动作",
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
}

export function AnalysisProgress({ job, onComplete, onNeedsSetup, onExpired }: AnalysisProgressProps) {
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
  return <main className="progress-page"><section className="progress-card"><div className="progress-icon">{current.state === "completed" ? <CheckCircle2 /> : failed ? <CircleAlert /> : <LoaderCircle className="spin" />}</div><p className="eyebrow">视频证据分析</p><h1>{labels[current.state] ?? current.state}</h1><p>{message}</p><div className="progress-track"><span style={{ width: `${current.progress}%` }} /></div><div className="progress-meta"><span>{current.progress}%</span><span>媒体将在 {new Date(current.expires_at).toLocaleString("zh-CN")} 删除</span></div>{failed && <button className="primary-button" type="button" onClick={onExpired}>返回重新上传</button>}</section></main>;
}
