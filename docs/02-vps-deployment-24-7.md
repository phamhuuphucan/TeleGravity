# 02. Triển Khai Antigravity & Bot Telegram Lên VPS Chạy 24/7

Nếu bạn không muốn phải bật máy tính cá nhân liên tục, việc đưa **Antigravity CLI (`agy`)** cùng **Telegram Bridge** lên một máy chủ ảo (**Linux VPS** chạy Ubuntu/Debian) là giải pháp lý tưởng nhất để có một "trợ lý lập trình" trực chiến 24/7 ở mọi nơi.

---

## 1. Cấu Hình VPS Khuyến Nghị

- **Hệ điều hành**: Ubuntu 22.04 LTS hoặc 24.04 LTS (64-bit) / Debian 12.
- **CPU & RAM**: Tối thiểu **2 vCPU / 2 GB RAM** (Khuyến nghị **4 GB RAM** nếu dự án của bạn chạy kèm Docker, Node.js build hoặc test nặng).
- **Ổ cứng**: 20 GB SSD trở lên.

---

## 2. Bước 1: Chuẩn Bị Môi Trường Trên VPS

SSH vào VPS của bạn và cài đặt các gói nền tảng cần thiết:

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y git curl wget unzip jq python3 python3-venv python3-pip build-essential
```

Tạo thư mục chứa các dự án code trên VPS (ví dụ `~/Projects`):

```bash
mkdir -p ~/Projects
```

---

## 3. Bước 2: Cài Đặt Antigravity CLI (`agy`) Trên VPS

Đảm bảo công cụ dòng lệnh `agy` đã được cài đặt tại `~/.local/bin/agy` và có quyền thực thi:

```bash
mkdir -p ~/.local/bin
# Nếu bạn đã có binary agy cho Linux x86_64/arm64 hoặc script cài đặt chính thức:
chmod +x ~/.local/bin/agy

# Thêm ~/.local/bin vào PATH nếu chưa có
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc

# Kiểm tra phiên bản
agy --version
```

---

## 4. Bước 3: Đăng Nhập Tài Khoản Google Trên VPS (Headless OAuth Login)

Vì VPS Linux chỉ có giao diện dòng lệnh (không có trình duyệt web để bấm đăng nhập Google), khi bạn chạy lệnh đăng nhập `agy acp --app-data-dir antigravity --login`, CLI sẽ khởi tạo một cổng callback cục bộ (dạng `http://localhost:<PORT>/...`) và in đường link đăng nhập Google ra màn hình.

Bạn hãy dùng kỹ thuật **SSH Local Port Forwarding** cực kỳ đơn giản sau đây để đăng nhập ngay trên trình duyệt máy tính cá nhân của mình:

### Quy trình thực hiện:

1. **Trong phiên SSH trên VPS**, chạy lệnh đăng nhập:
   ```bash
   ~/.local/bin/agy acp --app-data-dir antigravity --login
   ```
2. Quan sát đường link OAuth mà `agy` in ra trên Terminal. Trong đường link đó sẽ có tham số `redirect_uri=http://localhost:PORT/...` (hoặc `127.0.0.1:PORT`). Hãy nhìn kỹ số **`PORT`** (ví dụ: `45678` hoặc `8085`).
3. **Giữ nguyên cửa sổ Terminal đó trên VPS.** Mở một cửa sổ Terminal/PowerShell **mới trên máy tính cá nhân của bạn** và chạy lệnh nối cổng SSH:
   ```bash
   # Thay PORT bằng số cổng bạn vừa thấy, và user@ip-vps bằng thông tin VPS của bạn
   ssh -N -L PORT:127.0.0.1:PORT user@ip-vps
   ```
4. **Copy đường link đăng nhập Google** từ màn hình VPS dán vào trình duyệt trên máy tính cá nhân của bạn → Chọn tài khoản Google và bấm **Cho phép (Allow)**.
5. Trình duyệt sẽ chuyển hướng về `localhost:PORT`, thông qua đường hầm SSH truyền thẳng token xác thực về cho `agy` trên VPS!
6. Khi VPS báo đăng nhập thành công, bạn có thể đóng cửa sổ nối cổng SSH lại.

---

## 5. Bước 4: Cài Đặt Antigravity Telegram Bridge & Chạy Ngầm 24/7

1. **Clone repository về VPS và chạy script cài đặt:**
   ```bash
   cd ~
   git clone https://github.com/phamhuuphucan/TeleGravity.git
   cd TeleGravity
   ./setup.sh
   ```
   Điền `TELEGRAM_BOT_TOKEN`, `ALLOWED_USER_IDS` và thư mục dự án (ví dụ `/home/ubuntu/Projects`) khi được hỏi.

2. **Chạy thử để kiểm tra kết nối:**
   ```bash
   ./.venv/bin/python bot.py
   ```
   Mở Telegram trên điện thoại, gõ `/status`. Nếu bot phản hồi trạng thái bình thường, nhấn `Ctrl + C` để chuyển sang cài dịch vụ nền.

3. **Cài đặt dịch vụ `systemd` chạy 24/7 (tự khởi động lại khi crash hoặc khi reboot VPS):**
   ```bash
   ./service.sh install
   ```

4. **Kiểm tra trạng thái và theo dõi log trên VPS:**
   ```bash
   ./service.sh status
   ./service.sh logs
   ```

---

## 6. Mẹo Làm Việc Hiệu Quả Với Antigravity Trên VPS 24/7

1. **Cấu hình Git & SSH Key trên VPS**:
   - Hãy tạo SSH Key trên VPS (`ssh-keygen -t ed25519`) và gắn vào tài khoản GitHub/GitLab của bạn.
   - Nhờ đó, bạn chỉ cần nhắn qua Telegram: *"Hãy clone repo X về, tạo nhánh `feat/login`, viết xong tính năng thì chạy test và push PR lên GitHub cho anh"* — Agent trên VPS sẽ tự làm từ đầu đến cuối!
2. **Sử dụng lệnh `/goal` cho các tác vụ dài hơi**:
   - Vì VPS chạy 24/7 không sợ tắt máy giữa chừng, bạn có thể giao các việc lớn bằng lệnh `/goal <mục tiêu chi tiết>` để Agent tự kiểm thử và lặp lại cho đến khi hoàn thành.
3. **Đổi tài khoản Google trên VPS khi cần**:
   - Chạy `./service.sh login` kết hợp với bước SSH Port Forwarding ở Mục 4, dịch vụ `systemd` sẽ tự động restart bot sau khi nhận tài khoản mới.
