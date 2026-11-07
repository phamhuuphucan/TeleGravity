# 01. Cài Đặt Trên Máy Tính Cá Nhân & Đồng Bộ Phiên Với App Antigravity

Tài liệu này hướng dẫn cách thiết lập **Antigravity Telegram Bridge** trên máy tính cá nhân (**macOS**, **Windows**, **Linux Desktop**) và giải thích cách tận dụng tính năng đồng bộ phiên làm việc 2 chiều giữa Telegram và ứng dụng **Antigravity Desktop**.

---

## 1. Điều Kiện Tiên Quyết

1. **Python 3.10 trở lên**:
   - Kiểm tra bằng lệnh `python3 --version` (macOS/Linux) hoặc `python --version` (Windows).
2. **Antigravity CLI (`agy`)**:
   - Khi bạn cài ứng dụng Antigravity trên máy tính, công cụ dòng lệnh `agy` thường đã được cài sẵn tại `~/.local/bin/agy` (hoặc `%USERPROFILE%\.local\bin\agy.exe` trên Windows).
   - Hãy đảm bảo bạn đã đăng nhập tài khoản Google trong Antigravity (có thể kiểm tra bằng cách gõ `agy` trong Terminal/PowerShell).
3. **Telegram Bot Token & User ID**:
   - Nhắn tin cho **`@BotFather`** trên Telegram → gõ `/newbot` → đặt tên và nhận chuỗi **`TELEGRAM_BOT_TOKEN`**.
   - Nhắn tin cho **`@userinfobot`** trên Telegram → bấm Start → lấy số **`Id`** của bạn (ví dụ: `123456789`) để điền vào `ALLOWED_USER_IDS`.

---

## 2. Hướng Dẫn Cài Đặt Theo Hệ Điều Hành

### 🍎 A. Trên macOS & 🐧 Linux Desktop

1. **Mở Terminal, tải dự án và chạy script cài đặt tự động:**
   ```bash
   git clone https://github.com/phamhuuphucan/TeleGravity.git
   cd TeleGravity
   ./setup.sh
   ```
   *(Script `setup.sh` sẽ tự động tạo môi trường ảo `.venv`, cài đặt `requirements.txt` và hỏi bạn `TELEGRAM_BOT_TOKEN`, `ALLOWED_USER_IDS`, cùng thư mục dự án mặc định).*

2. **Chạy thử nghiệm trực tiếp:**
   ```bash
   ./.venv/bin/python bot.py
   ```
   Mở Telegram, nhắn `/start` và `/status` cho Bot để kiểm tra kết nối. Nhấn `Ctrl + C` để dừng chạy thử.

3. **Kích hoạt dịch vụ chạy nền 24/7 (`launchd` trên macOS / `systemd` trên Linux):**
   ```bash
   ./service.sh install
   ```

4. **Các lệnh quản lý dịch vụ nền:**
   ```bash
   ./service.sh status     # Xem trạng thái bot đang chạy hay dừng
   ./service.sh logs       # Xem log hoạt động theo thời gian thực
   ./service.sh restart    # Khởi động lại bot (sau khi chỉnh sửa file .env)
   ./service.sh login      # Mở trình duyệt đổi tài khoản Google & tự khởi động lại bot
   ./service.sh uninstall  # Gỡ dịch vụ chạy nền
   ```

---

### 🪟 B. Trên Windows (Có 2 cách)

#### Cách 1: Dùng WSL2 (Ubuntu trên Windows) — *Khuyên dùng nếu bạn code trong WSL*
Nếu mã nguồn dự án của bạn đặt trong môi trường WSL2:
- Mở cửa sổ Ubuntu (WSL2) và thực hiện **y hệt như hướng dẫn cho Linux ở Mục 2.A** (`./setup.sh` và `./service.sh install`).

#### Cách 2: Chạy Native trực tiếp trên Windows (PowerShell)
Nếu bạn dùng Antigravity trực tiếp trên Windows và muốn đồng bộ với ứng dụng Antigravity Windows:

1. Mở **PowerShell**, di chuyển vào thư mục dự án:
   ```powershell
   git clone https://github.com/phamhuuphucan/TeleGravity.git
   cd TeleGravity
   ```
   *(Nếu Windows báo chặn chạy script, hãy chạy lệnh cấp quyền cho user hiện tại: `Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned`)*.

2. **Chạy lệnh thiết lập tự động:**
   ```powershell
   .\service.ps1 setup
   ```
   Lệnh này sẽ tạo `.venv`, cài thư viện và mở file `.env` bằng Notepad để bạn điền `TELEGRAM_BOT_TOKEN`, `ALLOWED_USER_IDS` và đường dẫn thư mục dự án (ví dụ: `DEFAULT_WORKSPACE=C:\Users\TenBan\Projects`).

3. **Chạy thử nghiệm:**
   ```powershell
   .\.venv\Scripts\python.exe bot.py
   ```

4. **Cài đặt tự khởi chạy ngầm cùng Windows (Windows Task Scheduler):**
   ```powershell
   .\service.ps1 install
   ```

5. **Quản lý trên Windows:**
   ```powershell
   .\service.ps1 status     # Kiểm tra trạng thái Task Scheduler & PID
   .\service.ps1 logs       # Xem log thời gian thực
   .\service.ps1 restart    # Khởi động lại bot
   .\service.ps1 login      # Đăng nhập lại tài khoản Google cho agy
   .\service.ps1 uninstall  # Gỡ khỏi Task Scheduler
   ```

---

## 3. Quy Trình Đồng Bộ Phiên Làm Việc Giữa Máy Tính & Telegram

Một trong những ưu điểm lớn nhất của bộ Bridge này là khả năng **chia sẻ chung cơ sở dữ liệu phiên (`~/.gemini/antigravity`)** với ứng dụng Antigravity trên máy tính:

### Kịch bản 1: Làm việc trên máy tính → Đi ra ngoài làm tiếp trên Telegram
1. Bạn đang ngồi trước máy tính, mở ứng dụng Antigravity để viết code hoặc重构 (refactor) dự án.
2. Khi có việc cần ra ngoài, bạn có thể đóng ứng dụng Antigravity lại.
3. Mở Telegram trên điện thoại, gõ lệnh:
   ```text
   /sessions
   ```
4. Bot sẽ hiển thị danh sách **10 phiên hội thoại gần nhất** (bao gồm cả các phiên bạn vừa tạo trên App máy tính).
5. Bấm vào nút tương ứng với phiên làm việc đó → Gửi tin nhắn tiếp theo, Agent sẽ nhớ toàn bộ ngữ cảnh trước đó và làm việc tiếp!

### Kịch bản 2: Giao việc trên Telegram → Về mở máy tính kiểm tra chi tiết
1. Khi đang ở ngoài, bạn dùng Telegram chọn dự án (`/cd TenDuAn`) và giao cho Agent thực hiện một tính năng mới.
2. Sau mỗi lượt hội thoại (`run_turn`), `bot.py` tự động gọi hàm đồng bộ `sync_antigravity_projects()`:
   - Nếu thư mục dự án chưa có trong danh sách Project của App, bot tự tạo cấu hình project mới trong `~/.gemini/config/projects/`.
   - Chuyển `project_id` của phiên từ `default-cli-project` sang đúng ID dự án trên App.
   - Cập nhật trực tiếp bảng `conversation_summaries`, file DB riêng của phiên và hai file cache Protobuf (`agyhub_summaries_proto.pb`, `jetbox_summaries_proto.pb`).
3. Khi về đến bàn làm việc, bạn mở ứng dụng Antigravity lên sẽ thấy ngay cuộc trò chuyện vừa làm trên Telegram nằm gọn trong đúng Project của mình!

> [!WARNING]
> **Lưu ý quan trọng khi đồng bộ:** Không nên mở và gửi tin nhắn vào **cùng một phiên hội thoại tại cùng một thời điểm** trên cả App máy tính lẫn Telegram để tránh xung đột ghi file SQLite (`database is locked`). Khi chuyển sang dùng thiết bị nào, hãy để phiên ở thiết bị kia nghỉ.

---

## 4. Câu Hỏi Thường Gặp Khi Chạy Trên Máy Cá Nhân (FAQ)

### ❓ Có cần mở cửa sổ ứng dụng Antigravity liên tục không?
- **KHÔNG CẦN.** Bạn có thể thoát hoàn toàn (`Cmd + Q` trên Mac hoặc `Alt + F4` trên Windows) ứng dụng Antigravity.
- Bot Telegram tự khởi chạy tiến trình ngầm `agy acp` của riêng nó khi có tin nhắn.
- **Điều kiện duy nhất:** Máy tính của bạn đang bật, có kết nối Internet và **không rơi vào trạng thái Sleep (Ngủ)**.
  - *Mẹo trên macOS:* Vào *System Settings → Battery / Energy* → Bật *"Prevent automatic sleeping when the display is off"* để có thể tắt màn hình mà bot vẫn chạy 24/7.
  - *Mẹo trên Windows:* Vào *Settings → System → Power & battery → Screen and sleep* → Chọn *Never* ở mục *Put my device to sleep*.
