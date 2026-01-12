# GitHub Uploader Pro 技术规格书 (V4.0 Nebula)

## 1. 项目概述
GitHub Uploader Pro 是一款基于 PyQt6 的现代化桌面应用，旨在为用户提供极致、便捷的 GitHub 文件上传与仓库管理体验。

## 2. 技术栈
- **UI 框架**: PyQt6 (v6.6+)
- **逻辑核心**: Git CLI (通过 subprocess 进行原生对接)
- **API 通讯**: PyGithub (接入 GitHub REST API v3)
- **日志系统**: Loguru (结构化、彩色化日志)
- **配置管理**: JSON-based persistent storage

## 3. UI 视觉规范 (Ultra-Glass)
- **核心理念**: 拟物玻璃 (Skeuomorphic Glass) + 霓虹强调色 (Cyberpunk Accents)。
- **调色板**:
    - `Primary`: #58a6ff (GitHub Blue)
    - `Surface`: #0d1117 (Dark Mode)
    - `Accent`: #a371f7 (Cyber Purple)
- **动效**:
    - 线性入场 (Linear Slide-in)
    - 呼吸灯式进度反馈 (Breathing Progress)

## 4. 核心工作流
1. **OAuth2 鉴权**: Device Flow 授权流程。
2. **本地扫描**: Git Porcelain 状态检测。
3. **暂存与提交**: 自动化索引构建。
4. **远程推送**: 稳健的异常处理与递归重试。

## 5. 待办事项 (TODO)
- [x] 异步任务流重构 (V4 Nebula Pipeline)
- [x] 深度 UI 动效库集成 (Spring Animation)
- [x] 错误自愈代理引入 (AI Diagnosis)
- [ ] 跨平台 GPU 加速模糊优化
