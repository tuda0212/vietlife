---
name: pancake-chat-analysis
description: |
  Hỗ trợ tải dữ liệu hội thoại từ Pancake Chat API cho một Page ID cụ thể, tóm tắt và thực hiện các phân tích chuyên sâu (Chân dung khách hàng, Điểm nghẽn tư vấn, Tối ưu kịch bản chat, Tối ưu quảng cáo Ads).
  Kích hoạt khi người dùng cung cấp Page ID hoặc yêu cầu phân tích dữ liệu chat từ Pancake.
license: Apache-2.0
metadata:
  version: v1
  publisher: local
---

# Skill Phân Tích Hội Thoại Pancake Chat

Skill này hướng dẫn Agent cách hỗ trợ người dùng trích xuất dữ liệu chat từ hệ thống Pancake Chat (pages.fm) qua API và thực hiện các phân tích chuyên sâu nhằm tối ưu hóa tỷ lệ chuyển đổi và chiến dịch marketing.

## Quy Trình Xử Lý (BẮT BUỘC)

Khi người dùng cung cấp **Page ID** (hoặc yêu cầu phân tích dữ liệu chat Pancake):

### Bước 1: Thu thập thông tin xác thực (Token)
1. Kiểm tra xem đã có biến môi trường `PANCAKE_PAGE_ACCESS_TOKEN` hoặc `FB_ACCESS_TOKEN` trong tệp `.env` chưa.
2. Nếu chưa có, hãy lịch sự yêu cầu người dùng cung cấp **Page Access Token** để kết nối API.
3. *Lưu ý*: Nếu người dùng muốn thử nghiệm không cần token thật, hãy chạy kịch bản ở chế độ giả lập (`--dummy`).

### Bước 2: Tải dữ liệu hội thoại
Sử dụng công cụ `run_command` để chạy script Python tải dữ liệu (sử dụng môi trường ảo `.venv` nếu có):
```bash
# Ưu tiên sử dụng python từ môi trường ảo nếu có .venv
/Users/daudau/VL/.venv/bin/python3 /Users/daudau/VL/.agents/skills/pancake-chat-analysis/scripts/fetch_pancake_chats.py --page-id <PAGE_ID> --token <TOKEN> --limit 20 --output /Users/daudau/VL/pancake_chats_temp.json

# Hoặc sử dụng python3 hệ thống
python3 /Users/daudau/VL/.agents/skills/pancake-chat-analysis/scripts/fetch_pancake_chats.py --page-id <PAGE_ID> --token <TOKEN> --limit 20 --output /Users/daudau/VL/pancake_chats_temp.json
```
*(Nếu chạy giả lập để kiểm thử, thêm tham số `--dummy`)*.

### Bước 3: Đọc và hiển thị tóm tắt dữ liệu
1. Đọc tệp `/Users/daudau/VL/pancake_chats_temp.json` bằng công cụ `view_file`.
2. Hiển thị bảng tóm tắt ngắn gọn các hội thoại tải được:
   - Tổng số cuộc hội thoại.
   - Danh sách khách hàng và các nhãn (tags) được gắn kèm (nếu có).
   - Tần suất các tag xuất hiện nhiều nhất (ví dụ: "Khách Quan Tâm", "Khách Than Đắt", v.v.).

### Bước 4: Gợi ý các tính năng phân tích (Menu Chức Năng)
Đưa ra menu lựa chọn cho người dùng:
> **Bạn muốn thực hiện phân tích nào dưới đây cho dữ liệu vừa tải?**
> 1. **Phân tích Chân dung Khách hàng (Customer Persona)**: Thấu hiểu nhu cầu, độ tuổi, triệu chứng bệnh lý và rào cản tâm lý của khách hàng.
> 2. **Phát hiện Điểm nghẽn Quy trình Tư vấn (Bottlenecks)**: Phân tích tốc độ trả lời, cách tư vấn rập khuôn, và lý do thất bại khi chốt hẹn.
> 3. **Tối ưu Kịch bản Chat & Xử lý Từ chối (Script Optimization)**: Đề xuất kịch bản tư vấn mới, cách báo giá tinh tế và mẫu câu xử lý từ chối (chê đắt, hỏi ý kiến người thân).
> 4. **Tối ưu Chiến dịch Quảng cáo (Facebook Ads)**: Gợi ý các góc viết bài quảng cáo (Hooks), các từ khóa khách hàng hay dùng, và đề xuất Target đối tượng cụ thể trên Ads Manager.

---

## Các Khung Phân Tích Chi Tiết (Prompts của Agent)

Khi người dùng chọn một hoặc nhiều mục, Agent sẽ sử dụng dữ liệu hội thoại trong file JSON để thực hiện phân tích theo các cấu trúc dưới đây:

### 1. Phân tích Chân dung Khách hàng (Customer Persona)
Phân tích dữ liệu để trả lời các câu hỏi:
- **Ai là người nhắn tin chính?** (Bệnh nhân trực tiếp hay người thân hỏi hộ? Độ tuổi và giới tính thường gặp).
- **Mối quan tâm sức khỏe lớn nhất?** (Họ hỏi về triệu chứng gì? Cần tầm soát hay khám bệnh cụ thể nào?).
- **Rào cản tâm lý chính?** (Giá cả, lo lắng công nghệ MRI, khoảng cách địa lý, cần hỏi gia đình...).

### 2. Phát hiện Điểm nghẽn Tư vấn (Bottlenecks)
Đánh giá chất lượng của tư vấn viên trực page:
- **Tốc độ phản hồi**: Có phản hồi chậm làm khách hàng mất kiên nhẫn không?
- **Chất lượng nội dung**: Nhân viên có trả lời máy móc, sao chép văn bản mẫu không phù hợp không? Giải thích về MRI hoặc chi phí đã rõ ràng chưa?
- **Kỹ năng xử lý từ chối**: Khi khách hàng ngập ngừng hoặc chê giá cao, tư vấn viên phản ứng thế nào? Có thuyết phục được họ không?

### 3. Tối ưu Kịch bản Chat & Xử lý Từ chối
Đề xuất bảng so sánh kịch bản tư vấn cũ vs kịch bản tối ưu mới:
- **Kịch bản mở lời**: Cách khai thác triệu chứng trước khi báo giá.
- **Kịch bản báo giá thông minh**: Báo giá đi kèm giá trị công nghệ (như chụp MRI không tiếng ồn, kết quả chính xác cao).
- **Mẫu câu xử lý khi khách chê đắt**: Nhấn mạnh vào chẩn đoán sớm để phòng ngừa rủi ro lớn hơn (Đột quỵ, U não).
- **Mẫu câu xử lý khi khách hẹn "hỏi lại gia đình"**: Xin thông tin hỗ trợ tư vấn trực tiếp cho người thân.

### 4. Tối ưu Chiến dịch Quảng cáo (Facebook Ads)
Đề xuất các phương án quảng cáo dựa trên Insights thực tế của khách hàng:
- **Mẫu Tiêu đề Quảng cáo (Hooks)**: Tạo 3 tiêu đề đánh thẳng vào các triệu chứng khách hàng thường kể nhất (Ví dụ: "Đau đầu, mất ngủ triền miên...").
- **Từ khóa thực tế từ khách hàng**: Các cụm từ cần đưa vào bài viết quảng cáo (Ví dụ: "MRI không đau", "trọn gói không phát sinh").
- **Targeting**: Đề xuất thiết lập target độ tuổi, sở thích trên Ads Manager phù hợp với chân dung người trả tiền.
