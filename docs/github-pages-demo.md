# GitHub Pages 展示版

GitHub Pages 部署的是一个**纯静态、公开安全的产品展示**，地址为：

<https://jhxu003.github.io/BadmintonCoachSkill/>

它展示三套教练 Skill，以及 16 个逐条审核的可切换课程案例、动作阶段导航和证据边界。页面不包含或请求以下内容：

- `.runtime` 中的审核媒体、课程清单、缓存、数据库或访问令牌；
- 上传的学员视频、关键帧、动作包、模型权重或日志；
- 完整 API、GPU 推理、Celery、TTL 清理或访问控制能力。

## 浏览体验

公开首页以一段真实、已审核的教练连续示范开始。访客可按教练体系选择 16 节动作课，再通过同一次动作的 7 个阶段帧定位准备、挥拍、近似击球窗口和恢复。阶段帧只用于定位和讲解，不表示页面掌握了未公开的逐帧时间码，也不会声称精确跳转或精确触球。

下方技术库保留 873 条来源视频的原始标题、体系分类和原平台链接；它们是元数据目录，不等同于包含连续片段与阶段帧的 16 节公开动作课。页面只会在客户端按教练、体系模块和标题筛选，并分页显示结果。

## 十六个公开媒体例外

项目所有者于 2026-07-28 明确批准把以下 16 个案例用于公开 Pages 展示。它们是 Git 唯一跟踪的教练抽取媒体：

| 教练 | 技术 | 原始公开来源 | 公开连续窗口 | 发布目录 |
|---|---|---|---:|---|
| 刘辉 | 高远球 | [BV1Ed4y1s7vj](https://www.bilibili.com/video/BV1Ed4y1s7vj/) | 120.00–126.50 秒 | `liu-hui-high-clear/` |
| 刘辉 | 杀球 | [BV1p34y1V7qa](https://www.bilibili.com/video/BV1p34y1V7qa/) | 121.00–124.50 秒 | `liu-hui-smash/` |
| 刘辉 | 吊球 | [BV1e4421S76x](https://www.bilibili.com/video/BV1e4421S76x/) | 266.25–270.50 秒 | `liu-hui-slice-drop/` |
| 刘辉 | 后场步法 | [BV1NwrrBtEdY](https://www.bilibili.com/video/BV1NwrrBtEdY/) | 173.75–177.25 秒 | `liu-hui-backcourt-footwork/` |
| 刘辉 | 平抽挡 | [BV17t2wYxEF3](https://www.bilibili.com/video/BV17t2wYxEF3/) | 119.00–121.25 秒 | `liu-hui-drive/` |
| 刘辉 | 反手 | [BV1TT411r7Ft](https://www.bilibili.com/video/BV1TT411r7Ft/) | 287.50–289.50 秒 | `liu-hui-backhand/` |
| 刘辉 | 发接发 · 正手发高远球转拍与随摆纠正子课 | [BV1Xoe9zkEVT](https://www.bilibili.com/video/BV1Xoe9zkEVT/) | 1343.75–1346.75 秒 | `liu-hui-serve-receive/` |
| 李宇轩 | 高远球 | [BV1Z64y1F7Ys](https://www.bilibili.com/video/BV1Z64y1F7Ys) | 154.875–157.250 秒 | `li-yuxuan-high-clear/` |
| 李宇轩 | 平抽挡 | [BV1Bh411T7TR](https://www.bilibili.com/video/BV1Bh411T7TR) | 721.340–722.940 秒 | `li-yuxuan-drive/` |
| 李宇轩 | 网前跨步与回收 | [BV1MibBz5E9U](https://www.bilibili.com/video/BV1MibBz5E9U) | 477.060–480.100 秒 | `li-yuxuan-net-lunge/` |
| 郑思维 | 接发切腰 | [BV11o4ZePEPt](https://www.bilibili.com/video/BV11o4ZePEPt) | 45.750–47.750 秒 | `zheng-siwei-receive-cut-waist/` |
| 郑思维 | 左半场接发衔接 | [BV1SAtTewEbs](https://www.bilibili.com/video/BV1SAtTewEbs) | 71.750–76.250 秒 | `zheng-siwei-left-receive-route/` |
| 郑思维 | 贴网吊球 | [BV1bpN8eMEL5](https://www.bilibili.com/video/BV1bpN8eMEL5) | 180.250–182.750 秒 | `zheng-siwei-net-drop/` |
| 郑思维 | 正手后场突击步法 | [BV1iLCnYvEhw](https://www.bilibili.com/video/BV1iLCnYvEhw) | 162.500–165.250 秒 | `zheng-siwei-rear-attack-footwork/` |
| 郑思维 | 被压后场退步 | [BV1auRDY3Ept](https://www.bilibili.com/video/BV1auRDY3Ept) | 51.625–55.500 秒 | `zheng-siwei-rear-pressure-retreat/` |
| 郑思维 | 反手低手位过渡 | [BV1fxijBKEZc](https://www.bilibili.com/video/BV1fxijBKEZc) | 81.050–83.250 秒 | `zheng-siwei-backhand-low-transition/` |

每个目录包含 1 段 H.264 连续动作片段、7 张来自同一动作的有序关键帧、来源说明和 `review.json`。审核记录必须同时证明示范者是教练、课程语境将其作为正确示范，并给出动作前后各至少 20 秒的审核语境；缺少任一项时导出脚本会拒绝发布。

刘辉吊球旧窗口属于教练模仿另一种打法的对比段，现已替换为教练讲清隐蔽性后亲自完成并确认结果的第一种滑板吊球。发接发旧窗口属于女学员正在被纠正的尝试，现已替换为黑衣教练的慢动作纠正示范；因为没有完整持球、放球和清楚触球，页面只将它称为“转拍与随摆纠正子课”，不冒充完整发球或接发教学。刘辉平抽挡旧窗口包含多次击球、但关键帧只解释第一拍，现已收紧为同一次短出拍的 2.25 秒窗口，并在下一拍前结束。

李宇轩高远球旧候选位于问题动作模仿语境，未发布；软压／轻杀的未完成窗口和跨越多次喂球的勾对角窗口也保持隔离。郑思维六个案例只使用官方教学语境中由本人完成的单次正确示范；比赛回放、他人主示范、正误不可分、动作不完整或跨越重复的候选均不发布。

这些文件仅用于带原平台归属的可视化展示，不构成发布任何其他来源视频、完整原片、私有 runtime 缓存、学员上传、模型输出、数据库、日志或令牌的授权。任何新增媒体都需要单独的所有者明确授权与来源审阅。

完整视频证据产品仍按 [视频网页部署文档](video-evidence-web-app.md) 在受保护的 API 与 GPU 环境中运行。Pages 不应被当作完整服务的替代品。

## 发布

推送 `main` 且修改 `web/**` 或 `.github/workflows/deploy-pages.yml` 时，`Deploy public demo to GitHub Pages` 工作流会自动构建并部署。首次部署后，仓库管理员需要在 GitHub 仓库 **Settings → Pages** 确认 Source 为 **GitHub Actions**。

本地预览公开展示版：

```bash
VITE_PUBLIC_DEMO=true VITE_BASE_PATH=/BadmintonCoachSkill/ npm --prefix web run build
npm --prefix web run preview -- --host 127.0.0.1
```

正常开发完整网页时，不设置上述变量；该模式仍使用 API 与受保护 runtime。
