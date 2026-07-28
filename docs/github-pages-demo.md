# GitHub Pages 展示版

GitHub Pages 部署的是一个**纯静态、公开安全的产品展示**，地址为：

<https://jhxu003.github.io/BadmintonCoachSkill/>

它展示三套教练 Skill、刘辉高远球课程结构、动作阶段导航和证据边界。页面不包含或请求以下内容：

- `.runtime` 中的审核媒体、课程清单、缓存、数据库或访问令牌；
- 上传的学员视频、关键帧、动作包、模型权重或日志；
- 完整 API、GPU 推理、Celery、TTL 清理或访问控制能力。

## 单一公开媒体例外

项目所有者于 2026-07-28 明确批准一个公开 Pages case。它是 Git 唯一跟踪的教练抽取媒体：

- 原始公开来源：[Bilibili BV1ym411g74x](https://www.bilibili.com/video/BV1ym411g74x/)；
- 已审核 lesson：`corpus-067-lh_bili_season_bv1ym411g74x-high_clear-candidate-011-atlas-v2`；
- 已审核来源窗口：147.75–154.25 秒；
- 发布文件：1 段 6.5 秒连续片段和 7 张有序关键帧，位于 `web/public/pages-demo/liu-hui-high-clear/`。

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
