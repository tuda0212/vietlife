# Hướng Dẫn Sử Dụng AI Phân Tích Dữ Liệu Chat Pancake

Sau khi sử dụng script trích xuất dữ liệu chat từ Pancake API để tạo ra file JSON chứa lịch sử hội thoại, bạn có thể đưa dữ liệu này vào các mô hình AI (như Google Gemini, OpenAI GPT) kết hợp với các Prompt chuyên biệt dưới đây để thực hiện phân tích sâu.

---

## Prompt 1: Tổng Hợp & Phân Tích Chân Dung Khách Hàng (Customer Persona)

**Mục tiêu:** Hiểu rõ đối tượng đang tương tác là ai, nhu cầu thực sự của họ là gì, điều gì thúc đẩy hoặc cản trở họ quyết định đăng ký dịch vụ.

```markdown
Bạn là một chuyên gia phân tích dữ liệu khách hàng (Customer Insights Analyst) trong lĩnh vực y tế và chăm sóc sức khỏe. 
Dưới đây là dữ liệu lịch sử chat của khách hàng với phòng khám Vietlife Clinic (dưới dạng JSON):

[DÁN DỮ LIỆU JSON CHAT VÀO ĐÂY]

Hãy đọc kỹ lịch sử hội thoại và thực hiện phân tích chi tiết chân dung khách hàng theo các mục sau:
1. **Phân loại nhóm đối tượng chính:** (Ai là người nhắn tin? Người bệnh trực tiếp hay người thân hỏi hộ? Độ tuổi, giới tính phổ biến).
2. **Nhu cầu và Động lực chính:** (Họ đang gặp vấn đề gì về sức khỏe? Họ tìm kiếm dịch vụ khám/tầm soát nào? Mong muốn lớn nhất của họ là gì?).
3. **Rào cản/Mối quan ngại lớn nhất:** (Điều gì khiến họ do dự, chưa đặt lịch ngay? Ví dụ: Giá cả, khoảng cách địa lý, lo sợ về quy trình, chưa hiểu rõ công nghệ MRI, cần hỏi ý kiến người thân...).
4. **Hành vi hỏi đáp:** (Họ thường đặt câu hỏi vào thời điểm nào? Thích nhận tư vấn chi tiết hay báo giá nhanh?).

Hãy trình bày báo cáo rõ ràng kèm các trích dẫn ngắn từ tin nhắn thực tế để minh họa.
```

---

## Prompt 2: Phát Hiện Các Vấn Đề Hiện Tại & Điểm Nghẽn (Pain Points & Bottlenecks)

**Mục tiêu:** Nhận diện những thiếu sót trong quy trình tư vấn hiện tại và các điểm làm giảm trải nghiệm khách hàng dẫn đến mất cơ hội (drop-off).

```markdown
Bạn là một chuyên gia Quản lý Chất lượng dịch vụ khách hàng (Customer Service Quality Assurance).
Dựa trên dữ liệu hội thoại JSON được cung cấp dưới đây:

[DÁN DỮ LIỆU JSON CHAT VÀO ĐÂY]

Hãy phân tích và chỉ ra các "điểm nghẽn" (bottlenecks) và lỗi trong kịch bản/quy trình tư vấn hiện tại của nhân viên (sale/tư vấn viên):
1. **Tốc độ phản hồi:** Nhân viên trả lời có kịp thời không? Có khoảng trống thời gian dài nào khiến khách hàng mất kiên nhẫn không?
2. **Chất lượng nội dung tư vấn:** 
   - Nhân viên có lắng nghe đúng nhu cầu hay chỉ trả lời rập khuôn theo mẫu?
   - Cách giải thích về giá cả, dịch vụ (như chụp cộng hưởng từ MRI, gói khám đột quỵ) đã dễ hiểu đối với người dân bình thường chưa?
   - Có cung cấp đầy đủ thông tin hay để khách hàng phải hỏi đi hỏi lại?
3. **Kỹ năng xử lý từ chối (Objection Handling):** Khi khách hàng chê đắt hoặc hẹn "hỏi lại người thân", nhân viên đã phản ứng như thế nào? Có thuyết phục được họ không?
4. **Tỷ lệ chốt hẹn thất bại:** Chỉ ra các cuộc hội thoại cụ thể mà khách hàng đã rất quan tâm nhưng kết thúc không đặt lịch. Lý do cốt lõi là gì?

Đề xuất cụ thể hành động cần khắc phục ngay lập tức cho đội ngũ trực page.
```

---

## Prompt 3: Tối Ưu Kịch Bản Chat (Chat Script Optimization)

**Mục tiêu:** Xây dựng lại các mẫu câu trả lời, cấu trúc tư vấn để nâng cao tỷ lệ chuyển đổi (conversion rate) từ nhắn tin sang đặt lịch khám thực tế.

```markdown
Bạn là một Chuyên gia Viết kịch bản Bán hàng (Sales Script Designer).
Dựa trên các vấn đề đã phân tích từ dữ liệu chat thực tế dưới đây:

[DÁN DỮ LIỆU JSON CHAT VÀO ĐÂY]

Hãy xây dựng lại **Kịch Bản Tư Vấn Tối Ưu** cho Vietlife Clinic để nâng cao tỷ lệ đặt lịch khám. Kịch bản cần tối ưu hóa cho các tình huống sau:

1. **Lời chào & Khai thác nhu cầu ban đầu:** Làm sao để khách hàng cởi mở chia sẻ triệu chứng sức khỏe của họ thay vì chỉ hỏi "Giá bao nhiêu?".
2. **Kịch bản báo giá thông minh:** Tránh việc báo giá cục lốc làm khách hàng giật mình (đặc biệt với gói khám giá trị cao tầm soát đột quỵ/u não). Cách lồng ghép giá trị của công nghệ MRI độc quyền trước khi đưa ra mức giá.
3. **Xử lý từ chối khi khách hàng chê đắt:** Đưa ra 3 mẫu câu ứng xử khéo léo để điều hướng sự chú ý của khách hàng từ "giá cả" sang "chất lượng chẩn đoán sớm và bảo vệ tính mạng".
4. **Xử lý tình huống "Để mình hỏi lại người thân":** Đưa ra mẫu câu kéo dài cuộc hội thoại hoặc xin số điện thoại để hỗ trợ tư vấn trực tiếp cho người thân.
5. **Kêu gọi hành động chốt hẹn (Call to Action - CTA):** Cách chốt lịch khám tự nhiên và tạo cảm giác khan hiếm/ưu đãi giới hạn.

Cung cấp kịch bản dưới dạng bảng So sánh: "Kịch bản cũ (Không hiệu quả) VS Kịch bản mới (Tối ưu)" kèm theo lý do thay đổi.
```

---

## Prompt 4: Tối Ưu Chiến Dịch Quảng Cáo (Facebook Ads Optimization)

**Mục tiêu:** Sử dụng ngôn ngữ và vấn đề thực tế của khách hàng trong chat để viết lại Ad Copy (nội dung quảng cáo) và điều chỉnh Target (đối tượng mục tiêu).

```markdown
Bạn là một Performance Marketing Director chuyên chạy quảng cáo Facebook Ads ngành Y Tế / Dược Phẩm.
Dựa trên những thắc mắc, lo lắng và nhu cầu thực tế của khách hàng qua dữ liệu chat JSON:

[DÁN DỮ LIỆU JSON CHAT VÀO ĐÂY]

Hãy đề xuất chiến lược tối ưu quảng cáo Facebook Ads cho phòng khám:
1. **Ý tưởng nội dung quảng cáo mới (Ad Copy & Creative Concepts):**
   - Viết 3 mẫu tiêu đề (Hooks) quảng cáo đánh trúng tâm lý lo lắng thực tế nhất của khách hàng (Ví dụ: Hay đau đầu mất ngủ lo sợ đột quỵ...).
   - Đề xuất hình ảnh/video minh họa tương ứng (Ví dụ: Video quy trình chụp MRI không tiếng ồn, êm ái cho người sợ lồng kín).
2. **Tối ưu hóa thông điệp quảng cáo:** 
   - Những từ khóa, thuật ngữ nào khách hàng hay nhắc đến trong chat mà chúng ta nên đưa vào bài viết quảng cáo? (Ví dụ: "MRI không đau", "bác sĩ viện 108", "trọn gói không phát sinh"...).
   - Những thông tin gây hiểu lầm nào cần được đính chính ngay từ bài viết quảng cáo để giảm thiểu lượng inbox rác (non-qualified leads)?
3. **Gợi ý Target đối tượng quảng cáo:**
   - Dựa trên chân dung khách hàng thực tế (ai là người quyết định đi khám, ai là người trả tiền), hãy đề xuất cách cài đặt Target trên Facebook Ads Manager (Độ tuổi, giới tính, sở thích, hành vi liên quan).

Hãy phân tích và viết báo cáo dưới góc nhìn thực chiến, có thể áp dụng chạy thử nghiệm ngay.
```
