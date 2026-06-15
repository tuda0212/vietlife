# Hướng dẫn cài đặt: Vietlife Google Trends Tracker

Tự động lấy chủ đề trending tại Việt Nam về Google Sheet **mỗi 1 giờ**, kèm phân loại content phục vụ kế hoạch marketing.

Thời gian cài đặt: ~5 phút. Không cần biết lập trình.

---

## Bước 1 — Tạo Google Sheet mới

1. Vào [sheets.new](https://sheets.new) (đăng nhập tài khoản Google của Vietlife).
2. Đặt tên file, ví dụ: **"Vietlife - Google Trends VN"**.

## Bước 2 — Dán code

1. Trên thanh menu của Sheet: **Tiện ích mở rộng (Extensions) → Apps Script**.
2. Xóa toàn bộ code mẫu trong khung soạn thảo.
3. Mở file `Code.gs` (cùng thư mục với file hướng dẫn này), copy **toàn bộ** nội dung và dán vào.
4. Bấm biểu tượng 💾 **Lưu** (hoặc Ctrl+S).

## Bước 3 — Bật tự động cập nhật 1h/lần

1. Trong Apps Script, ở dropdown chọn hàm (cạnh nút Run), chọn **`setupTrigger`**.
2. Bấm **Run (Chạy)**.
3. Google sẽ hỏi cấp quyền → chọn tài khoản → **Advanced (Nâng cao) → Go to... (Tiếp tục) → Allow (Cho phép)**. Đây là quyền cho script của chính bạn, an toàn.
4. Xong. Script chạy ngay lần đầu và tự lặp lại mỗi 1 giờ, kể cả khi tắt máy (chạy trên server Google).

## Bước 4 — Đọc dữ liệu

Quay lại Google Sheet, sẽ có 3 tab:

| Tab | Nội dung | Dùng để |
|---|---|---|
| **DangTrending** | Snapshot các chủ đề đang hot ngay lúc này | Bắt trend nhanh trong ngày |
| **DuLieuTho** | Toàn bộ lịch sử tích lũy (có cột Năm/Tháng/Ngày/Giờ) | Lọc, pivot theo giờ / ngày / tháng / năm |
| **Dashboard** | Phân bổ chủ đề hôm nay, top từ khóa y tế 30 ngày, xu hướng dài hạn, trend ngắn hạn hôm nay | Họp content hàng tuần |

Menu **📈 Trends Tracker** trên thanh công cụ Sheet có nút **Cập nhật ngay** khi cần dữ liệu tức thì.

---

## Cách hệ thống phân loại content

**Theo chủ đề** (dựa trên từ khóa + tiêu đề tin liên quan): Sức khỏe - Y tế ⭐, Giải trí, Thể thao, Thời sự - Xã hội, Công nghệ, Giáo dục - Hữu ích, Khác.

**Theo vòng đời xu hướng** (số giờ chủ đề tồn tại trên bảng trending):

| Loại | Thời gian tồn tại | Gợi ý hành động content |
|---|---|---|
| Xu hướng ngắn hạn | dưới 24h | Bắt trend nhanh: Reels/TikTok/post Fanpage trong ngày |
| Xu hướng trung hạn | 1–7 ngày | Bài blog SEO, video giải thích, mini-series |
| Xu hướng dài hạn | trên 7 ngày | Content chuyên sâu, pillar page, chiến dịch quảng cáo |

**Theo giá trị với người dùng:**

| Tính chất | Nguồn | Ý nghĩa cho Vietlife |
|---|---|---|
| Giá trị cho người dùng | Sức khỏe - Y tế, Giáo dục - Hữu ích | Ưu tiên cao nhất — đúng chuyên môn, xây uy tín, kéo đặt lịch khám |
| Giải trí / bắt trend | Giải trí, Thể thao | Dùng làm content viral, "mượn trend" khéo léo gắn thông điệp sức khỏe |
| Thời sự / cập nhật | Thời sự - Xã hội | Phản ứng nhanh khi liên quan y tế (dịch bệnh, thời tiết, ATTP) |
| Cần đánh giá thủ công | Khác | Đội content review thêm |

Muốn thêm/bớt từ khóa phân loại: mở Apps Script, sửa danh sách `CATEGORY_RULES` ở đầu file (có chú thích tiếng Việt).

---

## Câu hỏi thường gặp

**Dữ liệu lấy từ đâu, có chính thống không?**
Từ feed RSS "Trending Now" chính thức của Google Trends (geo=VN) — cùng dữ liệu hiển thị tại trends.google.com/trending. Script có sẵn endpoint dự phòng nếu Google đổi đường dẫn.

**Có mất phí không?** Không. Apps Script + trigger hàng giờ nằm trong hạn mức miễn phí của Google.

**Sheet có bị đầy không?** Mỗi giờ ghi ~10–25 dòng, một năm ~150–200 nghìn dòng — vẫn trong giới hạn 10 triệu ô của Google Sheets. Nên tạo file mới mỗi năm.

**Muốn theo dõi mức độ quan tâm theo bộ từ khóa dịch vụ Vietlife (cơ xương khớp, nội soi...)?**
Feed trending không hỗ trợ từ khóa tùy chọn. Đó là bước nâng cấp tiếp theo: dùng API trả phí (SerpApi ~$50/tháng) hoặc đăng ký [Google Trends API alpha](https://developers.google.com/search/apis/trends). Liên hệ lại khi cần, tôi sẽ tích hợp thêm.
