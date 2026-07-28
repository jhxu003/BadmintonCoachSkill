# GitHub Pages 展示版

GitHub Pages 部署的是一个**纯静态、公开安全的产品展示**，地址为：

<https://jhxu003.github.io/BadmintonCoachSkill/>

它展示三套教练 Skill，以及刘辉七项技术的可切换课程结构、动作阶段导航和证据边界。页面不包含或请求以下内容：

- `.runtime` 中的审核媒体、课程清单、缓存、数据库或访问令牌；
- 上传的学员视频、关键帧、动作包、模型权重或日志；
- 完整 API、GPU 推理、Celery、TTL 清理或访问控制能力。

## 七个公开媒体例外

项目所有者于 2026-07-28 明确批准把以下七个刘辉案例用于公开 Pages 展示。它们是 Git 唯一跟踪的教练抽取媒体：

| 技术 | 原始公开来源 | 公开连续窗口 | 发布目录 |
|---|---|---:|---|
| 高远球 | [BV1Ed4y1s7vj](https://www.bilibili.com/video/BV1Ed4y1s7vj/) | 120.00–126.50 秒 | `liu-hui-high-clear/` |
| 杀球 | [BV1p34y1V7qa](https://www.bilibili.com/video/BV1p34y1V7qa/) | 121.00–124.50 秒 | `liu-hui-smash/` |
| 吊球 | [BV1e4421S76x](https://www.bilibili.com/video/BV1e4421S76x/) | 132.00–135.50 秒 | `liu-hui-slice-drop/` |
| 后场步法 | [BV1NwrrBtEdY](https://www.bilibili.com/video/BV1NwrrBtEdY/) | 173.75–177.25 秒 | `liu-hui-backcourt-footwork/` |
| 平抽挡 | [BV17t2wYxEF3](https://www.bilibili.com/video/BV17t2wYxEF3/) | 119.00–123.75 秒 | `liu-hui-drive/` |
| 反手 | [BV1TT411r7Ft](https://www.bilibili.com/video/BV1TT411r7Ft/) | 287.25–290.00 秒 | `liu-hui-backhand/` |
| 发接发 · 正手发高远球子课 | [BV1Xoe9zkEVT](https://www.bilibili.com/video/BV1Xoe9zkEVT/) | 1314.25–1317.50 秒 | `liu-hui-serve-receive/` |

每个目录包含 1 段 H.264 连续动作片段、7 张来自同一动作的有序关键帧和来源说明。发接发案例明确限定为“正手发高远球”子课，不将发球素材冒充完整接发教学。

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
