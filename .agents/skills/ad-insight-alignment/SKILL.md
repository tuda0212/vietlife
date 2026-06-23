---
name: ad-insight-alignment
description: |
  Đánh giá hiệu quả nội dung quảng cáo (Ad Copy) và đối chiếu độ khớp insight bằng cách phân tích dữ liệu chat Pancake và ad creatives.
  Tính toán tỷ lệ SĐT, tỷ lệ đặt lịch, phân phối các Pain Points thực tế (chi phí, triệu chứng, sợ phẫu thuật) để chỉ ra nguyên nhân thành công/thất bại và đề xuất tối ưu.
---

# Skill Đối Chiếu Độ Khớp Insight & Đánh Giá Content Quảng Cáo

Skill này hướng dẫn Agent cách thực hiện một cuộc kiểm định marketing (marketing audit) dựa trên dữ liệu bằng cách đối chiếu trực tiếp thông điệp quảng cáo (Ad Copy) với dữ liệu trò chuyện thực tế của khách hàng từ Pancake Chat để tìm ra các bài viết hiệu quả nhất (Good Ads) và bài viết kém hiệu quả (Bad Ads).

---

## 🏗️ Quy Trình Thực Hiện (BẮT BUỘC)

Khi người dùng yêu cầu "đánh giá content quảng cáo", "đối chiếu insight" hoặc khi bạn cần phân tích hiệu quả các chiến dịch Ads dựa trên dữ liệu chat Pancake:

### Bước 1: Chạy Script Phân Tích Định Lượng (PowerShell)
Sử dụng công cụ `run_command` để chạy script PowerShell trích xuất số liệu thống kê:
```powershell
powershell -File .\.agents\skills\ad-insight-alignment\scripts\analyze_pancake_ads.ps1
```
*Lưu ý:* Script này chạy hoàn toàn bằng ASCII để tương thích với Windows, tự động đọc dữ liệu từ `pancake_chats_with_ads.json`, `ad_creatives.json` và tệp cấu hình từ khóa `keywords.json` để tạo ra tệp báo cáo tổng quan `evaluation_report.md`.

### Bước 2: Đọc báo cáo định lượng vừa sinh ra
Đọc tệp `evaluation_report.md` tại thư mục gốc của dự án bằng công cụ `view_file`.

### Bước 3: Phân tích định tính & Bóc tách sâu (AI Analysis)
Dựa trên số liệu từ báo cáo, hãy thực hiện phân tích chuyên sâu cho người dùng theo các khía cạnh:

1. **Phân loại Nhóm Bài viết:**
   * **Nhóm bài Tốt (High Performers):** Các bài có tỷ lệ cung cấp SĐT >= 30% và tỷ lệ đặt lịch >= 15%. Phân tích xem tại sao họ thành công (Góc tiếp cận nào? Hook gì?).
   * **Nhóm bài Lệch Pha Giá (Cost Mismatch):** Tỷ lệ khách hỏi về giá rất cao (>50%) nhưng tỷ lệ chốt SĐT/đặt lịch lại rất thấp. Đánh giá xem có phải do bài viết chưa nêu bật giá trị dịch vụ trước khi khách hỏi giá hay không.
   * **Nhóm bài Sai Tệp/Spam:** Tỷ lệ khách hỏi về triệu chứng bệnh dưới 40% (khách click nhầm hoặc tương tác rác).

2. **Bản đồ Pain Points theo Chuyên khoa & Fanpage:**
   * Tổng hợp xem với mỗi nhóm đối tượng (ví dụ: bệnh nhân của BS Tuyên, BS Định về Cột sống), nỗi lo sợ lớn nhất của họ là gì (Chi phí, Sợ mổ, hay Triệu chứng đau).
   * Ví dụ: Bài viết nói về việc "Mổ xong vẫn tê chân" sẽ kích hoạt nỗi sợ mổ rất lớn (40-50% khách chat nhắc đến sợ mổ) nhưng lại thu hút tệp khách hàng rất nét.

3. **Đề xuất Hành động (Actionable Recommendations):**
   * Đề xuất hướng viết bài mới cho phòng Marketing (Ad Copy mới dựa trên Pain Point phổ biến nhất).
   * Đề xuất kịch bản phản hồi (Sales Script) cho tư vấn viên trực page để giải quyết đúng rào cản lớn nhất của khách hàng (ví dụ: cách giải quyết khi khách chê đắt hoặc sợ đau).

### Bước 4: Trình bày Báo cáo cho Người dùng
Xuất báo cáo cuối cùng cho người dùng theo định dạng Markdown trực quan, tập trung vào các kết luận cốt lõi và các gợi ý cải tiến thực chiến.

---

## 🎯 Cấu Trúc Báo Cáo Đầu Ra Khuyến Nghị

Báo cáo gửi cho người dùng nên có cấu trúc như sau:
1. **Tổng quan số liệu:** Tổng số chat, tỷ lệ chốt SĐT trung bình toàn hệ thống.
2. **Top 3 Bài Ads Đột Phá:** Chỉ số và góc tiếp cận thành công.
3. **Top 3 Bài Ads Cần Tối Ưu/Tắt:** Chỉ số kém, lý do thất bại (sai tệp, lệch giá).
4. **Bản đồ Tâm lý Khách hàng (Pain Points):** Tỷ lệ phần trăm các mối bận tâm của khách theo chuyên khoa.
5. **Đề xuất Ad Copy & Kịch bản Chat mới:** Các mẫu tiêu đề (Hooks) và câu thoại chốt hẹn tối ưu.
