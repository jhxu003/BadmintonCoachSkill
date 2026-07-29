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
    reviewStatus: string;
  };
  stages: Stage[];
  note: string;
}

interface TechniqueSystem {
  title: string;
  description: string;
  lessonIds: string[];
}

interface CoachDemo {
  id: CoachId;
  name: string;
  role: string;
  lessons: LessonDemo[];
  systems: TechniqueSystem[];
}

function publicAsset(path: string): string {
  return `${import.meta.env.BASE_URL}${path}`;
}

function lessonMedia(folder: string, names: string[], description: string): LessonDemo["media"] {
  return {
    clip: `pages-demo/${folder}/action.mp4`,
    keyframes: names.map((name) => `pages-demo/${folder}/keyframes/${name}`),
    clipDescription: description,
    reviewStatus: "教练身份已确认 · 正确示范语境已确认",
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
      "4.25 秒教练第一种滑板吊球示范：保留准备、挥拍、结果确认和恢复。",
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
    note: "已替换旧的对比模仿段；当前片段是教练在讲清隐蔽性后亲自完成并确认结果的第一种滑板吊球示范。",
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
    focus: "平抽挡短发力",
    lessonTitle: "平抽挡：紧凑准备、快速出拍与回到准备",
    lessonStatus: "complete",
    route: [
      { title: "只保留同一拍", copy: "连续短片从准备开始，到同一次紧凑出拍完成并重新准备为止，不混入后续击球。" },
      { title: "关键帧解释完整过程", copy: "七阶段帧全部落在这一次动作内，用于导航准备、短引拍、出拍和收回。" },
      { title: "回弹连接下一拍", copy: "观察出拍后的收回和再次准备，避免把球拍留在身前当作动作结束。" },
    ],
    source: {
      label: "查看原视频：什么是贴拍发力（Bilibili）",
      href: "https://www.bilibili.com/video/BV17t2wYxEF3/",
    },
    media: lessonMedia(
      "liu-hui-drive",
      ["01-ready.jpg", "02-split-step.jpg", "03-short-backswing.jpg", "04-forward-swing.jpg", "05-contact-window.jpg", "06-rebound.jpg", "07-ready-again.jpg"],
      "2.25 秒单次平抽挡短出拍：连续覆盖准备、出拍、回弹和再次准备，并在下一拍前结束。",
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
    note: "旧的多拍窗口已收紧；当前连续短片和七阶段都只对应同一次短出拍。",
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
      "2 秒反手被动球动作示范：关键帧收紧到启动、挥拍和恢复，不再把前后说话帧当成动作阶段。",
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
    focus: "发接发 · 正手发高远球纠正子课",
    lessonTitle: "正手发高远球：转拍与随摆纠正示范",
    lessonStatus: "complete",
    route: [
      { title: "先指出被纠正的问题", copy: "周边课程先指出学员转拍过慢、手臂继续上抬和随摆次序不清，本片段只承担对应纠正教学。" },
      { title: "只看教练的慢动作路线", copy: "七阶段全部来自黑衣教练同一次徒手挥拍，不混入前后的女学员尝试。" },
      { title: "不冒充完整发球", copy: "片段没有完整持球、放球和清楚触球，因此只教学可见转拍与随摆路线。" },
    ],
    source: {
      label: "查看原视频：正手发高远球教学（Bilibili）",
      href: "https://www.bilibili.com/video/BV1Xoe9zkEVT/",
    },
    media: lessonMedia(
      "liu-hui-serve-receive",
      ["01-coach-ready.jpg", "02-rotation-start.jpg", "03-forward-path.jpg", "04-acceleration.jpg", "05-high-swing-window.jpg", "06-follow-through.jpg", "07-recovery.jpg"],
      "3 秒教练慢动作纠正示范：只展示可见转拍、前摆、随摆和回收，不冒充带球发球。",
    ),
    stages: [
      { name: "教练接管示范", time: "01", focus: "确认当前主示范者已经切换为黑衣教练，并从慢动作准备开始。", boundary: "角色确认来自周边课程语境，不根据衣着自动猜身份。" },
      { name: "转拍启动", time: "02", focus: "观察教练所讲的转拍动作怎样先于后续随摆启动。", boundary: "“转拍”只描述画面和课程术语，不声称测得真实肩内旋。" },
      { name: "低位前摆", time: "03", focus: "看持拍侧从低位向前通过的连续路线，不混入学员此前的慢转错误。", boundary: "徒手示范不包含放球、触球或法规高度证据。" },
      { name: "加速通过", time: "04", focus: "结合相邻帧理解挥拍怎样连续通过身体前侧。", boundary: "运动模糊下不估算拍头速度、拍面或力量。" },
      { name: "高位随摆窗口", time: "05", focus: "观察球拍通过后手臂继续进入高位随摆，而不是把手臂提前僵住。", boundary: "该帧不是触球帧，也不能证明球路结果。" },
      { name: "随摆完成", time: "06", focus: "确认转拍之后仍有连续随摆动作，和学员此前被指出的次序问题区分开。", boundary: "普通单目画面不能量化关节旋转或减速负荷。" },
      { name: "回收", time: "07", focus: "观察慢动作示范怎样结束并回到可继续讲解的稳定状态。", boundary: "该段没有完整发球和接发方，不能替代完整发接发课程。" },
    ],
    note: "旧页面误用了女学员正在被纠正的尝试；现已替换为教练慢动作纠正示范，并明确降窄为转拍与随摆子课。",
  },
];

const liYuxuanLessons: LessonDemo[] = [
  {
    id: "high-clear",
    actionLabel: "高远球",
    focus: "后场高远球",
    lessonTitle: "正确语境中的单次高远球：准备、挥拍与恢复",
    lessonStatus: "complete",
    route: [
      { title: "先确认示范语境", copy: "课程已从问题动作说明切换到正确方法，不能把此前的错误模仿当成参考。" },
      { title: "看完整的一次挥拍", copy: "从步下准备进入上举、加载、挥拍和随挥，七帧全部来自同一次重复。" },
      { title: "恢复后才结束", copy: "动作包保留释放后的站稳与回收，并在下一次正确重复开始前结束。" },
    ],
    source: {
      label: "查看原视频：高远球打不到位？转身挥拍老发不上力？（Bilibili）",
      href: "https://www.bilibili.com/video/BV1Z64y1F7Ys",
    },
    media: lessonMedia(
      "li-yuxuan-high-clear",
      ["01-preparation.jpg", "02-start.jpg", "03-loading.jpg", "04-acceleration.jpg", "05-contact-window.jpg", "06-follow-through.jpg", "07-recovery.jpg"],
      "2.375 秒正确高远球重复：从准备连续覆盖挥拍、随挥和恢复。",
    ),
    stages: [
      { name: "准备", time: "01", focus: "观察身体与持拍侧怎样进入本次正确示范的稳定起点。", boundary: "准备帧不单独证明来球、距离或最终击球选择。" },
      { name: "启动", time: "02", focus: "看脚下和身体朝向怎样开始组织头顶动作。", boundary: "不从二维画面测量精确启动时间或重心轨迹。" },
      { name: "加载", time: "03", focus: "观察持拍侧上举和身体转入挥拍前段的连续关系。", boundary: "不声称精确关节角度、握拍压力或真实内旋。" },
      { name: "加速", time: "04", focus: "把向上向前的挥拍过程连接到此前准备，而非模仿孤立定格。", boundary: "运动模糊下不估算拍头速度或力量。" },
      { name: "近似击球窗口", time: "05", focus: "标记球拍经过预期高位击球区域的可见窗口。", boundary: "不声称精确触球、拍面角度、球速或落点。" },
      { name: "随挥", time: "06", focus: "观察球拍与身体如何连续通过近似窗口并释放。", boundary: "不能从单帧量化减速负荷或发力比例。" },
      { name: "恢复", time: "07", focus: "确认挥拍后重新取得可继续移动的稳定状态。", boundary: "该短片不代表所有来球下的唯一回位路线。" },
    ],
    note: "旧的 448 秒候选属于问题动作模仿，已明确隔离；当前页面只发布 154.875–157.250 秒的正确示范。",
  },
  {
    id: "drive",
    actionLabel: "平抽挡",
    focus: "紧凑平抽挡",
    lessonTitle: "同一次短出拍：准备、通过与再次可用",
    lessonStatus: "complete",
    route: [
      { title: "先保持可响应准备", copy: "快速交换不是从大幅后摆开始，先看球拍与身体能否及时进入这一次出拍。" },
      { title: "短路线连续通过", copy: "七阶段把启动、稳定支撑、短引拍和向前通过放在同一条时间线上。" },
      { title: "下一拍之前结束", copy: "片段在同一次出拍完成并回收后结束，不借用下一拍补齐动作阶段。" },
    ],
    source: {
      label: "查看原视频：抽球没力量、球总减速怎么办？（Bilibili）",
      href: "https://www.bilibili.com/video/BV1Bh411T7TR",
    },
    media: lessonMedia(
      "li-yuxuan-drive",
      ["01-ready.jpg", "02-start.jpg", "03-stable-position.jpg", "04-short-backswing.jpg", "05-contact-window.jpg", "06-release.jpg", "07-recovery.jpg"],
      "1.6 秒单次紧凑平抽挡：没有混入下一次击球。",
    ),
    stages: [
      { name: "准备", time: "01", focus: "观察球拍、躯干和支撑是否处于可快速响应的状态。", boundary: "不能由准备帧推断来球速度或预判方向。" },
      { name: "启动", time: "02", focus: "看持拍侧怎样从准备进入本次短出拍。", boundary: "不量化真实反应时间或肌肉激活顺序。" },
      { name: "稳定击球位", time: "03", focus: "观察原地快速交换中的可见支撑和身体朝向。", boundary: "这不是跨场到位距离或精确重心的测量。" },
      { name: "短引拍", time: "04", focus: "看引拍怎样保持紧凑并连接后续向前动作。", boundary: "不把一条示范固化为所有来球的唯一引拍长度。" },
      { name: "近似击球窗口", time: "05", focus: "定位球拍通过身前来球区域的连续窗口。", boundary: "不声称精确触球、拍面角度、球速或力量。" },
      { name: "释放", time: "06", focus: "观察出拍后怎样自然通过，而不是停在伸展末端。", boundary: "普通视频不能量化制动负荷。" },
      { name: "恢复", time: "07", focus: "确认球拍和身体已经回到可衔接下一拍的状态。", boundary: "不据此推断完整对抗中的最佳站位。" },
    ],
    note: "公开窗口只对应同一次短出拍；媒体和七帧在下一次击球开始前已经结束。",
  },
  {
    id: "net-lunge",
    actionLabel: "网前跨步",
    focus: "网前上网跨步与回收",
    lessonTitle: "从准备中心到网前，再回到可衔接状态",
    lessonStatus: "complete",
    route: [
      { title: "先从准备中心启动", copy: "不要先伸手够球；先看脚下怎样把身体送向网前。" },
      { title: "跨步与处理相连", copy: "到位、下沉和近似处理窗口是连续过程，不把最低点单独当成标准姿势。" },
      { title: "处理后必须回收", copy: "片段保留网前动作后的站稳与退出，只教学可见移动路线。" },
    ],
    source: {
      label: "查看原视频：挑球怎么轻松挑得又高又到位？（Bilibili）",
      href: "https://www.bilibili.com/video/BV1MibBz5E9U",
    },
    media: lessonMedia(
      "li-yuxuan-net-lunge",
      ["01-ready-center.jpg", "02-start.jpg", "03-front-arrival.jpg", "04-lunge-loading.jpg", "05-processing-window.jpg", "06-release.jpg", "07-recovery.jpg"],
      "3.04 秒网前上网跨步：连续覆盖准备、到位、处理附近与回收。",
    ),
    stages: [
      { name: "准备中心", time: "01", focus: "从稳定中心观察双脚、躯干与持拍侧的可启动状态。", boundary: "不把画面坐标当作标定后的场地坐标。" },
      { name: "启动", time: "02", focus: "观察第一步怎样把身体送向网前。", boundary: "不能从单目画面测量精确步幅或地面受力。" },
      { name: "前场到位", time: "03", focus: "看身体怎样接近可下沉、可处理来球的位置。", boundary: "不声称存在适用于所有来球的固定到位距离。" },
      { name: "跨步加载", time: "04", focus: "观察跨步、下沉与持拍准备怎样连续发生。", boundary: "不推断精确关节角度、重心高度或伤病风险。" },
      { name: "近似处理窗口", time: "05", focus: "标出球拍经过网前可见处理区域的窗口。", boundary: "不声称精确触球、拍面角度或具体挑球落点。" },
      { name: "释放", time: "06", focus: "观察处理后的身体与球拍怎样离开最低点。", boundary: "不能由单帧判断力量、旋转或触球质量。" },
      { name: "回收", time: "07", focus: "确认动作后重新站稳并准备衔接下一拍。", boundary: "短片只覆盖一次网前路线，不代表完整回合回位。" },
    ],
    note: "该案例只称为“网前上网跨步与回收”，不把可见移动路线冒充完整挑球手法。",
  },
];

const zhengSiweiLessons: LessonDemo[] = [
  {
    id: "receive-cut-waist",
    actionLabel: "接发切腰",
    focus: "发球偏高时的接发处理",
    lessonTitle: "读球、侧向启动、处理与回收",
    lessonStatus: "complete",
    route: [
      { title: "先读发球高度", copy: "课程把这一动作放在对方发球偏高的条件下，不把它扩写为所有接发球的固定答案。" },
      { title: "身体先进入路线", copy: "观察郑思维怎样从准备向侧前方移动，让球拍进入可处理区域。" },
      { title: "处理后保持可用", copy: "动作包一直保留到回收，不在近似击球窗口处截断。" },
    ],
    source: {
      label: "查看原视频：羽球思维第一期 · 接发球教学（Bilibili）",
      href: "https://www.bilibili.com/video/BV11o4ZePEPt",
    },
    media: lessonMedia(
      "zheng-siwei-receive-cut-waist",
      ["01-ready.jpg", "02-read.jpg", "03-start.jpg", "04-lunge.jpg", "05-contact-window.jpg", "06-release.jpg", "07-recovery.jpg"],
      "2 秒单次接发切腰示范：正面机位连续覆盖准备、侧向处理与回收。",
    ),
    stages: [
      { name: "准备", time: "01", focus: "确认接发前的站姿、眼线和球拍可用位置。", boundary: "不从单帧推断发球意图或反应时间。" },
      { name: "读球", time: "02", focus: "观察身体在动作发生前仍保持可向两侧响应。", boundary: "课程语境提供条件，画面本身不能证明对手意图。" },
      { name: "启动", time: "03", focus: "看脚下与身体怎样开始进入侧前方路线。", boundary: "二维视频不能给出精确移动距离或重心轨迹。" },
      { name: "跨步", time: "04", focus: "观察身体怎样接近身侧处理区域并保持平衡。", boundary: "不把该跨步固化为所有来球的唯一脚序。" },
      { name: "近似击球窗口", time: "05", focus: "定位球拍经过球体附近的可见时间窗。", boundary: "不声称精确触球、拍面、切削角或球速。" },
      { name: "释放", time: "06", focus: "观察处理后球拍和身体怎样继续通过。", boundary: "不能从普通画面判断真实力量或落点精度。" },
      { name: "恢复", time: "07", focus: "确认动作后回到可继续覆盖下一拍的位置。", boundary: "本片段不证明完整双打第三拍归属。" },
    ],
    note: "该示范只适用于课程明确的较高发球条件；其他发球高度仍需重新选择路线。",
  },
  {
    id: "left-receive-route",
    actionLabel: "左半场接发",
    focus: "左半场接发后的本侧衔接",
    lessonTitle: "一次接发移动，保留到回到下一拍准备",
    lessonStatus: "complete",
    route: [
      { title: "先建立本次分工", copy: "课程在此进入左半场接发套路，页面只复现这一条示范路线。" },
      { title: "接发后继续向前", copy: "观察启动、接近来球和处理后的继续移动，不把击球当成终点。" },
      { title: "角色规则不硬编码", copy: "来源标题中的性别表述不被推成所有搭档都必须遵守的固定角色规则。" },
    ],
    source: {
      label: "查看原视频：男生在左半场的几种接发球套路（Bilibili）",
      href: "https://www.bilibili.com/video/BV1SAtTewEbs",
    },
    media: lessonMedia(
      "zheng-siwei-left-receive-route",
      ["01-ready.jpg", "02-start.jpg", "03-approach.jpg", "04-loading.jpg", "05-contact-window.jpg", "06-follow-through.jpg", "07-recovery.jpg"],
      "4.5 秒单次接发与衔接路线：从准备保留到重新可用。",
    ),
    stages: [
      { name: "准备", time: "01", focus: "观察接发者面对发球方时的初始位置和可用方向。", boundary: "不从外观自动识别固定混双角色。" },
      { name: "启动", time: "02", focus: "看身体怎样从等待状态开始响应来球。", boundary: "不量化反应时、地面受力或发球意图。" },
      { name: "接近", time: "03", focus: "观察脚下怎样把身体送向身前处理区域。", boundary: "二维投影不能提供精确场地距离。" },
      { name: "加载", time: "04", focus: "看下肢支撑与持拍侧怎样为处理建立空间。", boundary: "不声称精确关节几何或握拍变化。" },
      { name: "近似击球窗口", time: "05", focus: "标出球拍经过来球附近的连续窗口。", boundary: "不声称精确触球、拍面角度、球速或落点。" },
      { name: "继续移动", time: "06", focus: "观察接发后身体仍然向可衔接区域推进。", boundary: "不能从该片段判断搭档和对手的全部战术意图。" },
      { name: "恢复", time: "07", focus: "确认本次路线结束时已经能准备下一拍。", boundary: "完整轮转仍需四人连续回合证据。" },
    ],
    note: "这是一条左半场接发实例，不是按性别固定前后场或两侧职责的通用规则。",
  },
  {
    id: "net-drop",
    actionLabel: "贴网吊球",
    focus: "贴网吊球的连续手法路线",
    lessonTitle: "隔离一次抛球示范，不跨入下一次重复",
    lessonStatus: "complete",
    route: [
      { title: "先保留来球与准备", copy: "从抛球后的稳定准备开始，避免只截取球拍经过头顶的一瞬间。" },
      { title: "用连续画面理解路线", copy: "加载、前挥、近似处理和随挥均来自同一次动作。" },
      { title: "下一次抛球前结束", copy: "重复训练中的每一次都单独审核，页面没有把两次动作拼成一个故事板。" },
    ],
    source: {
      label: "查看原视频：更简单学会贴网的吊球（Bilibili）",
      href: "https://www.bilibili.com/video/BV1bpN8eMEL5",
    },
    media: lessonMedia(
      "zheng-siwei-net-drop",
      ["01-ready.jpg", "02-start.jpg", "03-loading.jpg", "04-acceleration.jpg", "05-contact-window.jpg", "06-follow-through.jpg", "07-recovery.jpg"],
      "2.5 秒单次抛球示范：完整保留准备、挥拍与回收。",
    ),
    stages: [
      { name: "准备", time: "01", focus: "观察球拍和身体怎样等待本次抛起的羽球。", boundary: "准备帧不能证明最终落点或切削选择。" },
      { name: "启动", time: "02", focus: "看持拍侧怎样从准备进入头顶处理路线。", boundary: "不从二维视频推断肌肉发力顺序。" },
      { name: "加载", time: "03", focus: "观察上举与可见加载怎样连接后续挥拍。", boundary: "不声称精确肘角、拍面角或真实内旋。" },
      { name: "加速", time: "04", focus: "把球拍向前通过的过程放回完整动作中理解。", boundary: "运动模糊下不估算拍头速度或力量。" },
      { name: "近似击球窗口", time: "05", focus: "标记球拍与羽球接近的可见时间窗。", boundary: "不声称精确触球、切削角、旋转或落点。" },
      { name: "随挥", time: "06", focus: "观察球拍通过窗口后的释放路线。", boundary: "不能由单帧判断触球质量或减速负荷。" },
      { name: "恢复", time: "07", focus: "确认动作结束并在下一次抛球前回到稳定状态。", boundary: "原地手法示范不代表完整后场步法。" },
    ],
    note: "该窗口只包含一次抛球练习；下一次重复从媒体与关键帧中同时排除。",
  },
  {
    id: "rear-attack-footwork",
    actionLabel: "后场突击步法",
    focus: "正手区后场突击与恢复",
    lessonTitle: "第一条喂球：启动、后移、腾空、落地与恢复",
    lessonStatus: "complete",
    route: [
      { title: "从中间准备读球", copy: "先看脚下怎样响应喂球，再进入正手区后场路线。" },
      { title: "移动和突击是一条链", copy: "后移、加载、腾空和近似击球窗口不能拆成互不相关的定格。" },
      { title: "第二次喂球不混入", copy: "片段在第一条动作恢复后结束，后续重复另行审核。" },
    ],
    source: {
      label: "查看原视频：正手区后场突击步伐（Bilibili）",
      href: "https://www.bilibili.com/video/BV1iLCnYvEhw",
    },
    media: lessonMedia(
      "zheng-siwei-rear-attack-footwork",
      ["01-ready.jpg", "02-start.jpg", "03-loading.jpg", "04-acceleration.jpg", "05-contact-window.jpg", "06-landing.jpg", "07-recovery.jpg"],
      "2.75 秒第一条实战喂球：覆盖后移突击、落地和恢复。",
    ),
    stages: [
      { name: "准备", time: "01", focus: "确认面对来球的初始站姿和可移动方向。", boundary: "不把画面坐标当作精确场地测量。" },
      { name: "启动", time: "02", focus: "观察脚下怎样开始进入正手后场路线。", boundary: "不能测量真实反应时或地面反作用力。" },
      { name: "后场加载", time: "03", focus: "看后移后的支撑、身体朝向和持拍侧怎样共同加载。", boundary: "不声称唯一正确脚序或精确关节角度。" },
      { name: "加速／腾空", time: "04", focus: "观察身体与球拍如何继续进入突击动作。", boundary: "单目视频不能测量腾空高度、力量或三维位置。" },
      { name: "近似击球窗口", time: "05", focus: "定位球拍经过头顶预期击球区的可见窗口。", boundary: "不声称精确触球、拍面、球速或落点。" },
      { name: "落地", time: "06", focus: "观察腾空动作怎样连接到可继续移动的落地。", boundary: "不能量化落地冲击或伤病风险。" },
      { name: "恢复", time: "07", focus: "确认第一条喂球后重新建立准备状态。", boundary: "短片不证明完整比赛中的最佳回位选择。" },
    ],
    note: "七帧与连续片段均来自第一条实战喂球，并在第二次喂球开始前结束。",
  },
  {
    id: "rear-pressure-retreat",
    actionLabel: "被压后场退步",
    focus: "受压后的后场移动与处理",
    lessonTitle: "问题对比之后，只发布正确退步路线",
    lessonStatus: "complete",
    route: [
      { title: "先区分问题段", copy: "课程前段展示后仰和脚下缠结的问题，本案例不使用那些画面。" },
      { title: "按可见顺序组织", copy: "读球、启动、压低身体、出步伐和处理被保留为同一条连续路线。" },
      { title: "恢复仍属动作包", copy: "挥拍后继续观察落地与站稳，不把近似击球窗口当作结束。" },
    ],
    source: {
      label: "查看原视频：被压后场来不及退怎么办？（Bilibili）",
      href: "https://www.bilibili.com/video/BV1auRDY3Ept",
    },
    media: lessonMedia(
      "zheng-siwei-rear-pressure-retreat",
      ["01-ready.jpg", "02-read.jpg", "03-start.jpg", "04-loading.jpg", "05-contact-window.jpg", "06-release.jpg", "07-recovery.jpg"],
      "3.875 秒正确退步路线：已排除前段错误对比。",
    ),
    stages: [
      { name: "准备", time: "01", focus: "观察身体面对来球时的稳定起点。", boundary: "不能由静态帧推断来球速度或对手意图。" },
      { name: "读球", time: "02", focus: "看身体保持可响应，并准备进入后退路线。", boundary: "不声称测得真实视觉反应时间。" },
      { name: "启动", time: "03", focus: "观察第一下后退响应怎样建立方向。", boundary: "不从二维画面量化步幅或重心。" },
      { name: "压低与加载", time: "04", focus: "看身体降低、支撑和持拍侧如何为后续处理创造空间。", boundary: "不声称精确关节角度、受力或伤病阈值。" },
      { name: "近似击球窗口", time: "05", focus: "标记后退中球拍经过预期处理区域的窗口。", boundary: "不声称精确触球、拍面角度、球速或力量。" },
      { name: "释放", time: "06", focus: "观察挥拍通过窗口后怎样连接落地。", boundary: "不能由单帧判断出球质量或战术结果。" },
      { name: "恢复", time: "07", focus: "确认处理后重新取得可继续移动的状态。", boundary: "本示范不代表所有被动后场球的唯一选择。" },
    ],
    note: "前段错误示范保持隔离；公开 Case 只来自随后明确组织的正确移动路线。",
  },
  {
    id: "backhand-low-transition",
    actionLabel: "反手低手位过渡",
    focus: "反手底线低手位过渡",
    lessonTitle: "固定机位中的单次移动、处理与回收",
    lessonStatus: "complete",
    route: [
      { title: "镜头切换后再开始", copy: "片段从固定全身机位开始，避免把上一镜头的动作尾部误当作准备。" },
      { title: "低手位处理要连贯", copy: "移动、跨步、低手位挥拍和随挥均来自同一次连续动作。" },
      { title: "路线选择保留条件", copy: "本案例展示过渡对角的可见动作，不把它说成所有被动球的唯一答案。" },
    ],
    source: {
      label: "查看原视频：反手底线低手位过渡对角（Bilibili）",
      href: "https://www.bilibili.com/video/BV1fxijBKEZc",
    },
    media: lessonMedia(
      "zheng-siwei-backhand-low-transition",
      ["01-ready.jpg", "02-start.jpg", "03-lunge.jpg", "04-loading.jpg", "05-contact-window.jpg", "06-follow-through.jpg", "07-recovery.jpg"],
      "2.2 秒固定机位示范：从准备连续覆盖低手位处理与回收。",
    ),
    stages: [
      { name: "准备", time: "01", focus: "确认固定机位下的稳定站姿和可移动方向。", boundary: "不由静态帧推断来球落点或选择意图。" },
      { name: "启动", time: "02", focus: "观察脚下怎样开始进入反手低手位路线。", boundary: "二维视频不能量化反应时或精确移动距离。" },
      { name: "跨步", time: "03", focus: "看身体怎样接近较低的处理区域并保持支撑。", boundary: "不声称唯一正确脚序或重心高度。" },
      { name: "加载", time: "04", focus: "观察持拍侧与下肢支撑怎样连接低手位挥拍。", boundary: "不推断精确握拍、关节角度或肌肉发力。" },
      { name: "近似击球窗口", time: "05", focus: "标出球拍与羽球接近的可见时间窗。", boundary: "不声称精确触球、拍面、旋转、球速或落点。" },
      { name: "随挥", time: "06", focus: "观察处理后球拍和身体怎样继续通过。", boundary: "不能由单帧确认实际过渡效果。" },
      { name: "恢复", time: "07", focus: "确认动作后重新取得可移动的稳定状态。", boundary: "路线选择仍需结合来球和回合上下文。" },
    ],
    note: "公开窗口从固定机位开始并在下一次剪辑前结束，没有把镜头切换两侧拼成一条动作。",
  },
];

const coaches: CoachDemo[] = [
  {
    id: "liu-hui",
    name: "刘辉",
    role: "动作框架、发力路线与训练选择",
    lessons: liuHuiLessons,
    systems: [
      { title: "后场头顶体系", description: "从到位、加载到挥拍释放，把高远、杀球和吊球放在同一条后场动作链里理解。", lessonIds: ["high-clear", "smash", "slice-drop"] },
      { title: "步法与快速交换", description: "后场进入、落地退出与平抽挡短动作，共同服务于下一拍可衔接性。", lessonIds: ["backcourt-footwork", "drive"] },
      { title: "反手与发接发纠正", description: "针对被动处理和发接发中的可见次序问题，强调条件与动作边界。", lessonIds: ["backhand", "serve-receive"] },
    ],
  },
  {
    id: "li-yuxuan",
    name: "李宇轩",
    role: "时间预算、到位与动作链衔接",
    lessons: liYuxuanLessons,
    systems: [
      { title: "后场头顶体系", description: "把准备、加载、加速、随挥和恢复作为一条连续的后场高位动作链。", lessonIds: ["high-clear"] },
      { title: "中前场快速交换", description: "以紧凑平抽挡为例，组织准备、短出拍和再次准备的时间预算。", lessonIds: ["drive"] },
      { title: "网前到位与回收", description: "从中心启动、上网跨步到离开最低点，强调动作完成后的可继续移动性。", lessonIds: ["net-lunge"] },
    ],
  },
  {
    id: "zheng-siwei",
    name: "郑思维",
    role: "混双通道、衔接与轮转复盘",
    lessons: zhengSiweiLessons,
    systems: [
      { title: "接发与本侧衔接", description: "接发切腰与左半场路线展示条件下的启动、处理与本侧延续。", lessonIds: ["receive-cut-waist", "left-receive-route"] },
      { title: "前后场处理", description: "贴网吊球、后场突击和受压退步分别呈现前后场的可见动作路线。", lessonIds: ["net-drop", "rear-attack-footwork", "rear-pressure-retreat"] },
      { title: "反手低位过渡", description: "在固定机位中组织低手位移动、处理与恢复，不把一次示范扩张为通用战术结论。", lessonIds: ["backhand-low-transition"] },
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
  const activeSystem = coach.systems.find((system) => system.lessonIds.includes(lesson.id)) ?? coach.systems[0];
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
          <div className="pages-hero-actions"><a className="pages-primary" href="#experience">浏览三套教练案例 <ArrowRight size={17} /></a><a className="pages-secondary" href="https://github.com/jhxu003/BadmintonCoachSkill" target="_blank" rel="noreferrer">查看源代码</a></div>
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
        <div><b>3</b><span>教练体系</span></div><div><b>873</b><span>已解析来源视频</span></div><div><b>16</b><span>公开审核案例</span></div><div><b>7</b><span>每例阶段导航</span></div>
      </section>

      <section id="systems" className="pages-section pages-systems">
        <div className="pages-section-heading"><p className="pages-eyebrow">Coach systems</p><h2>一套教练知识，不是一张“标准姿势”图。</h2><p>不同教练体系解决不同的问题；页面不会把它们混成同一套万能动作。</p></div>
        <div className="pages-coach-tabs" role="tablist" aria-label="选择教练体系">
          {coaches.map((item) => <button key={item.id} type="button" role="tab" aria-selected={coach.id === item.id} className={coach.id === item.id ? "active" : ""} onClick={() => selectCoach(item.id)}><span>{item.name}</span><small>{item.role}</small><ChevronRight size={16} /></button>)}
        </div>
      </section>

      <section id="experience" className="pages-section pages-case">
        <div className="pages-case-heading"><div><p className="pages-eyebrow"><Film size={14} /> Interactive course case</p><h2>{coach.name} · {lesson.focus}</h2><p>{lesson.lessonTitle}</p></div><span className={`pages-status ${lesson.lessonStatus}`}>{statusCopy[lesson.lessonStatus]}</span></div>
        <div className="pages-taxonomy" aria-label={`${coach.name}技术体系分类`}>
          <div className="pages-taxonomy-heading"><p className="pages-eyebrow">Technique systems</p><p>当前模块：<b>{activeSystem.title}</b>。先选体系模块，再进入其中的公开动作案例。</p></div>
          <div className="pages-taxonomy-grid">
            {coach.systems.map((system) => <section key={system.title} className={system === activeSystem ? "active" : ""}><h3>{system.title}</h3><p>{system.description}</p><div role="tablist" aria-label={`${system.title}动作案例`}>{system.lessonIds.map((lessonId) => {
              const itemIndex = coach.lessons.findIndex((item) => item.id === lessonId);
              const item = coach.lessons[itemIndex];
              return item ? <button key={item.id} type="button" role="tab" aria-selected={lessonIndex === itemIndex} className={lessonIndex === itemIndex ? "selected" : ""} onClick={() => selectLesson(itemIndex)}>{item.actionLabel}</button> : null;
            })}</div></section>)}
          </div>
        </div>
        <div className="pages-route-grid">{lesson.route.map((item, index) => <article key={item.title}><b>{String(index + 1).padStart(2, "0")}</b><h3>{item.title}</h3><p>{item.copy}</p></article>)}</div>
        <div className="pages-motion-panel">
          <div className="pages-motion-copy"><p className="pages-eyebrow"><Layers3 size={14} /> Action package</p><h3>完整教学先保留过程，<br />再用关键帧解释过程。</h3><p>每一个阶段帧都来自同一次连续动作；一旦机位、可见性或连续性不够，系统就保留“证据不足”。</p><div className="pages-motion-labels"><span><Film size={15} /> 连续片段</span><span><Gauge size={15} /> 阶段导航</span></div></div>
          {lesson.media ? <div className="pages-motion-media"><video key={lesson.id} controls playsInline preload="metadata" poster={publicAsset(lesson.media.keyframes[0])}><source src={publicAsset(lesson.media.clip)} type="video/mp4" /></video><div className="pages-motion-caption"><span><ShieldCheck size={13} /> {lesson.media.reviewStatus}</span><p>{lesson.media.clipDescription}</p></div></div> : <div className="pages-court-visual" aria-hidden="true"><div className="pages-court-lines" /><div className="pages-player"><i /><b /><span /></div><div className="pages-path"><i /><i /><i /><i /><i /><i /><i /></div><div className="pages-flight" /></div>}
        </div>

        <div className="pages-stage-section"><div className="pages-stage-heading"><div><p className="pages-eyebrow">Ordered stage navigation</p><h3>选择一个阶段，查看它在连续动作里的教学角色。</h3></div><span>不是孤立的标准姿势</span></div><div className="pages-stage-rail" role="tablist" aria-label="动作阶段">{lesson.stages.map((item, index) => <button key={item.name} type="button" role="tab" aria-selected={stageIndex === index} className={stageIndex === index ? "active" : ""} onClick={() => setStageIndex(index)}>{lesson.media && <img src={publicAsset(lesson.media.keyframes[index])} alt="" />}<b>{item.time}</b><span>{item.name}</span></button>)}</div><article className={`pages-stage-detail ${stageAsset ? "has-media" : ""}`}>{stageAsset ? <div className="pages-stage-visual"><img src={publicAsset(stageAsset)} alt={`${coach.name}${lesson.focus}：${stage.name}关键帧`} /><b>{stage.time}</b></div> : <div className="pages-stage-number">{stage.time}</div>}<div><p className="pages-eyebrow">{stage.name}</p><h3>{stage.focus}</h3><p><strong>证据边界：</strong>{stage.boundary}</p></div><CheckCircle2 aria-hidden="true" /></article></div>

        <div className="pages-case-footer"><p><ShieldCheck size={17} /> {lesson.note}</p>{lesson.source ? <a href={lesson.source.href} target="_blank" rel="noreferrer">{lesson.source.label} <ExternalLink size={15} /></a> : <span>此公开展示不包含媒体副本或未验证课程。</span>}</div>
      </section>

      <section id="boundaries" className="pages-section pages-boundaries"><div className="pages-section-heading"><p className="pages-eyebrow">Evidence boundaries</p><h2>知道什么，也明确不知道什么。</h2></div><div className="pages-boundary-grid"><article><b>可以做</b><p>组织公开视频中的连续动作、阶段顺序、可见姿态事实、教学原则、练习和复测指标。</p></article><article><b>不能声称</b><p>精确触球、拍面角度、真实内旋、握拍压力、力量大小、标定三维运动学或对手意图。</p></article><article><b>证据不足时</b><p>不编造诊断；标记缺失阶段，说明需要怎样的机位、画面或重拍条件。</p></article></div></section>

      <section className="pages-cta"><BookOpenCheck size={28} /><div><p className="pages-eyebrow">Open source project</p><h2>查看 Skill、证据合同与完整部署方案。</h2><p>完整服务需要私有 runtime、GPU 后端和受令牌保护的媒体接口；GitHub Pages 只包含所有者明确允许且逐条审核的 16 个教练案例。</p></div><a className="pages-primary" href="https://github.com/jhxu003/BadmintonCoachSkill" target="_blank" rel="noreferrer">打开 GitHub <ExternalLink size={16} /></a></section>

      <footer className="pages-footer"><span>BadmintonCoachSkill · 非官方、非授权研究项目</span><a href="https://github.com/jhxu003/BadmintonCoachSkill" target="_blank" rel="noreferrer"><GitBranch size={14} /> GitHub Repository</a></footer>
    </main>
  );
}
