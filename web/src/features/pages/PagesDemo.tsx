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

interface Stage {
  name: string;
  time: string;
  focus: string;
  boundary: string;
}

interface CoachDemo {
  id: CoachId;
  name: string;
  role: string;
  focus: string;
  actions: string[];
  lessonTitle: string;
  lessonStatus: "complete" | "route" | "context";
  route: Array<{ title: string; copy: string }>;
  source?: { label: string; href: string };
  stages: Stage[];
  note: string;
}

const coaches: CoachDemo[] = [
  {
    id: "liu-hui",
    name: "刘辉",
    role: "动作框架、发力路线与训练选择",
    focus: "后场高远球",
    actions: ["高远球", "杀球", "吊球", "后场步法", "平抽挡", "反手", "发接发"],
    lessonTitle: "从后场到回位的高远球教学包",
    lessonStatus: "complete",
    route: [
      { title: "先到位", copy: "先建立启动、后退与支撑，避免在失衡状态里追求挥拍速度。" },
      { title: "再架拍", copy: "用连续动作理解侧身、引拍与架拍之间的衔接，而非孤立摆姿势。" },
      { title: "最后回位", copy: "把随挥、落地和下一拍准备放回同一条动作时间线上检查。" },
    ],
    source: {
      label: "查看原视频：刘辉教练教你正手发高远球（Bilibili）",
      href: "https://www.bilibili.com/video/BV1ym411g74x/",
    },
    stages: [
      { name: "启动与后退", time: "01", focus: "先识别来球方向，再以可控的启动和后退进入后场。", boundary: "静态阶段只用于定位，不能判断真实启动时机。" },
      { name: "最后两步与制动", time: "02", focus: "在击球前取得稳定支撑，为上肢动作保留空间。", boundary: "不从单目画面推断精确重心、力量或地面反作用力。" },
      { name: "侧身与引拍", time: "03", focus: "让身体和持拍侧逐步组织动作，不把手臂单独向后拉。", boundary: "可描述画面中的相对位置，不能声称真实关节旋转。" },
      { name: "架拍", time: "04", focus: "在加速前建立适合自己的持拍侧准备结构。", boundary: "不能从普通视频确定握拍压力或拍面精确角度。" },
      { name: "挥拍加速", time: "05", focus: "观察躯干、上肢与球拍路径的连续释放。", boundary: "这里是近似击球窗口，不宣称精确触球瞬间。" },
      { name: "随挥与落地", time: "06", focus: "让释放自然延续到落地，避免在动作峰值突然刹停。", boundary: "不以单帧判断力量大小或伤病风险。" },
      { name: "回位与下一拍", time: "07", focus: "完成出拍后恢复可移动状态，准备下一次来球。", boundary: "回位质量须结合连续片段，而非一张姿态图。" },
    ],
    note: "这是公开安全的课程结构示例。完整连续片段、阶段关键帧与其审核记录只在受保护的运行环境中按需提供。",
  },
  {
    id: "li-yuxuan",
    name: "李宇轩",
    role: "时间预算、到位与动作链衔接",
    focus: "后场到位与高远球",
    actions: ["高远球", "杀球", "吊球", "后场步法", "平抽挡", "反手", "发接发"],
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
  {
    id: "zheng-siwei",
    name: "郑思维",
    role: "混双通道、衔接与轮转复盘",
    focus: "混双进攻衔接",
    actions: ["接发与第三拍", "前场压迫", "后场进攻", "轮转", "防守转换", "回位迁移"],
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
];

const statusCopy = {
  complete: "连续课程结构示例",
  route: "Skill 教学路线示例",
  context: "回合复盘方法示例",
};

export function PagesDemo() {
  const [coachId, setCoachId] = useState<CoachId>("liu-hui");
  const [stageIndex, setStageIndex] = useState(0);
  const coach = useMemo(() => coaches.find((item) => item.id === coachId)!, [coachId]);
  const stage = coach.stages[stageIndex] ?? coach.stages[0];

  function selectCoach(nextCoach: CoachId): void {
    setCoachId(nextCoach);
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
          <div className="pages-hero-actions"><a className="pages-primary" href="#experience">浏览刘辉案例 <ArrowRight size={17} /></a><a className="pages-secondary" href="https://github.com/jhxu003/BadmintonCoachSkill" target="_blank" rel="noreferrer">查看源代码</a></div>
        </div>
        <aside className="pages-hero-card" aria-label="教学证据结构">
          <div className="pages-card-top"><span>Lesson container</span><span>public-safe demo</span></div>
          <div className="pages-lesson-line"><b>01</b><span>连续动作片段</span><i /></div>
          <div className="pages-lesson-line"><b>02</b><span>七阶段姿态导航</span><i /></div>
          <div className="pages-lesson-line"><b>03</b><span>教学原则与练习</span><i /></div>
          <div className="pages-lesson-line"><b>04</b><span>可见事实与不确定性</span><i /></div>
          <p><ShieldCheck size={15} /> 三帧用于定位，连续阶段用于理解</p>
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
        <div className="pages-case-heading"><div><p className="pages-eyebrow"><Film size={14} /> Interactive course case</p><h2>{coach.name} · {coach.focus}</h2><p>{coach.lessonTitle}</p></div><span className={`pages-status ${coach.lessonStatus}`}>{statusCopy[coach.lessonStatus]}</span></div>
        <div className="pages-action-list" aria-label="该体系覆盖的技术主题">{coach.actions.map((action, index) => <span className={index === 0 ? "selected" : ""} key={action}>{action}</span>)}</div>
        <div className="pages-route-grid">{coach.route.map((item, index) => <article key={item.title}><b>{String(index + 1).padStart(2, "0")}</b><h3>{item.title}</h3><p>{item.copy}</p></article>)}</div>
        <div className="pages-motion-panel">
          <div className="pages-motion-copy"><p className="pages-eyebrow"><Layers3 size={14} /> Action package</p><h3>完整教学先保留过程，<br />再用关键帧解释过程。</h3><p>真实课程中，每一个阶段帧都来自同一次连续动作；一旦机位、可见性或连续性不够，系统就保留“证据不足”。</p><div className="pages-motion-labels"><span><Film size={15} /> 连续片段</span><span><Gauge size={15} /> 阶段导航</span></div></div>
          <div className="pages-court-visual" aria-hidden="true"><div className="pages-court-lines" /><div className="pages-player"><i /><b /><span /></div><div className="pages-path"><i /><i /><i /><i /><i /><i /><i /></div><div className="pages-flight" /></div>
        </div>

        <div className="pages-stage-section"><div className="pages-stage-heading"><div><p className="pages-eyebrow">Ordered stage navigation</p><h3>选择一个阶段，查看它在连续动作里的教学角色。</h3></div><span>不是孤立的标准姿势</span></div><div className="pages-stage-rail" role="tablist" aria-label="动作阶段">{coach.stages.map((item, index) => <button key={item.name} type="button" role="tab" aria-selected={stageIndex === index} className={stageIndex === index ? "active" : ""} onClick={() => setStageIndex(index)}><b>{item.time}</b><span>{item.name}</span></button>)}</div><article className="pages-stage-detail"><div className="pages-stage-number">{stage.time}</div><div><p className="pages-eyebrow">{stage.name}</p><h3>{stage.focus}</h3><p><strong>证据边界：</strong>{stage.boundary}</p></div><CheckCircle2 aria-hidden="true" /></article></div>

        <div className="pages-case-footer"><p><ShieldCheck size={17} /> {coach.note}</p>{coach.source ? <a href={coach.source.href} target="_blank" rel="noreferrer">{coach.source.label} <ExternalLink size={15} /></a> : <span>此公开展示不包含媒体副本或未验证课程。</span>}</div>
      </section>

      <section id="boundaries" className="pages-section pages-boundaries"><div className="pages-section-heading"><p className="pages-eyebrow">Evidence boundaries</p><h2>知道什么，也明确不知道什么。</h2></div><div className="pages-boundary-grid"><article><b>可以做</b><p>组织公开视频中的连续动作、阶段顺序、可见姿态事实、教学原则、练习和复测指标。</p></article><article><b>不能声称</b><p>精确触球、拍面角度、真实内旋、握拍压力、力量大小、标定三维运动学或对手意图。</p></article><article><b>证据不足时</b><p>不编造诊断；标记缺失阶段，说明需要怎样的机位、画面或重拍条件。</p></article></div></section>

      <section className="pages-cta"><BookOpenCheck size={28} /><div><p className="pages-eyebrow">Open source project</p><h2>查看 Skill、证据合同与完整部署方案。</h2><p>完整服务需要私有 runtime、GPU 后端和受令牌保护的媒体接口；这些内容不会进入 GitHub Pages。</p></div><a className="pages-primary" href="https://github.com/jhxu003/BadmintonCoachSkill" target="_blank" rel="noreferrer">打开 GitHub <ExternalLink size={16} /></a></section>

      <footer className="pages-footer"><span>BadmintonCoachSkill · 非官方、非授权研究项目</span><a href="https://github.com/jhxu003/BadmintonCoachSkill" target="_blank" rel="noreferrer"><GitBranch size={14} /> GitHub Repository</a></footer>
    </main>
  );
}
