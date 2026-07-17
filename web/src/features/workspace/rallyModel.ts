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
};

export function evidenceTokenLabel(token: string): string {
  if (token.startsWith("module_review_candidate:")) {
    return `${rallyModuleTitle(token.split(":", 2)[1])}模块候选`;
  }
  return evidenceLabels[token] ?? token.split("_").join(" ");
}
