export const RALLY_MODULES = [
  { id: "serve_opening", short: "发球开局", title: "发球与开局" },
  { id: "receive_opening_exchange", short: "接发交换", title: "接发与开局交换" },
  { id: "frontcourt_pressure", short: "前场压迫", title: "前场压迫" },
  { id: "rear_attack", short: "后场进攻", title: "后场进攻" },
  { id: "rotation", short: "两人轮转", title: "两人轮转" },
  { id: "defense_transition", short: "防守转换", title: "防守到进攻转换" },
  { id: "reset_match_transfer", short: "回位迁移", title: "回位与实战迁移" },
] as const;

export interface ContactWindow {
  start_ms: number;
  end_ms: number;
  confidence: "low" | "medium" | "high";
}

const confidenceLabels = { low: "低可信", medium: "中可信", high: "高可信" } as const;

export function contactWindowLabel(contact: ContactWindow): string {
  return `${(contact.start_ms / 1000).toFixed(2)}–${(contact.end_ms / 1000).toFixed(2)}s · ${confidenceLabels[contact.confidence]} · 非精确触球候选`;
}

export function rallyModuleTitle(moduleId: string): string {
  return RALLY_MODULES.find((module) => module.id === moduleId)?.title ?? moduleId;
}

const evidenceLabels: Record<string, string> = {
  four_player_tracks_available: "四名球员轨迹可见",
  shuttle_temporal_heatmap_candidate_available: "羽球时序热图候选可见",
  exact_shuttle_contact_not_claimed: "非精确触球证据",
  single_view_2d_rally_proxy: "单机位二维回合代理",
  person_visible: "人物清晰可见",
  racket_visible: "球拍可见",
  arm_raised: "持拍臂抬起",
  arm_extended: "手臂展开",
  racket_above_shoulder: "球拍位于肩线上方",
  racket_waist_to_shoulder: "球拍位于腰部至肩部之间",
  view_front: "正面机位",
  view_side: "侧面机位",
  view_back: "背面机位",
  on_screen_text_present: "画面含字幕或文字",
  on_screen_text_absent: "画面无覆盖文字",
  still_frame_no_motion: "静态帧不能证明连续动作",
  coach_static_demonstration: "教练静态动作示范",
  expanded_racket_side_frame: "展开后的持拍侧框架",
  front_view_only: "仅有正面视角",
  non_official_public_source_research_synthesis: "非官方公开资料研究整理",
  reference_frame_supports_posture_comparison_not_complete_motion: "关键帧只支持姿态对照，不能代替完整动作",
  ordinary_monocular_video_does_not_prove_contact_racket_face_force_or_3d_kinematics: "普通单目视频不能证明精确触球、拍面、力量或三维运动学",
  demonstration_timepoint_requires_manual_review: "部分示范时间点仍需人工复核",
  no_reliable_same_phase_demonstration_frame: "当前没有可靠的同阶段示范帧",
};

export function evidenceTokenLabel(token: string): string {
  if (token.startsWith("module_review_candidate:")) {
    return `${rallyModuleTitle(token.split(":", 2)[1])}模块候选`;
  }
  return evidenceLabels[token] ?? token.split("_").join(" ");
}
