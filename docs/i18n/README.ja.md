# 🚀 TeleGravity — Google Antigravity Telegram ブリッジ (`agy acp`)

🌐 **言語**: [🇻🇳 Tiếng Việt](../../README.md) · [🇬🇧 English](README.en.md) · [🇫🇷 Français](README.fr.md) · **🇯🇵 日本語** · [🇰🇷 한국어](README.ko.md) · [🇨🇳 中文](README.zh.md) · [🇷🇺 Русский](README.ru.md) · [🇩🇪 Deutsch](README.de.md) · [🇪🇸 Español](README.es.md)

> **Telegram から 24時間365日 Google Antigravity をリモート操作** — デスクトップ版 Antigravity アプリ（macOS / Windows / Linux）との双方向セッション同期、およびクラウド VPS での24時間稼働に対応。**API キーは不要です。**

---

## ✨ 主な特徴

1. **🔑 API キー不要**: `agy acp`（`stdio` 経由の Agent Client Protocol）と直接通信し、Antigravity CLI にログイン済みの Google アカウントをそのまま利用します。
2. **🔄 デスクトップアプリとの双方向セッション＆プロジェクト同期**:
   - PC の **Antigravity デスクトップアプリ**で作業中のセッションを、外出先から Telegram の `/sessions` コマンドでそのまま引き継いで続行可能。
   - Telegram で開始した会話も、自動的に PC アプリ側の該当 **Project** に同期されます（SQLite `conversation_summaries.db` および Protobuf キャッシュを自動更新）。
3. **🛡️ リモート権限承認（インラインボタン）**:
   - エージェントがシェルコマンドを実行する際、Telegram 上のボタン（`✅ 1回許可` / `🔓 常に許可` / `❌ 拒否` / `⚡ 自動承認`）で安全に承認・拒否できます。
4. **📸 マルチモーダル＆全コマンド対応**:
   - テキストだけでなく**スクリーンショット画像＋キャプション**の送信に対応。
   - モデル切替（`/model`）、モード切替（`/mode`）、プロジェクト 이동（`/projects`, `/cd`）、`/goal` や `/plan` などのスラッシュコマンドもそのまま利用可能。
5. **☁️ クロスプラットフォーム＆24時間稼働**:
   - **macOS** (`launchd`)、**Linux / VPS / WSL2** (`systemd`)、**Windows** (`service.ps1` / タスクスケジューラ) に対応。

---

## ⚡ クイックスタート

#### 🍎 macOS / 🐧 Linux / 🪟 Windows (WSL2)
```bash
git clone https://github.com/phamhuuphucan/TeleGravity.git
cd TeleGravity
./setup.sh
./service.sh install
```

#### 🪟 Windows (PowerShell)
```powershell
git clone https://github.com/phamhuuphucan/TeleGravity.git
cd TeleGravity
.\service.ps1 setup
.\service.ps1 install
```
