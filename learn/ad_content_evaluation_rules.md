# Hướng Dẫn Logic & Quy Tắc Đồng Bộ Dữ Liệu `ad_content_evaluation`

Tài liệu này ghi lại toàn bộ logic nghiệp vụ, quy tắc xử lý dữ liệu và cấu hình hệ thống đã được tối ưu hóa cho bảng `ad_content_evaluation` trong BigQuery. **Bắt buộc đọc tài liệu này trước khi chỉnh sửa bất kỳ phần nào của pipeline.**

---

## 📌 1. Quy Tắc Trích Xuất Tên Quảng Cáo (`ad_name`)

Tên quảng cáo của Facebook Ads được đặt theo cú pháp chuẩn:
`Angle_tên bài_id post fb` (Ví dụ: `Khám Bệnh_L45 cúi người_1451045407022501`)

Khi đồng bộ và tổng hợp dữ liệu, hệ thống áp dụng các quy tắc trích xuất sau:

### A. Quy tắc tách chính (Split):
*   Tách `ad_name` bằng dấu gạch dưới `_`.
*   `angle` (Góc tiếp cận) = Phần thứ 1 (Ví dụ: `Khám Bệnh`).
*   `ad_post_name` (Tên bài viết) = Phần thứ 2 (Ví dụ: `L45 cúi người`).

### B. Quy tắc xử lý trường hợp đặc biệt:
1.  **Dữ liệu Organic (Tự nhiên)**:
    *   Nếu `ad_name = 'Organic'`, gán trực tiếp:
        *   `angle = 'Organic'`
        *   `ad_post_name = 'Organic'`
    *   *(Tránh việc gom dữ liệu Organic vào nhóm `Unknown` trên Looker Studio).*
2.  **Tên quảng cáo bắt đầu bằng dấu gạch dưới `_`**:
    *   Ví dụ: `_giơ 2 tay_...` hay `_TEO_...`
    *   **Bắt buộc giữ nguyên khoảng trống (blank) cho `angle`** (tức là phần 1 của split sẽ là chi tiết chuỗi rỗng `""`). **KHÔNG** tự động cắt bỏ (trim) dấu gạch dưới ở đầu.
3.  **Tên quảng cáo đặt tự do hoặc dạng ID số** (Không chứa dấu gạch dưới `_`):
    *   Áp dụng logic fallback tìm kiếm từ khóa cũ (Ví dụ: nếu chứa "feedback" thì angle là "Feedback", chứa "chuyen_gia" thì angle là "Chuyên gia", còn lại là "Unknown").

---

## ⚙️ 2. Cấu Hình & Tối Ưu Hệ Thống

### A. Xác thực Google Sheets CRM (Tránh `RefreshError`):
*   Đồng bộ CRM từ Google Sheets **bắt buộc** sử dụng Service Account thay vì token đăng nhập cá nhân (gcloud CLI) khi chạy lịch trình dài.
*   Cấu hình biến `GOOGLE_APPLICATION_CREDENTIALS` trong file `.env` trỏ đến file credentials Service Account (Ví dụ: `/Users/daudau/secrets/vietlife-sa.json`).
*   Hàm `_get_sheets_service()` trong [sheets_reader.py](file:///Users/daudau/.gemini/antigravity/worktrees/VL/evaluate-ad-content-feature/files/sheets_reader.py) sẽ tự động ưu tiên Service Account này để tự động refresh token vĩnh viễn.

### B. BigQuery Partition Expiration:
*   Bảng `ad_content_evaluation` phân vùng theo ngày (`date`) **không được phép cài đặt thời gian hết hạn phân vùng (partition expiration)**. 
*   Đảm bảo tùy chọn `partition_expiration_days` luôn là `NULL` để tránh BigQuery tự động xóa dữ liệu lịch sử cũ hơn 60 ngày.

### C. Tối ưu hóa hiệu năng Pancake API:
*   Không gọi API con `/messages` để quét từng tin nhắn tìm SĐT.
*   Đọc trực tiếp từ metadata của cuộc trò chuyện trong API `/conversations`:
    *   Nhận diện SĐT: `has_phone: true` hoặc thông tin trong `recent_phone_numbers`.
    *   Phản hồi của page: check `last_sent_by` có phải của page/admin hay không để tính tỷ lệ phản hồi (`reply_rate`).
*   Chia nhỏ khoảng thời gian query Pancake API dưới **15 ngày** mỗi chunk để tránh lỗi giới hạn 1 tháng của Pancake.
