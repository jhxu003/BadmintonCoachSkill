import { useMemo, useState } from "react";
import {
  ArrowRight,
  BookOpenCheck,
  CheckCircle2,
  ChevronRight,
  ExternalLink,
  Film,
  Gauge,
  GitBranch,
  Layers3,
  ShieldCheck,
  Sparkles,
} from "lucide-react";

import "./pages-demo.css";

type CoachId = "liu-hui" | "li-yuxuan" | "zheng-siwei";
type LessonStatus = "complete" | "route" | "context";

interface Stage {
  name: string;
  time: string;
  focus: string;
  boundary: string;
}

interface LessonDemo {
  id: string;
  actionLabel: string;
  focus: string;
  lessonTitle: string;
  lessonStatus: LessonStatus;
  route: Array<{ title: string; copy: string }>;
  source?: { label: string; href: string };
  media?: {
    clip: string;
    keyframes: string[];
    clipDescription: string;
  };
  stages: Stage[];
  note: string;
}

interface CoachDemo {
  id: CoachId;
  name: string;
  role: string;
  actions: string[];
  lessons: LessonDemo[];
}

function publicAsset(path: string): string {
  return `${import.meta.env.BASE_URL}${path}`;
}

function lessonMedia(folder: string, names: string[], description: string): LessonDemo["media"] {
  return {
    clip: `pages-demo/${folder}/action.mp4`,
    keyframes: names.map((name) => `pages-demo/${folder}/keyframes/${name}`),
    clipDescription: description,
  };
}

const liuHuiLessons: LessonDemo[] = [
  {
    id: "high-clear",
    actionLabel: "高远球",
    focus: "后场高远球",
    lessonTitle: "后场高远球：7 阶段连续示范",
    lessonStatus: "complete",
    route: [
      { title: "先看准备", copy: "从观察来球与身体朝向的转换开始，不跳过准备直接模仿挥拍末段。" },
      { title: "再看高位挥拍", copy: "把上举、引拍与挥拍当作一条连续路线理解，而不是孤立摆出某个姿势。" },
      { title: "最后看随挥", copy: "把挥拍后的释放、站稳与下一拍准备放回同一条时间线上检查。" },
    ],
    source: {
      label: "查看原视频：刘辉教练教你怎么打高远球 · 进阶（Bilibili）",
      href: "https://www.bilibili.com/video/BV1Ed4y1s7vj/",
    },
    media: lessonMedia(
      "liu-hui-high-clear",
      ["01-preparation.jpg", "02-start.jpg", "03-arrival.jpg", "04-top-elbow.jpg", "05-contact-window.jpg", "06-follow-through.jpg", "07-recovery.jpg"],
      "6.5 秒连续动作片段：保留完整挥拍及随后的结果段。",
    ),
    stages: [
      { name: "准备", time: "01", focus: "从本段的观察来球与身体朝向开始，再进入这一次高位挥拍。", boundary: "静态帧只用于导航，不能单独代表整套技术。" },
      { name: "启动", time: "02", focus: "观察身体怎样转入本次动作；不要跳过启动直接模仿挥拍末段。", boundary: "普通单目画面不能确定精确启动时机或地面反作用力。" },
      { name: "到位／加载", time: "03", focus: "观察眼线、身体朝向和持拍侧怎样为高位挥拍建立可见的连续路线。", boundary: "仅描述可见二维路线，不推断精确重心或关节角度。" },
      { name: "引拍／高位结构", time: "04", focus: "观察持拍侧在连续画面中的上举和引拍结构，而非孤立模仿定格。", boundary: "不能由普通视频声称真实内旋或精确关节几何。" },
      { name: "近似击球窗口", time: "05", focus: "标记球拍经过头顶附近预期击球区域的连续窗口，并连接到前后的挥拍过程。", boundary: "不声称精确触球、拍面角度、握拍压力或力量大小。" },
      { name: "随挥／释放", time: "06", focus: "观察球拍和身体怎样连续通过近似窗口，不把该窗口当作动作终点。", boundary: "不以单帧判断减速负荷或力量。" },
      { name: "回收／恢复", time: "07", focus: "观察挥拍结束后怎样重新取得稳定、可衔接下一拍的状态。", boundary: "该段不单独证明完整比赛回位路线。" },
    ],
    note: "7 张阶段帧与连续片段来自同一条已审核动作；页面只陈述画面可见的动作路线。",
  },
  {
    id: "smash",
    actionLabel: "杀球",
    focus: "后场重杀",
    lessonTitle: "重杀：准备、起跳、挥拍、落地与恢复",
    lessonStatus: "complete",
    route: [
      { title: "先建立来球下的准备", copy: "先看脚下调整和持拍侧进入位置，不从腾空定格开始倒推动作。" },
      { title: "把加载和起跳连起来", copy: "观察下肢、躯干朝向与持拍侧上举如何连续发生，不拆成互不相干的摆拍。" },
      { title: "击球后必须能落地", copy: "随挥、落地和下一拍准备属于同一个动作包，不能在球拍过顶处截断。" },
    ],
    source: {
      label: "查看原视频：遁地炮杀球有多重？重杀这样打（Bilibili）",
      href: "https://www.bilibili.com/video/BV1p34y1V7qa/",
    },
    media: lessonMedia(
      "liu-hui-smash",
      ["01-preparation.jpg", "02-start.jpg", "03-loading.jpg", "04-takeoff.jpg", "05-contact-window.jpg", "06-landing.jpg", "07-recovery.jpg"],
      "3.5 秒单次重杀：从准备进入起跳，保留随挥、落地和恢复。",
    ),
    stages: [
      { name: "准备", time: "01", focus: "确认来球方向下的站姿、眼线和持拍侧初始位置。", boundary: "不能仅凭这一帧判断最终击球选择或力量。" },
      { name: "启动调整", time: "02", focus: "观察脚下怎样把身体带入后场击球位置。", boundary: "二维画面不能给出精确移动距离和重心轨迹。" },
      { name: "加载／上举", time: "03", focus: "把下肢加载、身体朝向与球拍上举放在同一条连续链里看。", boundary: "不声称精确关节角度或肌肉发力顺序。" },
      { name: "起跳", time: "04", focus: "观察离地前后的整体姿态，以及击球侧如何继续进入高位。", boundary: "单目视频不能测量起跳力、腾空高度或三维位置。" },
      { name: "近似击球窗口", time: "05", focus: "定位球拍经过头顶击球区域的可见窗口，并与前后帧相互验证。", boundary: "不声称精确触球时刻、拍面角度或球速。" },
      { name: "随挥／落地", time: "06", focus: "观察挥拍释放如何连接到落地，而不是在击球附近突然结束。", boundary: "不能由画面推断落地冲击力或伤病风险。" },
      { name: "恢复", time: "07", focus: "确认落地后重新取得可衔接下一拍的姿态。", boundary: "本片段不证明完整比赛中的最佳回位路线。" },
    ],
    note: "本案例选取同一次完整重杀，不混入下一次喂球；球速、精确触球和力量大小均不作推断。",
  },
  {
    id: "slice-drop",
    actionLabel: "吊球",
    focus: "头顶区滑板吊球",
    lessonTitle: "滑板吊球：高位准备、挥拍变化与回收",
    lessonStatus: "complete",
    route: [
      { title: "准备仍然来自高位动作", copy: "先看与其他后场头顶球相似的准备路线，再观察后续可见变化。" },
      { title: "用连续画面看节奏", copy: "关键不是复制某一张拍面定格，而是理解上举、前挥和释放之间的衔接。" },
      { title: "结果之后回到下一拍", copy: "吊球结束后仍要完成随挥和恢复，不能只展示所谓“切”的瞬间。" },
    ],
    source: {
      label: "查看原视频：头顶区滑板吊球教学（Bilibili）",
      href: "https://www.bilibili.com/video/BV1e4421S76x/",
    },
    media: lessonMedia(
      "liu-hui-slice-drop",
      ["01-preparation.jpg", "02-racket-ready.jpg", "03-loading.jpg", "04-forward-swing.jpg", "05-contact-window.jpg", "06-follow-through.jpg", "07-recovery.jpg"],
      "3.5 秒单次滑板吊球示范：保留高位准备、挥拍和恢复。",
    ),
    stages: [
      { name: "准备", time: "01", focus: "观察示范者在动作开始前的站位和球拍初始位置。", boundary: "静态准备帧不能证明与其他后场球完全一致。" },
      { name: "球拍上举", time: "02", focus: "看持拍侧怎样进入头顶区域，为后续挥拍建立连续路线。", boundary: "不从二维画面测量精确肘角和拍面角度。" },
      { name: "加载", time: "03", focus: "观察身体朝向、脚下支撑和持拍侧如何共同进入挥拍前段。", boundary: "不推断真实内旋、握拍压力或肌肉发力。" },
      { name: "前挥", time: "04", focus: "把球拍向前通过的过程与准备相连，不只看最终一帧。", boundary: "运动模糊下不声称拍头的精确三维路径。" },
      { name: "近似击球窗口", time: "05", focus: "标出球拍经过预期击球区的时间窗，用前后帧确认动作连续性。", boundary: "不声称精确触球、切削角度或落点。" },
      { name: "随挥", time: "06", focus: "观察球拍通过窗口后的释放和身体衔接。", boundary: "不能从单帧判断力量大小或减速负荷。" },
      { name: "恢复", time: "07", focus: "确认动作完成后重新取得稳定、可继续移动的状态。", boundary: "片段不包含完整回合，因此不推断战术意图。" },
    ],
    note: "该片段是同一机位下的单次滑板吊球示范；页面不把可见挥拍路线包装成精确拍面或落点数据。",
  },
  {
    id: "backcourt-footwork",
    actionLabel: "后场步法",
    focus: "中国跳后场突击步法",
    lessonTitle: "后场步法：从启动到中国跳，再回到可衔接位置",
    lessonStatus: "complete",
    route: [
      { title: "从中间准备开始", copy: "先看启动前的站位与节奏，避免只模仿最后一步或腾空姿态。" },
      { title: "移动和击球是一条链", copy: "分腿、第一步、后场加载和击球窗口要连续理解，不能各自截图拼接。" },
      { title: "落地后仍要退出", copy: "中国跳不是动作终点；落地、回收和重新面对场地同样属于教学内容。" },
    ],
    source: {
      label: "查看原视频：中国跳突击教学（Bilibili）",
      href: "https://www.bilibili.com/video/BV1NwrrBtEdY/",
    },
    media: lessonMedia(
      "liu-hui-backcourt-footwork",
      ["01-ready.jpg", "02-split-step.jpg", "03-first-step.jpg", "04-loading.jpg", "05-jump-strike-window.jpg", "06-landing.jpg", "07-recovery.jpg"],
      "3.5 秒后场突击步法：从中间启动，保留中国跳、落地和退出。",
    ),
    stages: [
      { name: "中间准备", time: "01", focus: "先确认面对场地的初始状态和可用移动方向。", boundary: "不把画面坐标当作标定后的精确场地坐标。" },
      { name: "分腿／启动", time: "02", focus: "观察脚下节奏怎样为向后场移动建立第一下响应。", boundary: "不能从普通视频测量地面反作用力或反应时。" },
      { name: "第一步", time: "03", focus: "看身体朝向和脚步怎样开始进入后场路线。", boundary: "二维投影不能给出精确步幅和重心高度。" },
      { name: "后场加载", time: "04", focus: "观察到位前的最后调整与下肢加载，而非只看腾空结果。", boundary: "不声称唯一正确脚序，需结合来球与个人条件。" },
      { name: "中国跳／击球窗口", time: "05", focus: "把腾空姿态放回前后步法中，理解它在整条路线里的作用。", boundary: "不声称精确触球、腾空高度或三维身体角度。" },
      { name: "落地", time: "06", focus: "观察身体怎样从腾空过渡到可继续移动的落地状态。", boundary: "画面不能量化冲击负荷或安全阈值。" },
      { name: "退出／恢复", time: "07", focus: "确认落地后继续退出后场并重新组织下一拍。", boundary: "本示范只覆盖一种后场路线，不代表全部后场步法。" },
    ],
    note: "该案例具体展示“中国跳后场突击”，不是用一条路线冒充全部后场步法体系。",
  },
  {
    id: "drive",
    actionLabel: "平抽挡",
    focus: "连续平抽挡与短发力",
    lessonTitle: "平抽挡：紧凑准备、快速出拍与连续回到准备",
    lessonStatus: "complete",
    route: [
      { title: "先保留连续交换", copy: "平抽挡的教学不能只截一张伸拍图；短片保留多次往返，看到每次回弹后的再准备。" },
      { title: "关键帧聚焦一次短动作", copy: "七阶段帧解释其中一次紧凑出拍，连续片段则验证它不是孤立摆拍。" },
      { title: "回弹决定下一拍", copy: "观察出拍后的收回和再次准备，避免把球拍留在身前当作动作结束。" },
    ],
    source: {
      label: "查看原视频：什么是贴拍发力（Bilibili）",
      href: "https://www.bilibili.com/video/BV17t2wYxEF3/",
    },
    media: lessonMedia(
      "liu-hui-drive",
      ["01-ready.jpg", "02-split-step.jpg", "03-short-backswing.jpg", "04-forward-swing.jpg", "05-contact-window.jpg", "06-rebound.jpg", "07-ready-again.jpg"],
      "4.75 秒连续平抽挡：关键帧聚焦第一拍，短片保留后续快速交换。",
    ),
    stages: [
      { name: "准备", time: "01", focus: "观察球拍处于能快速覆盖身前来球的位置。", boundary: "不从单帧判断握拍压力或预判方向。" },
      { name: "分腿／响应", time: "02", focus: "看脚下与上肢怎样共同响应来球，而不是只伸手够球。", boundary: "不能测量真实反应时间或地面受力。" },
      { name: "短引拍", time: "03", focus: "观察紧凑动作中的可见引拍幅度，避免把大幅后摆套入快节奏交换。", boundary: "不声称存在适用于所有来球的固定引拍长度。" },
      { name: "向前出拍", time: "04", focus: "把球拍从准备带向身前击球区，保持动作与脚下节奏相连。", boundary: "运动模糊下不估算精确拍头速度。" },
      { name: "近似击球窗口", time: "05", focus: "定位球拍经过来球区域的窗口，并用连续片段确认前后动作。", boundary: "不声称精确触球、拍面角度、球速或力量。" },
      { name: "回弹／收拍", time: "06", focus: "观察出拍后如何及时回收，而不是让球拍停留在伸展末端。", boundary: "不能由二维画面推断真实制动负荷。" },
      { name: "再次准备", time: "07", focus: "确认第一拍结束后已能进入下一次快速交换。", boundary: "这一帧不单独证明完整对抗中的站位选择。" },
    ],
    note: "连续短片包含多次同类快速交换；七阶段只解释其中同一次短出拍，不跨动作拼帧。",
  },
  {
    id: "backhand",
    actionLabel: "反手",
    focus: "反手被动球处理",
    lessonTitle: "反手被动球：启动、转身、伸展挥拍与恢复",
    lessonStatus: "complete",
    route: [
      { title: "先处理被动到位", copy: "反手被动球先看脚下与身体朝向怎样争取空间，不把教学缩成手腕动作。" },
      { title: "再看伸展挥拍", copy: "把转身、持拍侧加载、向上伸展和释放作为一条连续路线理解。" },
      { title: "示范不等于落点证据", copy: "本片段用于解释动作组织；没有清楚球路时，不虚构精确触球、球速或落点。" },
    ],
    source: {
      label: "查看原视频：反手被动球保姆级教学（Bilibili）",
      href: "https://www.bilibili.com/video/BV1TT411r7Ft/",
    },
    media: lessonMedia(
      "liu-hui-backhand",
      ["01-ready.jpg", "02-start.jpg", "03-loading.jpg", "04-reach.jpg", "05-contact-window.jpg", "06-release.jpg", "07-recovery.jpg"],
      "2.75 秒反手被动球动作示范：保留启动、挥拍和恢复；不虚构球路。",
    ),
    stages: [
      { name: "准备", time: "01", focus: "从可见的站姿和持拍位置开始理解这次反手被动处理。", boundary: "不能从准备帧推断来球速度、落点或选择意图。" },
      { name: "启动", time: "02", focus: "观察脚下和身体朝向怎样开始转入反手侧。", boundary: "二维视频不能给出精确启动时间和移动距离。" },
      { name: "加载／转身", time: "03", focus: "看身体与持拍侧怎样为向上伸展建立空间。", boundary: "不声称精确关节角度、握拍变化或肌肉用力。" },
      { name: "伸展挥拍", time: "04", focus: "观察持拍侧向后上方进入击球区域的连续路线。", boundary: "普通画面不能恢复球拍完整三维轨迹。" },
      { name: "近似击球窗口", time: "05", focus: "标出球拍通过预期击球区的可见窗口，并与相邻帧核对。", boundary: "不声称精确触球、拍面角度、真实内旋或球速。" },
      { name: "释放", time: "06", focus: "观察挥拍通过窗口后的身体与球拍释放。", boundary: "没有清楚球路时，不给出落点和效果判断。" },
      { name: "恢复", time: "07", focus: "确认动作结束后重新取得能够继续移动的状态。", boundary: "该示范不代表所有反手被动球的唯一处理方式。" },
    ],
    note: "专门反手课程中的单次完整示范；由于球路证据不足，页面只教学可见动作路线。",
  },
  {
    id: "serve-receive",
    actionLabel: "发接发",
    focus: "发接发 · 正手发高远球子课",
    lessonTitle: "正手发高远球：准备、放球、前摆与恢复",
    lessonStatus: "complete",
    route: [
      { title: "先固定这一课的范围", copy: "“发接发”是技术家族；本公开案例只展示正手发高远球，不冒充完整接发教学。" },
      { title: "把持球与挥拍连起来", copy: "从站姿、持球、放球到球拍前摆连续观察，避免只模仿击球附近一帧。" },
      { title: "发出后重新准备", copy: "球离开后仍要完成随挥和恢复，连接到下一拍，而不是停在发球动作里。" },
    ],
    source: {
      label: "查看原视频：正手发高远球教学（Bilibili）",
      href: "https://www.bilibili.com/video/BV1Xoe9zkEVT/",
    },
    media: lessonMedia(
      "liu-hui-serve-receive",
      ["01-stance.jpg", "02-set.jpg", "03-release.jpg", "04-forward-swing.jpg", "05-contact-window.jpg", "06-flight.jpg", "07-recovery.jpg"],
      "3.25 秒单次正手发高远球：保留准备、放球、挥拍、球路结果和恢复。",
    ),
    stages: [
      { name: "站姿准备", time: "01", focus: "观察发球前的身体朝向、持拍手与持球手关系。", boundary: "不把二维站位当作精确场地测量。" },
      { name: "持球／设定", time: "02", focus: "确认球与球拍在动作开始前的可见相对位置。", boundary: "不从画面判断握拍压力或法规尺度上的精确高度。" },
      { name: "放球启动", time: "03", focus: "观察持球手释放与球拍开始前摆之间的连续衔接。", boundary: "普通视频不能给出精确放球时刻或球体三维轨迹。" },
      { name: "球拍前摆", time: "04", focus: "看球拍怎样从准备位置向前通过预期击球区域。", boundary: "运动模糊下不估算拍头速度或精确拍面。" },
      { name: "近似击球窗口", time: "05", focus: "定位球拍与球最接近的可见时间窗，并结合前后帧理解。", boundary: "不声称精确触球、拍面角度、力量或球速。" },
      { name: "球路结果", time: "06", focus: "用连续片段观察球离开后的可见飞行方向，同时保持结论克制。", boundary: "未标定机位不能计算精确高度、速度或落点。" },
      { name: "恢复", time: "07", focus: "观察发球动作结束后怎样重新组织身体与球拍，准备下一拍。", boundary: "本子课没有展示接发方完整技术，不能替代接发教学。" },
    ],
    note: "该案例属于“发接发”家族中的正手发高远球子课；接发球技术仍需独立、可靠来源。",
  },
];

const coaches: CoachDemo[] = [
  {
    id: "liu-hui",
    name: "刘辉",
    role: "动作框架、发力路线与训练选择",
    actions: liuHuiLessons.map((lesson) => lesson.actionLabel),
    lessons: liuHuiLessons,
  },
  {
    id: "li-yuxuan",
    name: "李宇轩",
    role: "时间预算、到位与动作链衔接",
    actions: ["高远球", "杀球", "吊球", "后场步法", "平抽挡", "反手", "发接发"],
    lessons: [
      {
        id: "arrival-chain",
        actionLabel: "高远球",
        focus: "后场到位与高远球",
        lessonTitle: "先处理时间与到位，再进入挥拍细节",
        lessonStatus: "route",
        route: [
          { title: "来球信号", copy: "先把启动与第一步放在技术讨论之前，明确时间从哪里被消耗。" },
          { title: "到位与调整", copy: "把转身、调整步与击球窗口视为一条连续链，而不是独立问题。" },
          { title: "释放与退出", copy: "在稳定到位后，再讨论顶肘、架拍、释放与回位之间的取舍。" },
        ],
        stages: [
          { name: "信号与启动", time: "01", focus: "从来球信号开始组织第一步。", boundary: "示例不替代实际视频的可见性审核。" },
          { name: "到位与转身", time: "02", focus: "保证击球前有可用空间。", boundary: "不从静态展示判断精确距离。" },
          { name: "击球窗口", time: "03", focus: "在可观察的窗口内组织架拍与释放。", boundary: "不推断精确触球。" },
          { name: "退出与回位", time: "04", focus: "把动作结束连接到下一拍准备。", boundary: "需结合连续素材复核。" },
        ],
        note: "Pages 仅展示可公开的 Skill 路线。实际视频教学包只在素材满足连续性与阶段证据标准时才会发布到受保护服务。",
      },
    ],
  },
  {
    id: "zheng-siwei",
    name: "郑思维",
    role: "混双通道、衔接与轮转复盘",
    actions: ["接发与第三拍", "前场压迫", "后场进攻", "轮转", "防守转换", "回位迁移"],
    lessons: [
      {
        id: "mixed-doubles-context",
        actionLabel: "接发与第三拍",
        focus: "混双进攻衔接",
        lessonTitle: "混双不是两个人的单人动作相加",
        lessonStatus: "context",
        route: [
          { title: "确认四人", copy: "先由用户确认学员、搭档、对手和场地角，系统不根据外观猜身份。" },
          { title: "检查两条通道", copy: "复盘前后连接、可达线路与下一拍归属，而不是给单帧贴战术意图。" },
          { title: "保留不确定性", copy: "四人、边线或羽球不可见时，返回重拍指引，不编造轮转结论。" },
        ],
        stages: [
          { name: "发球与开局", time: "01", focus: "建立回合开始时的角色与站位背景。", boundary: "不推断发球意图。" },
          { name: "接发与交换", time: "02", focus: "检查下一拍是否已有角色准备。", boundary: "需要完整回合上下文。" },
          { name: "前后连接", time: "03", focus: "观察两人是否保持可用通道。", boundary: "不把二维投影当作精确场地坐标。" },
          { name: "转换与回位", time: "04", focus: "复核下一拍归属是否重新建立。", boundary: "缺少连续性时只给重拍建议。" },
        ],
        note: "该体系的公开展示只说明混双复盘方法。完整四人视频分析需要后端、受保护的上传媒体和用户确认步骤。",
      },
    ],
  },
];

const statusCopy: Record<LessonStatus, string> = {
  complete: "连续课程结构示例",
  route: "Skill 教学路线示例",
  context: "回合复盘方法示例",
};

export function PagesDemo() {
  const [coachId, setCoachId] = useState<CoachId>("liu-hui");
  const [lessonIndex, setLessonIndex] = useState(0);
  const [stageIndex, setStageIndex] = useState(0);
  const coach = useMemo(() => coaches.find((item) => item.id === coachId)!, [coachId]);
  const lesson = coach.lessons[lessonIndex] ?? coach.lessons[0];
  const stage = lesson.stages[stageIndex] ?? lesson.stages[0];
  const stageAsset = lesson.media?.keyframes[stageIndex];

  function selectCoach(nextCoach: CoachId): void {
    setCoachId(nextCoach);
    setLessonIndex(0);
    setStageIndex(0);
  }

  function selectLesson(index: number): void {
    setLessonIndex(index);
    setStageIndex(0);
  }

  return (
    <main className="pages-demo">
      <header className="pages-nav">
        <a className="pages-brand" href="#top" aria-label="BadmintonCoachSkill 首页"><span aria-hidden="true" />BadmintonCoach<span>Skill</span></a>
        <nav aria-label="页面导航"><a href="#experience">体验</a><a href="#systems">教练体系</a><a href="#boundaries">证据边界</a><a href="https://github.com/jhxu003/BadmintonCoachSkill" target="_blank" rel="noreferrer">GitHub <ExternalLink size={13} /></a></nav>
      </header>

      <section id="top" className="pages-hero">
        <div>
          <p className="pages-eyebrow"><Sparkles size={14} /> Evidence-grounded coaching intelligence</p>
          <h1>把一条教练视频，<br /><em>变成可复查的教学路线。</em></h1>
          <p className="pages-lede">这是 BadmintonCoachSkill 的公开展示版。选择教练体系与技术主题，查看连续动作如何被组织成阶段导航、教学要点与明确的证据边界。</p>
          <div className="pages-hero-actions"><a className="pages-primary" href="#experience">浏览刘辉七项案例 <ArrowRight size={17} /></a><a className="pages-secondary" href="https://github.com/jhxu003/BadmintonCoachSkill" target="_blank" rel="noreferrer">查看源代码</a></div>
        </div>
        <aside className="pages-hero-card" aria-label="教学证据结构">
          <div className="pages-card-top"><span>Lesson container</span><span>public-safe demo</span></div>
          <div className="pages-lesson-line"><b>01</b><span>连续动作片段</span><i /></div>
          <div className="pages-lesson-line"><b>02</b><span>七阶段姿态导航</span><i /></div>
          <div className="pages-lesson-line"><b>03</b><span>教学原则与练习</span><i /></div>
          <div className="pages-lesson-line"><b>04</b><span>可见事实与不确定性</span><i /></div>
          <p><ShieldCheck size={15} /> 关键帧用于解释，连续片段用于验证</p>
        </aside>
      </section>

      <section className="pages-stat-row" aria-label="项目规模摘要">
        <div><b>3</b><span>教练体系</span></div><div><b>823</b><span>公开来源索引</span></div><div><b>5,496</b><span>教学时间窗</span></div><div><b>110</b><span>诊断规则</span></div>
      </section>

      <section id="systems" className="pages-section pages-systems">
        <div className="pages-section-heading"><p className="pages-eyebrow">Coach systems</p><h2>一套教练知识，不是一张“标准姿势”图。</h2><p>不同教练体系解决不同的问题；页面不会把它们混成同一套万能动作。</p></div>
        <div className="pages-coach-tabs" role="tablist" aria-label="选择教练体系">
          {coaches.map((item) => <button key={item.id} type="button" role="tab" aria-selected={coach.id === item.id} className={coach.id === item.id ? "active" : ""} onClick={() => selectCoach(item.id)}><span>{item.name}</span><small>{item.role}</small><ChevronRight size={16} /></button>)}
        </div>
      </section>

      <section id="experience" className="pages-section pages-case">
        <div className="pages-case-heading"><div><p className="pages-eyebrow"><Film size={14} /> Interactive course case</p><h2>{coach.name} · {lesson.focus}</h2><p>{lesson.lessonTitle}</p></div><span className={`pages-status ${lesson.lessonStatus}`}>{statusCopy[lesson.lessonStatus]}</span></div>
        <div className="pages-action-list" role={coach.lessons.length > 1 ? "tablist" : undefined} aria-label="该体系覆盖的技术主题">
          {coach.actions.map((action, index) => coach.lessons.length > 1 ? <button key={action} type="button" role="tab" aria-selected={lessonIndex === index} className={lessonIndex === index ? "selected" : ""} onClick={() => selectLesson(index)}>{action}</button> : <span className={index === 0 ? "selected" : ""} key={action}>{action}</span>)}
        </div>
        <div className="pages-route-grid">{lesson.route.map((item, index) => <article key={item.title}><b>{String(index + 1).padStart(2, "0")}</b><h3>{item.title}</h3><p>{item.copy}</p></article>)}</div>
        <div className="pages-motion-panel">
          <div className="pages-motion-copy"><p className="pages-eyebrow"><Layers3 size={14} /> Action package</p><h3>完整教学先保留过程，<br />再用关键帧解释过程。</h3><p>每一个阶段帧都来自同一次连续动作；一旦机位、可见性或连续性不够，系统就保留“证据不足”。</p><div className="pages-motion-labels"><span><Film size={15} /> 连续片段</span><span><Gauge size={15} /> 阶段导航</span></div></div>
          {lesson.media ? <div className="pages-motion-media"><video key={lesson.id} controls playsInline preload="metadata" poster={publicAsset(lesson.media.keyframes[0])}><source src={publicAsset(lesson.media.clip)} type="video/mp4" /></video><p>{lesson.media.clipDescription}</p></div> : <div className="pages-court-visual" aria-hidden="true"><div className="pages-court-lines" /><div className="pages-player"><i /><b /><span /></div><div className="pages-path"><i /><i /><i /><i /><i /><i /><i /></div><div className="pages-flight" /></div>}
        </div>

        <div className="pages-stage-section"><div className="pages-stage-heading"><div><p className="pages-eyebrow">Ordered stage navigation</p><h3>选择一个阶段，查看它在连续动作里的教学角色。</h3></div><span>不是孤立的标准姿势</span></div><div className="pages-stage-rail" role="tablist" aria-label="动作阶段">{lesson.stages.map((item, index) => <button key={item.name} type="button" role="tab" aria-selected={stageIndex === index} className={stageIndex === index ? "active" : ""} onClick={() => setStageIndex(index)}>{lesson.media && <img src={publicAsset(lesson.media.keyframes[index])} alt="" />}<b>{item.time}</b><span>{item.name}</span></button>)}</div><article className={`pages-stage-detail ${stageAsset ? "has-media" : ""}`}>{stageAsset ? <div className="pages-stage-visual"><img src={publicAsset(stageAsset)} alt={`${coach.name}${lesson.focus}：${stage.name}关键帧`} /><b>{stage.time}</b></div> : <div className="pages-stage-number">{stage.time}</div>}<div><p className="pages-eyebrow">{stage.name}</p><h3>{stage.focus}</h3><p><strong>证据边界：</strong>{stage.boundary}</p></div><CheckCircle2 aria-hidden="true" /></article></div>

        <div className="pages-case-footer"><p><ShieldCheck size={17} /> {lesson.note}</p>{lesson.source ? <a href={lesson.source.href} target="_blank" rel="noreferrer">{lesson.source.label} <ExternalLink size={15} /></a> : <span>此公开展示不包含媒体副本或未验证课程。</span>}</div>
      </section>

      <section id="boundaries" className="pages-section pages-boundaries"><div className="pages-section-heading"><p className="pages-eyebrow">Evidence boundaries</p><h2>知道什么，也明确不知道什么。</h2></div><div className="pages-boundary-grid"><article><b>可以做</b><p>组织公开视频中的连续动作、阶段顺序、可见姿态事实、教学原则、练习和复测指标。</p></article><article><b>不能声称</b><p>精确触球、拍面角度、真实内旋、握拍压力、力量大小、标定三维运动学或对手意图。</p></article><article><b>证据不足时</b><p>不编造诊断；标记缺失阶段，说明需要怎样的机位、画面或重拍条件。</p></article></div></section>

      <section className="pages-cta"><BookOpenCheck size={28} /><div><p className="pages-eyebrow">Open source project</p><h2>查看 Skill、证据合同与完整部署方案。</h2><p>完整服务需要私有 runtime、GPU 后端和受令牌保护的媒体接口；GitHub Pages 只包含所有者明确允许公开的刘辉七项审核案例。</p></div><a className="pages-primary" href="https://github.com/jhxu003/BadmintonCoachSkill" target="_blank" rel="noreferrer">打开 GitHub <ExternalLink size={16} /></a></section>

      <footer className="pages-footer"><span>BadmintonCoachSkill · 非官方、非授权研究项目</span><a href="https://github.com/jhxu003/BadmintonCoachSkill" target="_blank" rel="noreferrer"><GitBranch size={14} /> GitHub Repository</a></footer>
    </main>
  );
}
