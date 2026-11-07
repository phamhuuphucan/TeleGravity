# 🚀 TeleGravity — Antigravity Telegram Bridge (`agy acp`)

🌐 **Languages**: [🇻🇳 Tiếng Việt](../../README.md) · **🇬🇧 English** · [🇫🇷 Français](README.fr.md) · [🇯🇵 日本語](README.ja.md) · [🇰🇷 한국어](README.ko.md) · [🇨🇳 中文](README.zh.md) · [🇷🇺 Русский](README.ru.md) · [🇩🇪 Deutsch](README.de.md) · [🇪🇸 Español](README.es.md)

> **Control Google Antigravity remotely 24/7 via Telegram** — Seamlessly sync sessions two-way with the Antigravity Desktop App (macOS / Windows / Linux) or run standalone on a Cloud VPS, **with no API Key required**.

---

## ✨ Key Highlights

1. **🔑 Zero API Key Cost**: Communicates directly with `agy acp` (Agent Client Protocol over `stdio`), using the Google account already signed in to your Antigravity CLI.
2. **🔄 Two-Way Session & Project Sync with Desktop App**:
   - Start coding on the **Antigravity Desktop App** → step away and type `/sessions` on Telegram → resume the exact same conversation from your phone.
   - Start a new session on Telegram → automatically mapped to the matching **Project** in the Desktop App (syncs both SQLite `conversation_summaries.db` and Protobuf caches `agyhub_summaries_proto.pb` / `jetbox_summaries_proto.pb`).
3. **🛡️ Interactive Permission Approval**:
   - Whenever the Agent needs to execute a shell command (`run_command`) or modify sensitive files, the bot sends inline approval buttons on Telegram: `✅ Allow once` · `🔓 Always allow` · `❌ Reject` · `⚡ Auto-approve`.
4. **📸 Multimodal & Full Antigravity Capabilities**:
   - Send text prompts or **screenshots with captions** to debug UI/UX issues.
   - Switch models (`/model`), approval modes (`/mode`), projects (`/projects`, `/cd`), and forward native slash commands (`/goal`, `/plan`, `/browser`).
5. **☁️ Cross-Platform & 24/7 Ready**:
   - Supports **macOS** (`launchd`), **Linux / VPS / WSL2** (`systemd`), and **Native Windows** (`Task Scheduler` via `service.ps1`).

---

## ⚡ Quick Start

### 1. Prerequisites
1. Message **`@BotFather`** on Telegram → `/newbot` → save your **`TELEGRAM_BOT_TOKEN`**.
2. Message **`@userinfobot`** on Telegram → save your numeric **`Id`** (for whitelist security).
3. Ensure **Antigravity CLI (`agy`)** is installed and logged in to your Google account.

### 2. Installation

#### 🍎 macOS / 🐧 Linux / 🪟 Windows (WSL2)
```bash
git clone https://github.com/phamhuuphucan/TeleGravity.git
cd TeleGravity
./setup.sh
./service.sh install
```

#### 🪟 Windows (Native PowerShell)
```powershell
git clone https://github.com/phamhuuphucan/TeleGravity.git
cd TeleGravity
.\service.ps1 setup
.\service.ps1 install
```

---

## 💬 Common Telegram Commands

| Command | Description |
| :--- | :--- |
| *(Text / Photo + caption)* | Assign coding tasks directly to the Antigravity Agent |
| `/status` | View current Workspace, App Project, Session, Model, and Mode |
| `/sessions` | List the 10 most recent sessions (from both App & Telegram) → tap to resume |
| `/projects` | List all projects inside `PROJECTS_ROOT` |
| `/cd <Project \| Path>` | Switch workspace to another project |
| `/new` | Start a new conversation in the current workspace |
| `/stop` | Cancel the currently running Agent task |
| `/model [id]` | View available models or switch models (Gemini, Claude, etc.) |
| `/mode [default\|accept-edits\|plan]` | Change permission approval mode |
| `/auto [on\|off]` | Enable or disable automatic approval for all tool calls |
| `/goal ...`, `/plan ...`, `/browser ...` | Forward native Antigravity slash commands directly to the Agent |
