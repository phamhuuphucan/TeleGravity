#!/usr/bin/env bash
# Quản lý bot chạy nền 24/7 bằng launchd (macOS) hoặc systemd (Linux / WSL2 / VPS).
# Dùng: ./service.sh install | uninstall | restart | status | logs | login
set -e

LEGACY_LABEL="com.phucan.antigravity-telegram"
DEFAULT_LABEL="com.antigravity.telegram-bridge"
if [[ -f "$HOME/Library/LaunchAgents/$LEGACY_LABEL.plist" ]]; then
  LABEL="${SERVICE_LABEL:-$LEGACY_LABEL}"
else
  LABEL="${SERVICE_LABEL:-$DEFAULT_LABEL}"
fi

SYSTEMD_UNIT="antigravity-telegram.service"
DIR="$(cd "$(dirname "$0")" && pwd)"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
PY="$DIR/.venv/bin/python"
AGY="$(command -v agy 2>/dev/null || echo "$HOME/.local/bin/agy")"
UID_NUM="$(id -u)"
OS_TYPE="$(uname -s)"

if [[ "$OS_TYPE" == "Linux" ]]; then
  UNIT_PATH="/etc/systemd/system/$SYSTEMD_UNIT"
  case "$1" in
    install)
      [[ -f "$DIR/.env" ]] || { echo "❌ Chưa có file .env (hãy chạy ./setup.sh hoặc cp .env.example .env)"; exit 1; }
      mkdir -p "$DIR/logs"
      sudo tee "$UNIT_PATH" > /dev/null <<EOF
[Unit]
Description=Antigravity Telegram Bridge Bot
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$DIR
Environment="PATH=$HOME/.local/bin:/usr/local/bin:/usr/bin:/bin"
Environment="PYTHONUNBUFFERED=1"
ExecStart=$PY $DIR/bot.py
Restart=always
RestartSec=5
StandardOutput=append:$DIR/logs/bot.log
StandardError=append:$DIR/logs/bot.log

[Install]
WantedBy=multi-user.target
EOF
      sudo systemctl daemon-reload
      sudo systemctl enable "$SYSTEMD_UNIT"
      sudo systemctl restart "$SYSTEMD_UNIT"
      echo "✅ Đã cài và khởi động $SYSTEMD_UNIT (systemd). Xem log: ./service.sh logs"
      ;;
    uninstall)
      sudo systemctl stop "$SYSTEMD_UNIT" 2>/dev/null || true
      sudo systemctl disable "$SYSTEMD_UNIT" 2>/dev/null || true
      sudo rm -f "$UNIT_PATH"
      sudo systemctl daemon-reload
      echo "✅ Đã gỡ $SYSTEMD_UNIT"
      ;;
    restart)
      sudo systemctl restart "$SYSTEMD_UNIT"
      echo "✅ Đã khởi động lại $SYSTEMD_UNIT"
      ;;
    status)
      sudo systemctl status "$SYSTEMD_UNIT" --no-pager || true
      ;;
    logs)
      tail -n 100 -f "$DIR/logs/bot.log"
      ;;
    login)
      echo "🔑 Đang khởi chạy đăng nhập tài khoản Google cho Antigravity CLI..."
      "$AGY" acp --app-data-dir antigravity --login
      if systemctl is-active --quiet "$SYSTEMD_UNIT"; then
        sudo systemctl restart "$SYSTEMD_UNIT"
        echo "✅ Đã cập nhật tài khoản và khởi động lại bot Telegram!"
      else
        echo "✅ Đã cập nhật tài khoản!"
      fi
      ;;
    *)
      echo "Dùng: $0 install | uninstall | restart | status | logs | login"
      ;;
  esac
  exit 0
fi

case "$1" in
  install)
    [[ -f "$DIR/.env" ]] || { echo "❌ Chưa có file .env (hãy chạy ./setup.sh hoặc cp .env.example .env)"; exit 1; }
    mkdir -p "$DIR/logs" "$HOME/Library/LaunchAgents"
    cat > "$PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>$LABEL</string>
  <key>ProgramArguments</key>
  <array><string>$PY</string><string>$DIR/bot.py</string></array>
  <key>WorkingDirectory</key><string>$DIR</string>
  <key>EnvironmentVariables</key>
  <dict>
    <key>PATH</key><string>$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>
    <key>PYTHONUNBUFFERED</key><string>1</string>
  </dict>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
  <key>ThrottleInterval</key><integer>10</integer>
  <key>StandardOutPath</key><string>$DIR/logs/bot.log</string>
  <key>StandardErrorPath</key><string>$DIR/logs/bot.log</string>
</dict>
</plist>
EOF
    launchctl bootout "gui/$UID_NUM/$LABEL" 2>/dev/null || true
    launchctl bootstrap "gui/$UID_NUM" "$PLIST"
    echo "✅ Đã cài và khởi động $LABEL. Xem log: ./service.sh logs"
    ;;
  uninstall)
    launchctl bootout "gui/$UID_NUM/$LABEL" 2>/dev/null || true
    rm -f "$PLIST"
    echo "✅ Đã gỡ $LABEL"
    ;;
  restart)
    launchctl kickstart -k "gui/$UID_NUM/$LABEL"
    echo "✅ Đã khởi động lại"
    ;;
  status)
    launchctl print "gui/$UID_NUM/$LABEL" | grep -E "state|pid|last exit" || echo "Chưa cài"
    ;;
  logs)
    tail -n 100 -f "$DIR/logs/bot.log"
    ;;
  login)
    echo "🔑 Đang mở trình duyệt để đăng nhập/đổi tài khoản Google cho Antigravity CLI..."
    "$AGY" acp --login
    if launchctl print "gui/$UID_NUM/$LABEL" >/dev/null 2>&1; then
      launchctl kickstart -k "gui/$UID_NUM/$LABEL"
      echo "✅ Đã cập nhật tài khoản và khởi động lại bot Telegram!"
    else
      echo "✅ Đã cập nhật tài khoản!"
    fi
    ;;
  *)
    echo "Dùng: $0 install | uninstall | restart | status | logs | login"
    ;;
esac
