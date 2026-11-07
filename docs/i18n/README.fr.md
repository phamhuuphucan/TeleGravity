# 🚀 TeleGravity — Pont Telegram pour Google Antigravity (`agy acp`)

🌐 **Langues**: [🇻🇳 Tiếng Việt](../../README.md) · [🇬🇧 English](README.en.md) · **🇫🇷 Français** · [🇯🇵 日本語](README.ja.md) · [🇰🇷 한국어](README.ko.md) · [🇨🇳 中文](README.zh.md) · [🇷🇺 Русский](README.ru.md) · [🇩🇪 Deutsch](README.de.md) · [🇪🇸 Español](README.es.md)

> **Contrôlez Google Antigravity à distance 24h/24 et 7j/7 via Telegram** — Synchronisation bidirectionnelle transparente des sessions avec l'application de bureau Antigravity (macOS / Windows / Linux) ou exécution autonome sur un VPS Cloud, **sans clé API requise**.

---

## ✨ Points Forts

1. **🔑 Aucune Clé API Requise**: Communique directement avec `agy acp` (Agent Client Protocol via `stdio`) en utilisant le compte Google connecté à votre CLI Antigravity.
2. **🔄 Synchronisation Bidirectionnelle avec l'Application Desktop**:
   - Commencez à coder sur **Antigravity Desktop** → sortez et tapez `/sessions` sur Telegram → reprenez exactement la même session depuis votre téléphone.
   - Les sessions créées sur Telegram sont automatiquement associées au bon **Projet** dans l'application (synchronisation SQLite `conversation_summaries.db` et cache Protobuf).
3. **🛡️ Approbation Interactive des Permissions**:
   - Lorsque l'Agent doit exécuter une commande shell, le bot envoie des boutons de validation sur Telegram : `✅ Autoriser une fois` · `🔓 Toujours autoriser` · `❌ Refuser` · `⚡ Auto-approve`.
4. **📸 Multimodal & Fonctionnalités Complètes**:
   - Envoyez du texte ou des **captures d'écran avec légende**.
   - Changez de modèle (`/model`), de mode (`/mode`), de projet (`/projects`, `/cd`) et utilisez `/goal`, `/plan`, `/browser`.
5. **☁️ Multiplateforme & Service 24/7**:
   - Compatible **macOS** (`launchd`), **Linux / VPS / WSL2** (`systemd`) et **Windows Natif** (`Task Scheduler` via `service.ps1`).

---

## ⚡ Démarrage Rapide

#### 🍎 macOS / 🐧 Linux / 🪟 Windows (WSL2)
```bash
git clone https://github.com/phamhuuphucan/TeleGravity.git
cd TeleGravity
./setup.sh
./service.sh install
```

#### 🪟 Windows (PowerShell Natif)
```powershell
git clone https://github.com/phamhuuphucan/TeleGravity.git
cd TeleGravity
.\service.ps1 setup
.\service.ps1 install
```
