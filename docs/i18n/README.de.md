# 🚀 TeleGravity — Telegram-Bridge für Google Antigravity (`agy acp`)

🌐 **Sprachen**: [🇻🇳 Tiếng Việt](../../README.md) · [🇬🇧 English](README.en.md) · [🇫🇷 Français](README.fr.md) · [🇯🇵 日本語](README.ja.md) · [🇰🇷 한국어](README.ko.md) · [🇨🇳 中文](README.zh.md) · [🇷🇺 Русский](README.ru.md) · **🇩🇪 Deutsch** · [🇪🇸 Español](README.es.md)

> **Steuern Sie Google Antigravity 24/7 aus der Ferne über Telegram** — Nahtlose bidirektionale Sitzungssynchronisierung mit der Antigravity Desktop-App (macOS / Windows / Linux) oder eigenständiger Betrieb auf einem Cloud-VPS, **ganz ohne API-Schlüssel**.

---

## ✨ Hauptmerkmale

1. **🔑 Keine API-Key-Kosten**: Kommuniziert direkt mit `agy acp` (Agent Client Protocol über `stdio`) und nutzt das bereits in der Antigravity-CLI angemeldete Google-Konto.
2. **🔄 Bidirektionale Sitzungs- & Projektsynchronisierung mit der Desktop-App**:
   - Beginnen Sie am PC in der **Antigravity Desktop-App** → tippen Sie unterwegs in Telegram `/sessions` → setzen Sie exakt dieselbe Sitzung auf dem Smartphone fort.
   - Neue Sitzungen aus Telegram werden automatisch dem richtigen **Projekt** in der Desktop-App zugeordnet (Synchronisierung von SQLite `conversation_summaries.db` und Protobuf-Caches).
3. **🛡️ Interaktive Berechtigungsfreigabe**:
   - Vor dem Ausführen von Shell-Befehlen fragt der Bot per Telegram-Buttons nach: `✅ Einmal erlauben` · `🔓 Immer erlauben` · `❌ Ablehnen` · `⚡ Auto-Approve`.
4. **📸 Multimodal & Voller Funktionsumfang**:
   - Senden Sie Textnachrichten oder **Screenshots mit Bildunterschrift**.
   - Wechseln Sie Modelle (`/model`), Modi (`/mode`), Projekte (`/projects`, `/cd`) und nutzen Sie Slash-Befehle wie `/goal`, `/plan`, `/browser`.
5. **☁️ Plattformübergreifend & 24/7-Hintergrunddienst**:
   - Unterstützt **macOS** (`launchd`), **Linux / VPS / WSL2** (`systemd`) und **Windows** (`service.ps1` / Aufgabenplanung).

---

## ⚡ Schnellstart

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
