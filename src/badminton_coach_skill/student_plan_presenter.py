"""Chinese-first, bounded presentation for structured coaching plans.

The matching rubrics deliberately keep compact English identifiers and source
wording for auditability.  This module is the separate learner-facing layer:
it never turns those strings into unbounded biomechanical claims and never
falls back to displaying a raw rubric sentence to a learner.
"""

from __future__ import annotations

import re
from typing import Any


# These labels are intentionally maintained separately from the source
# rubrics.  The source rules remain the reviewable technical trace; this map
# is the constrained language a learner is allowed to see.
RULE_LABELS: dict[str, str] = {
    # 李宇轩：准备、到位与释放链
    "lyx-low-ready-racket": "持拍准备位置偏低",
    "lyx-large-drive-preparation": "平抽挡准备幅度过大",
    "lyx-passive-receive": "接球后缺少主动衔接",
    "lyx-unstable-landing": "落地后不利于下一步",
    "lyx-no-recovery": "收拍后没有回到可用位置",
    "lyx-form-only-success": "固定练习能做、连贯对抗会散",
    "lyx-too-many-cues": "一次练习承载了过多调整点",
    "lyx-rushed-release": "准备未稳就急于加快释放",
    "lyx-unsafe-load": "当前负荷不适合继续加量",
    "lyx-missing-prerequisite": "基础动作尚未稳定就加入变化",
    "lyx-short-swing-distance": "可用挥拍距离不足",
    "lyx-collapsed-frame": "肩、肘、拍的准备框架不稳定",
    "lyx-late-trunk-turn": "身体转动没有及时衔接挥拍",
    "lyx-pain": "疼痛或不适需要先降负荷",
    "lyx-late-preparation": "拍和肘的准备偏晚",
    "lyx-telegraphed-preparation": "准备过早暴露了变化意图",
    "lyx-forced-wrist": "手部动作在替代前面的准备",
    "lyx-low-contact": "可见击球窗偏低",
    "lyx-forced-cut": "切削动作是在不稳定条件下硬做出来的",
    "lyx-large-preparation": "快速来球中的准备幅度过大",
    "lyx-late-contact": "拦截窗口已经错过",
    "lyx-late-first-step": "第一步没有跟上来球提示",
    "lyx-passive-third-shot": "发球后的第三拍缺少主动安排",
    "lyx-grip-tension": "可见准备显得过于僵硬",
    "lyx-slow-recovery": "回位无法衔接下一拍",
    "lyx-cramped-contact": "击球空间被挤在身体一侧",
    "lyx-decision-breakdown": "连贯回合中的选择开始失稳",
    "lyx-unstable-base": "基础位置不利于下一次移动",
    "lyx-no-retest": "调整后缺少可观察的复测标准",
    "lyx-unstable-contact": "相似重复中的击球结果不稳定",
    "lyx-delayed-first-step": "看到提示后第一步有迟疑",
    "lyx-forced-release": "释放路径被迫用力带动",
    "lyx-late-start": "启动晚于来球提示",
    "lyx-late-arrival": "到位后没有留下稳定的击球窗",
    "lyx-rear-turn-error": "后场转身与落位没有连成稳定底座",
    "lyx-no-confirmation-step": "击球前缺少最后的确认调整",
    "lyx-contact-behind": "可见击球窗落在头部与身体后方",
    "lyx-low-elbow": "准备时肘部高度不足",
    "lyx-early-tension": "进入击球窗前已经明显紧张",
    "lyx-arm-first-swing": "手臂先于身体转动开始加速",
    "lyx-wrist-first": "手部动作早于肘部引导的路径",
    "lyx-forced-twist": "可见释放路径像在强行扭转",
    "lyx-short-follow-through": "收拍过早停止",
    "lyx-pain-stop": "动作中出现疼痛或不适",
    "lyx-unsafe-floor": "场地、鞋或踝部条件不适合加速移动",
    "lyx-technique-before-equipment": "用器材替代了可见技术问题",
    "lyx-unstable-serve": "发球模式不够可重复",
    "lyx-role-conflict": "双打前两拍的分工不清",
    "lyx-grip-tension-serve": "发接发准备显得过于紧绷",
    # 刘辉：基础动作、步法与击球链
    "backhand-low-contact": "反手击球窗偏低或偏晚",
    "doubles-watch-after-hit": "出球后停在原地观察",
    "body-jammed-spacing": "来球把身体一侧的击球空间挤住",
    "drive-large-preparation": "平抽挡的准备幅度过大",
    "exchange-second-shot-not-ready": "第一拍后没有准备好第二拍",
    "drop-too-slow": "吊球轨迹偏慢或偏高",
    "drop-early-reveal": "吊球意图在击球前暴露",
    "drop-overcut-face": "可见拍面切削过多",
    "drop-direction-mismatch": "已会的一条线路没有迁移到另一条线路",
    "contact-point-too-low": "当前变线所需的击球窗偏低",
    "slide-drop-transfer-fails": "前场的滑拍方式没有迁移到后场被动球",
    "grip-face-mismatch": "准备形态与所选吊球变化不匹配",
    "racket-too-heavy-for-stage": "当前拍重不适合正在练的动作阶段",
    "racket-balance-mismatch": "拍头平衡与当前练习任务不匹配",
    "racket-torsion-mismatch": "相似击球中的拍面稳定性不足",
    "shaft-stiffness-mismatch": "球拍杆响应与当前节奏不匹配",
    "late-arrival": "后场到位偏晚",
    "slow-recovery": "出球后的回位偏慢",
    "rear-foot-orientation-blocks-hip": "后脚朝向限制了转身与蹬转",
    "over-rotated-rear-attack-entry": "后场进攻前的转身幅度过大",
    "foot-switch-cost": "换脚动作拖慢了后场回收",
    "long-ground-contact": "落地触地时间偏长，影响下一步",
    "late-front-arrival": "前场到位偏晚",
    "drill-form-rally-breakdown": "固定练习能做到，实战节奏会散",
    "tactical-context-missing": "现有观察不足以给出战术结论",
    "contact-point-behind": "可见击球窗在头部后方",
    "low-elbow": "准备时肘部没有建立到可用高度",
    "collapsed-racket-structure": "持拍侧准备框架塌陷",
    "late-hip-rotation": "身体转动没有及时衔接挥拍",
    "pronation-whip-misread": "手部加速被放在了动作链前面",
    "short-follow-through": "收拍过早停止",
    "contact-point-too-forward": "击球窗被推得过前，影响自然释放",
    "forced-follow-through": "收拍在被强行带动或强行停住",
    "pain-reported-load-reduction": "疼痛或伤病风险要求先降负荷",
    "receive-large-preparation": "接发球准备幅度过大",
    "deceleration-missing": "出球后的自然减速与收拍不完整",
    "jump-contact-window-missed": "起跳与可用击球窗没有对上",
    "jump-landing-recovery-unstable": "起跳后落地与回收不稳定",
    "standing-frame-not-ready-for-jump": "站地基础框架未稳，不宜进阶起跳",
    "frame-goal-mismatch": "动作框架与当前击球目标不匹配",
    "pro-model-copying": "在复制高成本动作，基础条件尚未稳定",
    "slow-racket-preparation-consumes-window": "举拍准备占用了可用时间窗",
    "heavy-smash-frame-mismatch": "重杀目标与当前动作框架不匹配",
    "body-force-window-too-long": "身体带动持续过久，节奏没有集中",
    "big-arm-dominant-swing": "挥拍主要靠大臂拉动",
    "swing-path-offline": "挥拍路径没有穿过目标击球线",
    "upper-arm-never-stabilizes": "上臂没有形成稳定的衔接点",
    "upper-body-tension": "上身在动作链建立前已明显紧张",
    "fly-swatter-grip-blocks-rotation": "握拍形态限制了可用的挥拍路径",
    "wrist-force-scattered": "手部发力分散，没落在可用窗口内",
    # 郑思维：双打站位、通道与下一拍
    "zsw-serve-without-third-shot-plan": "发球没有连到第三拍安排",
    "zsw-passive-receive-route": "接发线路没有创造下一拍主动性",
    "zsw-flick-serve-cover-late": "挑球后的后场补位偏晚",
    "zsw-front-player-disconnected": "前场队员没有接入后场进攻",
    "zsw-rear-attack-no-continuation": "后场进攻后失去下一拍可用性",
    "zsw-same-lane-rotation-conflict": "轮转时两人进入同一条通道",
    "zsw-opening-role-unclear": "下一拍的负责人与通道不明确",
    "zsw-defense-spacing-collapsed": "防守时双人通道被挤在一起",
    "zsw-no-transition-after-time-gained": "争取到时间后没有及时转换站位",
    "zsw-slow-reset": "回合后没有回到可用的双打分工",
    "zsw-drill-to-rally-breakdown": "固定配合能做，随机回合会失稳",
}

DRILL_LABELS: dict[str, str] = {
    "lyx-split-start-call": "对手触球提示下的启动练习", "lyx-rear-turn-freeze": "后场转身与确认步定格练习", "lyx-high-contact-shadow": "高点击球窗影子练习", "lyx-relaxed-clear-distance": "放松的高远球距离阶梯", "lyx-top-elbow-frame": "肩肘准备框架练习", "lyx-turn-release-chain": "转身到释放的连贯练习", "lyx-smash-five-phase": "五阶段杀球重建", "lyx-grounded-smash-target": "站地杀球目标与出球后回收", "lyx-jump-land-reset": "小幅起跳、落地与复位", "lyx-drop-target-contrast": "吊球目标对比", "lyx-drive-compact-exchange": "紧凑平抽挡连续练习", "lyx-receive-first-attack": "接发到第一拍主动衔接", "lyx-serve-repeatability-grid": "发球落点可重复性练习", "lyx-doubles-two-shot-role": "双打前两拍分工练习", "lyx-backhand-early-choice": "反手提前选择练习", "lyx-rally-transfer-ladder": "从技术练习到回合的迁移阶梯", "lyx-equipment-comfort-log": "器材适配记录练习",
    "rear-court-arrival-shadow": "后场到位影子步", "contact-window-freeze": "前上方击球窗定格", "top-elbow-freeze": "肘部准备定格挥拍", "racket-frame-wall-check": "持拍侧框架靠墙检查", "slow-chain-throw": "慢速身体到肘部衔接练习", "complete-follow-through-line": "自然完整收拍线练习", "front-court-arrival-shadow": "前场到位影子步", "backhand-contact-height-check": "反手击球高度检查", "compact-receive-ready": "紧凑接发准备", "doubles-after-shot-recovery": "双打出球后回位", "drop-disguise-speed-ladder": "吊球隐蔽性节奏阶梯", "drop-face-window-check": "吊球拍面与击球窗检查", "jammed-spacing-reset": "受挤压时的空间重置", "compact-drive-exchange": "紧凑平抽挡连续练习", "pressure-transfer-ladder": "从慢练到回合压力的迁移阶梯", "rally-context-retake": "回合场景补拍", "reduced-load-safety-reset": "低负荷安全重置", "equipment-fit-retest": "器材适配复测", "arm-path-reset": "挥拍路径重置", "deceleration-release-line": "自然减速与收拍线练习", "jump-contact-ladder": "起跳击球窗阶梯", "jump-landing-recovery": "起跳落地与回位", "time-budget-racket-lift": "有限时间内的举拍准备", "compact-standard-frame-freeze": "紧凑基础框架定格", "framework-a-b-selector": "两种动作框架的可控对比", "rear-foot-horizontal-hip-drive": "后脚蹬转与转身练习", "elbow-track-arm-segment-transfer": "肘部轨迹与挥拍衔接", "drop-variant-target-line": "吊球变化与目标线路", "china-jump-short-contact": "短触地节奏练习", "wrist-contact-segmentation": "击球窗内的手部节奏分段",
    "zsw-serve-return-third-shot": "发球、回球与第三拍连贯练习", "zsw-receive-two-exchange": "接发后的两拍线路练习", "zsw-flick-serve-first-step": "短发与挑发的第一步判断", "zsw-front-back-three-ball": "前后场三球压迫练习", "zsw-rear-attack-exit": "后场进攻后的出球与退出路线", "zsw-two-lane-rotation-call": "双通道轮转口令练习", "zsw-role-call-random-feed": "随机来球的分工口令", "zsw-defense-two-channel": "双通道防守练习", "zsw-defense-neutral-attack-ladder": "从防守到转攻的阶梯", "zsw-hit-call-reset": "出球、呼叫与重置", "zsw-rally-transfer-ladder": "双打配合到随机回合的迁移阶梯",
}


def validate_presentation_coverage(knowledge: dict[str, Any]) -> None:
    """Fail early if a newly added rubric has no learner-safe label."""
    rule_ids = {
        str(rule.get("rule_id", ""))
        for rule in knowledge.get("rules", [])
        if isinstance(rule, dict)
    }
    drill_ids = {
        str(drill.get("drill_id", ""))
        for drill in knowledge.get("drills", [])
        if isinstance(drill, dict)
    }
    missing_rules = sorted(rule_ids.difference(RULE_LABELS))
    missing_drills = sorted(drill_ids.difference(DRILL_LABELS))
    if missing_rules or missing_drills:
        parts: list[str] = []
        if missing_rules:
            parts.append("rule labels: " + ", ".join(missing_rules))
        if missing_drills:
            parts.append("drill labels: " + ", ".join(missing_drills))
        raise ValueError("Learner presentation coverage is incomplete (" + "; ".join(parts) + ")")


def _safe_evidence_label(_: str) -> str:
    # Evidence remains visible but is deliberately phrased only as a confirmed
    # structured observation.  Do not leak raw VLM/ASR/rubric wording here.
    return "结构化观察已确认这一可见环节"


def _present_dosage(value: str) -> str:
    numbers = re.findall(r"\d+", value)
    if len(numbers) >= 2:
        return f"{numbers[0]} 组 × {numbers[1]} 次；每组之间按状态充分休息。"
    if numbers:
        return f"完成 {numbers[0]} 次可复拍的稳定重复；状态下降就停止加量。"
    return "采用小组重复练习，保留一次可复拍、可比较的动作。"


def _present_retest(issue_id: str, _: list[str]) -> str:
    explicit = {
        "late-arrival": "同机位复拍后场移动：确认到位是否更及时，并仍能保留下一步回收。",
        "lyx-late-start": "以对手触球为提示复拍：确认第一步是否能在提示后及时出现。",
        "zsw-front-player-disconnected": "连续 10 次后场进攻中，观察前场队员是否能在对手触球前保持拍子可用；目标至少 8 次。",
    }
    return explicit.get(issue_id, "以同一机位和相近来球复拍，确认这一可见环节是否更稳定且能衔接下一拍。")


def present_focus_item(issue: dict[str, Any], topic_unit: dict[str, Any] | None) -> dict[str, Any]:
    """Build the compact Chinese lesson item exposed to learners."""
    issue_id = str(issue.get("issue_id", ""))
    drills = [drill for drill in issue.get("drills", []) if isinstance(drill, dict)]
    first_drill = drills[0] if drills else None
    drill_id = str(first_drill.get("drill_id", "")) if first_drill else ""
    return {
        "issue_id": issue_id,
        "title_zh": RULE_LABELS[issue_id],
        "visible_evidence_zh": [
            _safe_evidence_label(str(item)) for item in issue.get("evidence", [])
        ] or ["当前结构化观察确认了这一动作环节。"],
        "correction_zh": "先把这个可见环节稳定下来，再增加速度、变化或练习强度。",
        "drill": (
            {
                "drill_id": drill_id,
                "title_zh": DRILL_LABELS[drill_id],
                "dosage_zh": _present_dosage(str(first_drill.get("dosage", ""))),
            }
            if first_drill and drill_id in DRILL_LABELS
            else None
        ),
        "retest_zh": _present_retest(issue_id, list(issue.get("retest_metrics", []))),
        "topic_unit": present_topic_unit(topic_unit),
    }


def present_topic_unit(unit: dict[str, Any] | None) -> dict[str, Any] | None:
    if not unit:
        return None
    media_ready = str(unit.get("media_status", "")) == "teaching_ready" and bool(
        unit.get("reviewed_course_ids", [])
    )
    # A topic title can legitimately contain a source-curriculum shorthand
    # such as “内旋”.  In a learner diagnosis it would read like an observed
    # joint-mechanics claim, so keep the teaching scope visible while using a
    # 2D-safe description of the observable movement path.
    learning_goal = str(unit.get("learning_goal_zh", "")).replace("内旋", "身体带动与释放路径")
    return {
        "topic_id": str(unit.get("topic_id", "")),
        "topic_name_zh": str(unit.get("topic_name_zh", "")),
        "learning_goal_zh": learning_goal,
        "knowledge_status": str(unit.get("knowledge_status", "")),
        "media_status": "reviewed_media_available" if media_ready else "knowledge_only_no_reviewed_media",
        "media_notice_zh": "本主题有已审核的连续教练示范。" if media_ready else "本主题目前只提供知识与练习；没有经过主题绑定审核的连续示范，不用其他片段替代。",
    }
