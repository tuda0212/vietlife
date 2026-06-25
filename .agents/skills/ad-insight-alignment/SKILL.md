---
name: ad-insight-alignment
description: |
  Đánh giá hiệu quả nội dung quảng cáo (Ad Copy) và đối chiếu độ khớp insight bằng cách phân tích dữ liệu chat Pancake và ad creatives.
  Hỗ trợ phân tích động theo từng Bác sĩ (tra cứu từ cấu hình bảo mật pages_config.json) và lọc theo khoảng thời gian tùy chỉnh.
  Tính toán tỷ lệ SĐT, tỷ lệ đặt lịch, phân phối các Pain Points thực tế (chi phí, triệu chứng, sợ phẫu thuật) để chỉ ra nguyên nhân thành công/thất bại và đề xuất tối ưu.
---

# Skill Đối Chiếu Độ Khớp Insight & Đánh Giá Content Quảng Cáo (Đa Fanpage & Theo Thời Gian)

Skill này hướng dẫn Agent cách thực hiện một cuộc kiểm định marketing (marketing audit) dựa trên dữ liệu cho **từng bác sĩ cụ thể** và trong **khoảng thời gian tùy chỉnh** bằng cách truy cập cấu hình bảo mật Fanpage và chạy các bộ lọc tương ứng.

---

## 🏗️ Quy Trình Thực Hiện (BẮT BUỘC)

Khi người dùng yêu cầu phân tích một trang bác sĩ cụ thể hoặc một khoảng thời gian, ví dụ:
* *"Hãy phân tích content trang bác sĩ Tuyên từ 2026-06-01 đến 2026-06-20"*
* *"Xem hiệu quả ad-insight của Bác sĩ Duy trong tuần trước"*

Agent phải tuân thủ nghiêm ngặt quy trình dưới đây:

### Bước 1: Tra cứu cấu hình Bác sĩ (Doctor Lookup)
1. Đọc tệp cấu hình bảo mật `pages_config.json` tại đường dẫn:
   `/.agents/skills/ad-insight-alignment/scripts/pages_config.json`
2. Đối chiếu tên bác sĩ người dùng yêu cầu để lấy ra:
   * `page_id`
   * `pancake_token`
   * `doctor_name` (Tên chuẩn hóa)
3. Nếu không tìm thấy bác sĩ yêu cầu trong tệp cấu hình, hãy liệt kê danh sách các bác sĩ đang có sẵn để người dùng lựa chọn.

### Bước 2: Chuẩn hóa khoảng thời gian (Date Normalization)
1. Xác định khoảng thời gian bắt đầu (`since` / `StartDate`) và kết thúc (`until` / `EndDate`) từ yêu cầu của người dùng.
2. Chuẩn hóa về định dạng `YYYY-MM-DD`. 
   * *Ví dụ:* "Tháng 6 năm 2026" -> StartDate: `2026-06-01`, EndDate: `2026-06-30`.
   * Nếu người dùng không chỉ định khoảng thời gian, mặc định lấy 30 ngày gần nhất.

### Bước 3: Tải dữ liệu chat Pancake theo bộ lọc (Fetch Chats)
Sử dụng công cụ `run_command` để chạy script Python tải dữ liệu chat của đúng trang bác sĩ đó trong khoảng thời gian yêu cầu:
```bash
# Định dạng lệnh chạy:
python .agents/skills/pancake-chat-analysis/scripts/fetch_pancake_chats.py --page-id <PAGE_ID> --token <TOKEN> --since <START_DATE> --until <END_DATE> --limit 100 --output pancake_chats_with_ads.json
```
*(Thay thế `<PAGE_ID>`, `<TOKEN>`, `<START_DATE>`, `<END_DATE>` bằng dữ liệu thật vừa tra cứu được. Dữ liệu tải về sẽ được lưu đè vào file `pancake_chats_with_ads.json` ở thư mục gốc).*

### Bước 4: Chạy Phân Tích Định Lượng (Analyze)
Chạy script PowerShell để thực hiện thống kê và lọc khoảng thời gian cục bộ:
```powershell
powershell -File .\.agents\skills\ad-insight-alignment\scripts\analyze_pancake_ads.ps1 -StartDate <START_DATE> -EndDate <END_DATE>
```
*(Script sẽ đọc dữ liệu chat mới tải về, ghép nối với `ad_creatives.json` và tạo ra tệp báo cáo tổng quan `evaluation_report.md` tại thư mục gốc).*

### Bước 5: Đọc và Trình bày Báo cáo cho Người dùng
1. Đọc tệp `evaluation_report.md` bằng công cụ `view_file`.
2. Hiển thị báo cáo chi tiết, nhấn mạnh vào:
   * Tổng số chat thu được trong kỳ.
   * Tỷ lệ cung cấp SĐT và Tỷ lệ Đặt Lịch của bác sĩ đó.
   * Các Pain Points nổi bật nhất của khách hàng thuộc chuyên khoa của bác sĩ này.
   * So sánh content của các bài tốt/kém để đề xuất giải pháp tối ưu hóa.
