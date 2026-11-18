#!/usr/bin/env bash
# Script cài đặt nhanh Antigravity Telegram Bridge (macOS / Linux / WSL2)
set -e

DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"

echo "========================================================"
echo "🚀 Cài đặt Antigravity Telegram Bridge"
echo "========================================================"

# 1. Kiểm tra Python 3.10+
if ! command -v python3 >/dev/null 2>&1; then
  echo "❌ Chưa cài đặt python3. Vui lòng cài Python 3.10 trở lên."
  exit 1
fi

# 2. Kiểm tra Antigravity CLI (agy)
AGY_BIN="$(command -v agy 2>/dev/null || echo "$HOME/.local/bin/agy")"
if [[ ! -x "$AGY_BIN" ]]; then
  echo "⚠️  Chưa tìm thấy Antigravity CLI (agy) tại $AGY_BIN."
  echo "👉 Nếu bạn đang ở trên VPS/Linux hoặc máy mới, hãy cài đặt agy trước khi chạy bot."
else
  echo "✅ Đã tìm thấy agy tại: $AGY_BIN"
fi

# 3. Tạo môi trường ảo (.venv) và cài đặt thư viện
if [[ ! -d "$DIR/.venv" ]]; then
  echo "📦 Đang tạo môi trường ảo Python (.venv)..."
  python3 -m venv "$DIR/.venv"
fi

echo "📥 Đang cài đặt các thư viện trong requirements.txt..."
"$DIR/.venv/bin/pip" install --upgrade pip -q
"$DIR/.venv/bin/pip" install -r "$DIR/requirements.txt" -q
echo "✅ Đã cài xong thư viện Python."

# 4. Tạo file .env nếu chưa có
if [[ ! -f "$DIR/.env" ]]; then
  cp "$DIR/.env.example" "$DIR/.env"

  # Tự động dò múi giờ hệ thống làm gợi ý mặc định
  DETECTED_TZ=""
  if [[ -f /etc/timezone ]]; then
    DETECTED_TZ="$(cat /etc/timezone 2>/dev/null | tr -d '[:space:]')"
  elif [[ -L /etc/localtime ]]; then
    LT_TARGET="$(readlink /etc/localtime 2>/dev/null || true)"
    if [[ "$LT_TARGET" == *"/zoneinfo/"* ]]; then
      DETECTED_TZ="${LT_TARGET#*zoneinfo/}"
    fi
  fi
  DETECTED_TZ="${DETECTED_TZ:-Asia/Ho_Chi_Minh}"

  echo ""
  echo "📝 Hãy cấu hình nhanh thông tin Bot Telegram (Enter để giữ giá trị mặc định):"
  read -r -p "1. Nhập TELEGRAM_BOT_TOKEN (từ @BotFather): " tg_token
  read -r -p "2. Nhập ALLOWED_USER_IDS (từ @userinfobot): " tg_uid

  default_projects="$HOME/Projects"
  read -r -p "3. Thư mục gốc chứa các dự án code (PROJECTS_ROOT) [mặc định: $default_projects]: " ws_dir
  ws_dir="${ws_dir:-$default_projects}"
  ws_dir="${ws_dir/#\~/$HOME}"

  default_pa="${ws_dir%/}/Personal_Assistant"
  read -r -p "4. Thư mục Trợ lý cá nhân (ASSISTANT_HOME) [mặc định: $default_pa]: " pa_dir
  pa_dir="${pa_dir:-$default_pa}"
  pa_dir="${pa_dir/#\~/$HOME}"

  read -r -p "5. Múi giờ lịch hẹn (ASSISTANT_TIMEZONE) [mặc định: $DETECTED_TZ]: " tz_val
  tz_val="${tz_val:-$DETECTED_TZ}"

  mkdir -p "$ws_dir" "$pa_dir"

  # Cập nhật vào .env
  "$DIR/.venv/bin/python" - "$DIR/.env" "$tg_token" "$tg_uid" "$AGY_BIN" "$ws_dir" "$pa_dir" "$tz_val" <<'PYEOF'
import sys
from pathlib import Path

env_path = Path(sys.argv[1])
token, uid, agy_bin, ws, pa, tz = sys.argv[2:8]
lines = env_path.read_text(encoding="utf-8").splitlines()
out = []
for line in lines:
    if line.startswith("TELEGRAM_BOT_TOKEN=") and token:
        out.append(f"TELEGRAM_BOT_TOKEN={token}")
    elif line.startswith("ALLOWED_USER_IDS=") and uid:
        out.append(f"ALLOWED_USER_IDS={uid}")
    elif line.startswith("AGY_PATH=") and agy_bin:
        out.append(f"AGY_PATH={agy_bin}")
    elif line.startswith("PROJECTS_ROOT="):
        out.append(f"PROJECTS_ROOT={ws}")
    elif line.startswith("ASSISTANT_HOME="):
        out.append(f"ASSISTANT_HOME={pa}")
    elif line.startswith("DEFAULT_WORKSPACE="):
        out.append(f"DEFAULT_WORKSPACE={pa}")
    elif line.startswith("ASSISTANT_TIMEZONE="):
        out.append(f"ASSISTANT_TIMEZONE={tz}")
    else:
        out.append(line)
env_path.write_text("\n".join(out) + "\n", encoding="utf-8")
PYEOF
  echo "✅ Đã lưu cấu hình vào file .env"
else
  echo "ℹ️  File .env đã tồn tại, giữ nguyên cấu hình hiện tại."
fi

chmod +x "$DIR/service.sh"

echo ""
echo "========================================================"
echo "🎉 Hoàn tất cài đặt!"
echo "👉 Bước 1 (Nếu chưa đăng nhập Google cho agy): ./service.sh login"
echo "👉 Bước 2 (Chạy thử trực tiếp)               : ./.venv/bin/python bot.py"
echo "👉 Bước 3 (Chạy ngầm 24/7 tự động)           : ./service.sh install"
echo "========================================================"
