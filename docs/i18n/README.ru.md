# 🚀 TeleGravity — Мост Telegram для Google Antigravity (`agy acp`)

🌐 **Языки**: [🇻🇳 Tiếng Việt](../../README.md) · [🇬🇧 English](README.en.md) · [🇫🇷 Français](README.fr.md) · [🇯🇵 日本語](README.ja.md) · [🇰🇷 한국어](README.ko.md) · [🇨🇳 中文](README.zh.md) · **🇷🇺 Русский** · [🇩🇪 Deutsch](README.de.md) · [🇪🇸 Español](README.es.md)

> **Удаленное управление Google Antigravity 24/7 через Telegram** — Двусторонняя синхронизация сессий с настольным приложением Antigravity (macOS / Windows / Linux) или автономная работа на облачном VPS **без необходимости использования API-ключа**.

---

## ✨ Ключевые возможности

1. **🔑 Без затрат на API-ключ**: Напрямую взаимодействует с `agy acp` (Agent Client Protocol через `stdio`), используя аккаунт Google, авторизованный в Antigravity CLI.
2. **🔄 Двусторонняя синхронизация сессий и проектов с Desktop App**:
   - Начните работу в **Antigravity Desktop App** → в дороге введите `/sessions` в Telegram → продолжите ту же самую сессию со смартфона.
   - Новые диалоги из Telegram автоматически привязываются к нужному **Проекту** в настольном приложении (синхронизация SQLite `conversation_summaries.db` и кэша Protobuf).
3. **🛡️ Интерактивное подтверждение разрешений**:
   - Когда агенту нужно выполнить shell-команду, бот присылает кнопки в Telegram: `✅ Разрешить один раз` · `🔓 Разрешать всегда` · `❌ Отклонить` · `⚡ Авто-одобрение`.
4. **📸 Мультимодальность и все функции Antigravity**:
   - Отправляйте текст или **скриншоты с подписями**.
   - Переключайте модели (`/model`), режимы (`/mode`), проекты (`/projects`, `/cd`) и используйте слэш-команды `/goal`, `/plan`, `/browser`.
5. **☁️ Кроссплатформенность и работа 24/7**:
   - Поддержка **macOS** (`launchd`), **Linux / VPS / WSL2** (`systemd`) и **Windows** (`service.ps1` / Планировщик задач).

---

## ⚡ Быстрый старт

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
