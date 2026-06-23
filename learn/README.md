# Tài Liệu Nghiên Cứu & Tích Hợp Phân Tích Chat Pancake

Thư mục này chứa tài liệu và mã nguồn mẫu phục vụ cho mục tiêu **Tích hợp Pancake Chat API, thu thập lịch sử hội thoại khách hàng và ứng dụng trí tuệ nhân tạo (AI) để phân tích chân dung khách hàng, tối ưu kịch bản tư vấn và tối ưu hóa hiệu quả quảng cáo**.

---

## 🎯 Mục Tiêu Dự Án

```
  [Pancake Chat API] ──(fetch_chats_sample.py)──► [Dữ liệu JSON]
                                                         │
  [Kịch bản tư vấn & Ads mới] ◄──(AI Prompts)────────────┘
```

1. **Lấy dữ liệu chat tự động:** Sử dụng API chính thức của Pancake để kéo dữ liệu các cuộc hội thoại và nội dung tin nhắn chi tiết của khách hàng về máy chủ cục bộ hoặc database.
2. **Tổng hợp & Phân tích nội dung:** Nhận diện các cuộc hội thoại thành công (chốt được hẹn) và thất bại, từ đó phân tích các chủ đề chính mà khách hàng quan tâm.
3. **Xây dựng chân dung khách hàng (Persona):** Xác định nhân khẩu học, triệu chứng bệnh lý, mối bận tâm và các rào cản tâm lý của khách hàng khi tìm kiếm dịch vụ tại Vietlife Clinic.
4. **Phát hiện lỗi & Tối ưu kịch bản:** Tìm ra các điểm nghẽn trong quy trình tư vấn hiện tại (tốc độ trả lời, cách báo giá, xử lý từ chối) và thiết kế lại kịch bản tối ưu.
5. **Tối ưu Ads (Marketing):** Dịch chuyển thông điệp quảng cáo sát với ngôn ngữ và nhu cầu thực tế của khách hàng từ dữ liệu chat, đồng thời tinh chỉnh đối tượng mục tiêu (targeting).

---

## 📂 Danh Sách Tài Liệu Trong Thư Mục `learn/`

Để bắt đầu triển khai, bạn hãy tham khảo các tài liệu và công cụ dưới đây theo thứ tự:

1. 📖 **[Hướng Dẫn Tích Hợp Pancake Chat API (pancake_api_guide.md)](pancake_api_guide.md)**
   * Hướng dẫn chi tiết cách lấy User Access Token, Page Access Token từ giao diện Pancake.
   * Chi tiết cấu trúc các endpoint `GET` lấy danh sách trang, cuộc trò chuyện, lịch sử tin nhắn và cấu hình Webhook thời gian thực.

2. 🐍 **[Script Cào Dữ Liệu Chat Mẫu (fetch_chats_sample.py)](fetch_chats_sample.py)**
   * Script Python mẫu sử dụng thư viện `requests` để tự động hóa việc gọi API Pancake, xử lý phân trang, quản lý rate limit và lưu dữ liệu thành file JSON.
   * Chế độ giả lập tự sinh tệp `pancake_chats_dummy.json` để bạn thử nghiệm quy trình phân tích ngay cả khi chưa có token thật.

3. 🤖 **[Prompts Phân Tích Với AI (chat_analysis_prompt.md)](chat_analysis_prompt.md)**
   * Bộ khung System Prompts chuyên sâu được tối ưu riêng cho LLM (Gemini, GPT) để thực hiện:
     * *Phân tích Chân dung khách hàng.*
     * *Phát hiện điểm nghẽn tư vấn.*
     * *Viết lại kịch bản phản hồi xử lý từ chối.*
     * *Đề xuất thông điệp & target tối ưu Facebook Ads.*

4. 📊 **[Báo Cáo Phân Tích Thực Tế Bình An Nano (pancake_chat_analysis_report.md)](pancake_chat_analysis_report.md)**
   * Báo cáo phân tích chi tiết dựa trên dữ liệu thật của 200 cuộc hội thoại vừa tải về.
   * Chỉ rõ các lỗi thực tế trong kịch bản cũ (Spam bot tự động, lặp câu hỏi, báo giá quá sớm).
   * Đề xuất kịch bản tư vấn mới tối ưu chuyển đổi và định hướng quảng cáo Facebook Ads thực chiến.

5. 📢 **[Hướng Dẫn Facebook Ads & Commerce Platform (facebook_ads_commerce_guide.md)](facebook_ads_commerce_guide.md)**
   * Hướng dẫn chi tiết cách tích hợp Marketing API (tạo chiến dịch, ad set, ad creative, ad), Ads Insights API, Commerce Manager (Product Catalog, Product Feeds) và Conversions API.

---

## 🚀 Các Bước Triển Khai Tiếp Theo

1. **Bước 1: Cấu hình và chạy thử Script kéo dữ liệu**
   * Đăng nhập vào tài khoản Pancake và lấy Page Access Token cho fanpage cần phân tích.
   * Thiết lập biến môi trường và chạy thử script:
     ```bash
     export PANCAKE_PAGE_ID="id_trang_cua_ban"
     export PANCAKE_PAGE_ACCESS_TOKEN="token_trang_cua_ban"
     python3 learn/fetch_chats_sample.py
     ```
   * Nếu chưa cấu hình token, bạn có thể chạy chay script để tạo ra file dữ liệu giả lập mẫu `pancake_chats_dummy.json`.

2. **Bước 2: Phân tích dữ liệu bằng LLM**
   * Sao chép nội dung file JSON thu được.
   * Truy cập các công cụ AI (Gemini hoặc ChatGPT) và sử dụng các prompt trong tệp **[chat_analysis_prompt.md](chat_analysis_prompt.md)** để trích xuất báo cáo phân tích.

3. **Bước 3: Thử nghiệm thực tế & Đo lường**
   * Đào tạo đội ngũ tư vấn viên trực page áp dụng kịch bản xử lý từ chối mới.
   * Tạo bài viết quảng cáo mới (Ad Copy) sử dụng các "Hooks" đề xuất từ AI và đo lường sự thay đổi của chi phí trên mỗi tin nhắn (Cost per Message - CPM/CPR) cùng tỷ lệ chốt hẹn khám thực tế.
