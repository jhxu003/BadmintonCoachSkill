import { ExternalLink, ImageOff } from "lucide-react";

import { studentFrameUrl, type FrameRef, type IssueEvidence } from "../../api/client";

interface FrameComparisonProps { analysisId: string; evidence?: IssueEvidence; studentFrames: Map<string, FrameRef>; coachFrames: Map<string, FrameRef>; }

export function FrameComparison({ analysisId, evidence, studentFrames, coachFrames }: FrameComparisonProps) {
  if (!evidence) return <section className="comparison-empty"><ImageOff size={22} /><p>选择一个诊断问题后查看对应画面。</p></section>;
  const student = evidence.student_frame_ids.map((id) => studentFrames.get(id)).find(Boolean);
  const coach = evidence.coach_reference_ids.map((id) => coachFrames.get(id)).find(Boolean);
  const unavailable = evidence.status === "insufficient_evidence";
  return <section className="comparison-panel"><div className="comparison-head"><div><p className="eyebrow">同阶段画面对照</p><h2>{evidence.comparison_phase}</h2></div>{coach?.source_url && <a className="source-link" href={coach.source_url} target="_blank" rel="noreferrer">在原平台打开 <ExternalLink size={14} /></a>}</div><div className="comparison-grid"><article className="evidence-frame"><div className="frame-label"><b>学员关键帧</b><span>{student ? `${(student.timestamp_ms / 1000).toFixed(2)}s` : "未获取"}</span></div>{student ? <img src={student.media_url ?? studentFrameUrl(analysisId, student.frame_id)} alt="学员动作关键帧" /> : <EmptyFrame text="当前视频没有足够画面支持该阶段判断" />}<FrameFacts frame={student} /></article><div className="compare-arrow" aria-hidden="true">↔</div><article className="evidence-frame"><div className="frame-label"><b>教练公开参考帧</b><span>{coach ? `${(coach.timestamp_ms / 1000).toFixed(2)}s` : "来源不可用"}</span></div>{coach?.media_url ? <img src={coach.media_url} alt="教练动作参考关键帧" /> : <EmptyFrame text={unavailable ? "证据不足，请补拍对应机位" : "该公开来源的画面缓存暂不可用"} />}<FrameFacts frame={coach} /></article></div><div className="evidence-boundary"><b>纠正目标：</b>{evidence.correction_target}<br /><span>{evidence.confidence_boundary}</span></div></section>;
}

function EmptyFrame({ text }: { text: string }) { return <div className="empty-frame"><ImageOff size={26} /><span>{text}</span></div>; }
function FrameFacts({ frame }: { frame?: FrameRef }) { return <p className="frame-facts">{frame ? <><b>可见事实：</b>{frame.visible_facts.join("；") || "当前帧未提供额外可见事实"}<br /><span>{frame.limitations.join("；")}</span></> : ""}</p>; }
