# 🚀 TeleGravity — Puente de Telegram para Google Antigravity (`agy acp`)

🌐 **Idiomas**: [🇻🇳 Tiếng Việt](../../README.md) · [🇬🇧 English](README.en.md) · [🇫🇷 Français](README.fr.md) · [🇯🇵 日本語](README.ja.md) · [🇰🇷 한국어](README.ko.md) · [🇨🇳 中文](README.zh.md) · [🇷🇺 Русский](README.ru.md) · [🇩🇪 Deutsch](README.de.md) · **🇪🇸 Español**

> **Controla Google Antigravity de forma remota 24/7 a través de Telegram** — Sincronización bidireccional de sesiones con la aplicación de escritorio Antigravity (macOS / Windows / Linux) o ejecución independiente en un VPS en la nube, **sin necesidad de clave API**.

---

## ✨ Características Principales

1. **🔑 Sin Costo de Clave API**: Se comunica directamente con `agy acp` (Agent Client Protocol mediante `stdio`), utilizando la cuenta de Google ya iniciada en tu CLI de Antigravity.
2. **🔄 Sincronización Bidireccional de Sesiones y Proyectos con la App de Escritorio**:
   - Empieza a programar en **Antigravity Desktop App** → sal de casa y escribe `/sessions` en Telegram → continúa exactamente la misma conversación desde tu móvil.
   - Las conversaciones creadas en Telegram se asignan automáticamente al **Proyecto** correspondiente en la aplicación de escritorio (sincronizando SQLite `conversation_summaries.db` y la caché Protobuf).
3. **🛡️ Aprobación Interactiva de Permisos**:
   - Cuando el Agente necesita ejecutar un comando de terminal, el bot envía botones interactivos en Telegram: `✅ Permitir una vez` · `🔓 Permitir siempre` · `❌ Rechazar` · `⚡ Auto-aprobar`.
4. **📸 Multimodal y Funciones Completas de Antigravity**:
   - Envía mensajes de texto o **capturas de pantalla con descripción**.
   - Cambia de modelo (`/model`), modo (`/mode`), proyecto (`/projects`, `/cd`) y reenvía comandos como `/goal`, `/plan`, `/browser`.
5. **☁️ Multiplataforma y Listo para Funcionar 24/7**:
   - Compatible con **macOS** (`launchd`), **Linux / VPS / WSL2** (`systemd`) y **Windows Nativo** (`service.ps1` / Programador de tareas).

---

## ⚡ Inicio Rápido

#### 🍎 macOS / 🐧 Linux / 🪟 Windows (WSL2)
```bash
git clone https://github.com/phamhuuphucan/TeleGravity.git
cd TeleGravity
./setup.sh
./service.sh install
```

#### 🪟 Windows (PowerShell Nativo)
```powershell
git clone https://github.com/phamhuuphucan/TeleGravity.git
cd TeleGravity
.\service.ps1 setup
.\service.ps1 install
```
