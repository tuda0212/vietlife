# Hướng dẫn bổ sung: TikTok Trends Tracker

Module mở rộng cho file **"Vietlife - Google Trends VN"** đã cài trước đó. Tự động lấy **hashtag, âm thanh, creator đang trending tại Việt Nam** từ TikTok Creative Center mỗi 6 giờ, ghi vào cùng Google Sheet.

Yêu cầu: đã cài xong module Google Trends theo `HUONG-DAN-CAI-DAT.md`.
Thời gian cài thêm: ~3 phút.

---

## Bước 1 — Thêm file code TikTok

1. Mở Google Sheet "Vietlife - Google Trends VN" → **Tiện ích mở rộng → Apps Script** (vào đúng dự án đã có code Google Trends).
2. Bên trái, cạnh mục **Tệp (Files)** bấm dấu **+** → chọn **Tập lệnh (Script)** → đặt tên `TikTokTracker`.
3. Xóa nội dung mặc định, copy toàn bộ file `TikTok-Tracker.gs` dán vào → **Lưu** (Ctrl+S).
4. **Cập nhật file Code.gs cũ**: copy lại toàn bộ `Code.gs` mới (cùng thư mục này) đè lên nội dung cũ — bản mới đã thêm menu TikTok. Lưu.

## Bước 2 — Bật tự động cập nhật

1. Ở dropdown chọn hàm, chọn **`setupTikTokTrigger`** → bấm **Run**.
2. Cho phép quyền nếu Google hỏi (như lần trước).
3. Script chạy ngay lần đầu và tự lặp mỗi 6 giờ.

> Vì sao 6h/lần mà không phải 1h/lần? Bảng xếp hạng trends của TikTok Creative Center cập nhật **theo ngày**, chạy dày hơn không có dữ liệu mới, chỉ tốn quota. Muốn đổi: sửa `UPDATE_EVERY_HOURS` ở đầu file (chấp nhận 1, 2, 4, 6, 8, 12).

## Bước 3 — Đọc dữ liệu

4 tab mới trong Sheet:

| Tab | Nội dung | Dùng để |
|---|---|---|
| **TT_Hashtag** | Top 30 hashtag VN: hạng, biến động, lượt xem, chủ đề, vòng đời trend | Lên content plan TikTok/Reels |
| **TT_AmThanh** | Top nhạc/âm thanh trending tuần | Chọn nhạc nền video bắt trend |
| **TT_Creator** | Creator nổi bật VN: follower, lượt thích, link kênh | Sàng lọc KOC/KOL hợp tác |
| **TT_Dashboard** | Hashtag y tế đang trending ⭐, hashtag tăng nhanh hôm nay, trend dài hạn, nhạc hot | Họp content |

Tab **NhatKy** ghi trạng thái mỗi lần chạy (OK / MOT_PHAN / LOI) — nếu thấy LOI liên tục vài ngày nghĩa là TikTok đã đổi endpoint, cần vá lại code.

Menu **📈 Trends Tracker** trên Sheet giờ có thêm: **Cập nhật TikTok ngay** và **Bật tự động TikTok 6h/lần**.

---

## Cách phân tích trends TikTok cho content Vietlife

**Hashtag được phân loại 3 lớp như Google Trends:**

1. **Chủ đề content** — nhận diện cả hashtag viết liền không dấu (#suckhoe, #benhvien, #xuongkhop → Sức khỏe - Y tế).
2. **Vòng đời** — tính theo số ngày hashtag trụ trên bảng trending: dưới 3 ngày = ngắn hạn (bắt trend nhanh), 3–14 ngày = trung hạn (series video), trên 14 ngày = dài hạn (đầu tư content chuyên sâu + quảng cáo).
3. **Trạng thái động lượng** — so hạng với lần ghi trước: **Mới vào bảng** (cửa sổ vàng để bắt trend sớm), **Đang tăng** (làm ngay trong 1–2 ngày), **Đang giảm** (bỏ qua, trend đã nguội), **Ổn định**.

**Gợi ý quy trình hàng tuần:** thứ 2 mở TT_Dashboard xem mục 1 (hashtag y tế) và mục 3 (trend dài hạn) để chốt 2–3 video chủ lực; hàng ngày xem mục 2 (đang tăng) để quyết định video bắt trend nhanh, ưu tiên hashtag "Mới vào bảng" có lượt xem cao; chọn nhạc từ mục 4 — lưu ý kiểm tra bản quyền nhạc khi dùng cho tài khoản doanh nghiệp (TikTok Business chỉ được dùng Commercial Music Library).

---

## Lưu ý quan trọng về độ ổn định

Dữ liệu lấy từ endpoint nội bộ của [TikTok Creative Center](https://ads.tiktok.com/business/creativecenter) — TikTok **không có API trends chính thức** cho doanh nghiệp, nên endpoint này có thể bị TikTok thay đổi/chặn bất kỳ lúc nào. Khi tab NhatKy báo LOI kéo dài:

1. Kiểm tra trang Creative Center trên trình duyệt còn hoạt động không.
2. Phương án dự phòng trả phí: [Apify TikTok Creative Center Scraper](https://apify.com/doliz/tiktok-creative-center-scraper) (~$5–20/tháng, có free credit $5/tháng) — liên hệ tôi để tích hợp, chỉ cần đổi hàm lấy dữ liệu, toàn bộ phân loại và dashboard giữ nguyên.
