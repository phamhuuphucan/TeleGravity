# 04. Sổ Tay Lệnh Telegram, Chế Độ Duyệt Quyền & Bảo Mật

Tài liệu này tổng hợp toàn bộ các lệnh điều khiển trên Telegram, cách kiểm soát quyền hạn của Agent và cách quản lý tài khoản Google.

---

## 1. Bảng Tra Cứu Toàn Bộ Lệnh Telegram

### Nhóm lệnh Quản lý Phiên & Dự án
| Lệnh | Cú pháp & Ví dụ | Mô tả chi tiết |
| :--- | :--- | :--- |
| `/start`, `/help` | `/help` | Hiển thị bảng hướng dẫn nhanh và đường dẫn workspace hiện tại. |
| `/status` | `/status` | Hiển thị chi tiết: Workspace, tên Project trên App, tên & ID phiên hiện tại, Model, Mode, trạng thái Auto-approve và trạng thái tiến trình `agy`. |
| `/projects` | `/projects` | Liệt kê tất cả các thư mục dự án con nằm trong `PROJECTS_ROOT`. |
| `/cd` | `/cd TenDuAn`<br/>`/cd /duong/dan/tuyet/doi` | Chuyển sang thư mục dự án khác và bắt đầu phiên hội thoại mới tại đó. |
| `/pwd` | `/pwd` | Xem nhanh đường dẫn thư mục dự án hiện tại. |
| `/sessions` | `/sessions` | Lấy 10 phiên làm việc gần nhất (cả phiên tạo trên App máy tính lẫn trên Telegram). Bấm vào nút bên dưới tin nhắn để mở lại phiên đó. |
| `/new` | `/new` | Đóng phiên hiện tại, tin nhắn kế tiếp sẽ mở một cuộc hội thoại hoàn toàn mới. |
| `/stop` | `/stop` | Gửi tín hiệu huỷ (`session/cancel`) ngay lập tức nếu Agent đang chạy tác vụ quá lâu hoặc đi sai hướng. |

### Nhóm lệnh Cấu hình Agent (Model & Mode)
| Lệnh | Cú pháp & Ví dụ | Mô tả chi tiết |
| :--- | :--- | :--- |
| `/model` | `/model`<br/>`/model <model_id>` | Nếu không truyền tham số: liệt kê các model hiện có trong tài khoản của bạn. Nếu truyền `model_id`: chuyển ngay sang model đó. |
| `/mode` | `/mode default`<br/>`/mode accept-edits`<br/>`/mode plan` | Thay đổi chế độ kiểm duyệt của Agent (xem chi tiết ở Mục 2 bên dưới). |
| `/auto` | `/auto on`<br/>`/auto off` | Bật hoặc tắt chế độ tự động chấp thuận mọi yêu cầu quyền hạn của Agent mà không cần hỏi lại trên Telegram. |

### Nhóm lệnh Giao việc & Slash Commands của Antigravity
- **Tin nhắn văn bản thông thường**: Gửi trực tiếp yêu cầu lập trình, sửa lỗi, giải thích code...
- **Gửi ảnh (Photo) kèm chú thích (Caption)**: Chụp màn hình giao diện lỗi hoặc bản vẽ thiết kế gửi vào Bot kèm yêu cầu, Bot sẽ mã hóa ảnh sang Base64 và gửi trực tiếp cho model đa phương thức xử lý.
- **Slash Commands chuyên biệt của Antigravity**:
  - `/goal <mục tiêu>`: Yêu cầu Agent làm việc tự chủ, tự kiểm tra cho đến khi hoàn thành trọn vẹn mục tiêu.
  - `/plan <yêu cầu>`: Yêu cầu Agent lập kế hoạch chi tiết từng bước trước khi bắt tay vào sửa code.
  - `/browser <yêu cầu>`: Yêu cầu Agent sử dụng công cụ trình duyệt để kiểm tra web hoặc tra cứu.
  - *(Mọi lệnh `/...` không trùng với lệnh nội bộ của Bot đều được chuyển tiếp nguyên vẹn cho Antigravity Agent).*

---

## 2. Hiểu Rõ 3 Chế Độ Duyệt Quyền (`/mode`)

Để cân bằng giữa sự tiện lợi khi dùng trên điện thoại và tính an toàn cho mã nguồn, bạn có thể chuyển đổi linh hoạt giữa 3 chế độ:

1. **`accept-edits` (Mặc định — Khuyên dùng)**:
   - Agent được phép **tự động đọc và sửa file bên trong Workspace** hiện tại.
   - Khi Agent muốn **chạy lệnh Terminal/Shell** (`run_command`) hoặc thao tác ngoài vùng an toàn, Bot sẽ tạm dừng và hiện nút bấm xin phép bạn trên Telegram:
     - `✅ Allow once`: Cho phép chạy lệnh này 1 lần.
     - `🔓 Always allow`: Cho phép luôn loại lệnh này trong phiên.
     - `❌ Reject`: Từ chối, yêu cầu Agent tìm hướng khác.
     - `⚡ Tự duyệt mọi lệnh (/auto on)`: Cho phép và bật luôn Auto-approve.

2. **`default` (Kiểm soát chặt nhất)**:
   - Agent sẽ hỏi ý kiến bạn qua nút bấm Telegram **trước cả khi sửa bất kỳ file nào** và trước khi chạy lệnh shell. Phù hợp khi đang thao tác trên codebase nhạy cảm.

3. **`plan` (Lập kế hoạch trước)**:
   - Agent ưu tiên khảo sát codebase và trình bày phương án thiết kế trước khi thực thi thay đổi.

---

## 3. Cách Đổi Tài Khoản Google Cho Bot

Khi bạn muốn chuyển sang một tài khoản Google khác (hoặc khi phiên đăng nhập Google hết hạn sau thời gian dài):

### Cách 1: Dùng lệnh nhanh (Khuyên dùng)
- **Trên macOS / Linux / VPS:**
  ```bash
  ./service.sh login
  ```
- **Trên Windows (PowerShell):**
  ```powershell
  .\service.ps1 login
  ```
Lệnh này sẽ gọi `agy acp --login` để bạn xác thực tài khoản Google mới, sau đó **tự động khởi động lại dịch vụ nền của Bot Telegram** để áp dụng tài khoản mới ngay lập tức.

### Cách 2: Đổi thủ công qua giao diện `agy`
1. Mở Terminal / PowerShell, gõ `agy` rồi nhấn Enter.
2. Gõ `/logout` (hoặc `/auth`) để đăng xuất tài khoản cũ và đăng nhập tài khoản Google mới.
3. Thoát `agy` (`Ctrl + D` hai lần).
4. Khởi động lại bot: `./service.sh restart` (hoặc `.\service.ps1 restart` trên Windows).

---

## 4. Nguyên Tắc Bảo Mật Cốt Lõi

1. **Bắt buộc cấu hình `ALLOWED_USER_IDS`**:
   - Tuyệt đối không để lộ hoặc bỏ trống kiểm tra User ID. Chỉ những ID nằm trong danh sách này mới có thể tương tác và bấm nút duyệt lệnh trên Bot.
2. **Không bao giờ commit file `.env` lên Git**:
   - File `.gitignore` đã chặn sẵn `.env`, `data/`, và `logs/`. Trước khi `git push` lên GitHub công khai, hãy kiểm tra lại bằng `git status` để chắc chắn không đẩy nhầm Token cá nhân.
3. **Thói quen dùng Git trước khi giao việc lớn**:
   - Trước khi bật `/auto on` hoặc giao một lệnh `/goal` lớn từ xa, hãy nhắn Agent: *"Hãy git status và commit lại trạng thái hiện tại trước khi làm tính năng mới"* để luôn có điểm quay lui an toàn.
