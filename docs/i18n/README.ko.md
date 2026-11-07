# 🚀 TeleGravity — Google Antigravity 텔레그램 브리지 (`agy acp`)

🌐 **언어**: [🇻🇳 Tiếng Việt](../../README.md) · [🇬🇧 English](README.en.md) · [🇫🇷 Français](README.fr.md) · [🇯🇵 日本語](README.ja.md) · **🇰🇷 한국어** · [🇨🇳 中文](README.zh.md) · [🇷🇺 Русский](README.ru.md) · [🇩🇪 Deutsch](README.de.md) · [🇪🇸 Español](README.es.md)

> **텔레그램을 통해 연중무휴 24시간 Google Antigravity를 원격 제어하세요** — 데스크톱 Antigravity 앱(macOS / Windows / Linux)과 실시간 양방향 세션 동기화를 지원하며, 클라우드 VPS에서도 **별도의 API 키 없이** 24시간 구동할 수 있습니다.

---

## ✨ 핵심 기능

1. **🔑 API 키 비용 제로**: Antigravity CLI에 로그인된 Google 계정을 사용하여 `agy acp`(표준 입출력 기반 Agent Client Protocol)와 직접 통신합니다.
2. **🔄 데스크톱 앱과 양방향 세션 및 프로젝트 동기화**:
   - PC **Antigravity 데스크톱 앱**에서 작업하던 세션을 외출 중 텔레그램 `/sessions` 명령으로 이어받아 그대로 진행할 수 있습니다.
   - 텔레그램에서 생성한 새 대화도 데스크톱 앱의 올바른 **Project**로 자동 매핑 및 동기화됩니다(SQLite `conversation_summaries.db` 및 Protobuf 캐시 동기화).
3. **🛡️ 대화형 권한 승인 (Inline Buttons)**:
   - 에이전트가 셸 명령어를 실행할 때 텔레그램 인라인 버튼(`✅ 1회 허용` · `🔓 항상 허용` · `❌ 거부` · `⚡ 자동 승인`)으로 안전하게 제어합니다.
4. **📸 멀티모달 및 모든 Antigravity 명령 지원**:
   - 텍스트 메시지뿐만 아니라 **스크린샷 이미지와 캡션** 전송 지원.
   - 모델 변경(`/model`), 모드 변경(`/mode`), 프로젝트 전환(`/projects`, `/cd`), `/goal`, `/plan`, `/browser` 슬래시 명령어를 그대로 전달합니다.
5. **☁️ 크로스 플랫폼 & 24/7 백그라운드 서비스**:
   - **macOS** (`launchd`), **Linux / VPS / WSL2** (`systemd`), **Windows Native** (`service.ps1` / 작업 스케줄러) 완벽 지원.

---

## ⚡ 빠른 시작 (Quick Start)

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
