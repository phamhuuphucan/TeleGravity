# 🚀 TeleGravity — Google Antigravity Telegram 桥接工具 (`agy acp`)

🌐 **语言**: [🇻🇳 Tiếng Việt](../../README.md) · [🇬🇧 English](README.en.md) · [🇫🇷 Français](README.fr.md) · [🇯🇵 日本語](README.ja.md) · [🇰🇷 한국어](README.ko.md) · **🇨🇳 中文** · [🇷🇺 Русский](README.ru.md) · [🇩🇪 Deutsch](README.de.md) · [🇪🇸 Español](README.es.md)

> **通过 Telegram 全天候 24/7 远程控制 Google Antigravity** — 与桌面端 Antigravity 应用（macOS / Windows / Linux）无缝双向同步会话，或独立部署在云端 VPS 上，**无需任何 API Key**。

---

## ✨ 核心亮点

1. **🔑 无需 API Key 费用**：直接与 `agy acp`（基于 `stdio` 的 Agent Client Protocol）通信，复用 Antigravity CLI 中已登录的 Google 账号。
2. **🔄 与桌面端应用双向同步会话与项目**：
   - 在电脑 **Antigravity 桌面端**写代码到一半 → 出门在外打开 Telegram 发送 `/sessions` → 在手机上无缝继续同一个会话。
   - 在 Telegram 上新建的会话会自动映射到桌面端对应的 **Project**（自动同步 SQLite `conversation_summaries.db` 与 Protobuf 缓存）。
3. **🛡️ 远程交互式权限审批**：
   - 当 Agent 需要执行终端命令（`run_command`）或修改敏感文件时，Bot 会在 Telegram 上发送审批按钮：`✅ 仅允许一次` · `🔓 始终允许` · `❌ 拒绝` · `⚡ 自动批准`。
4. **📸 多模态与完整功能支持**：
   - 支持发送文本提示词或**截图配文字说明**来排查 UI/UX 问题。
   - 支持切换模型（`/model`）、审批模式（`/mode`）、项目目录（`/projects`, `/cd`），以及转发原生斜杠命令（`/goal`, `/plan`, `/browser`）。
5. **☁️ 跨平台与 24/7 后台守护**：
   - 原生支持 **macOS** (`launchd`)、**Linux / VPS / WSL2** (`systemd`) 与 **Windows** (`service.ps1` / 任务计划程序)。

---

## ⚡ 快速开始

#### 🍎 macOS / 🐧 Linux / 🪟 Windows (WSL2)
```bash
git clone https://github.com/phamhuuphucan/TeleGravity.git
cd TeleGravity
./setup.sh
./service.sh install
```

#### 🪟 Windows (原生 PowerShell)
```powershell
git clone https://github.com/phamhuuphucan/TeleGravity.git
cd TeleGravity
.\service.ps1 setup
.\service.ps1 install
```
