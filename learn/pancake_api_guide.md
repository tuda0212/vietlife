# Hướng Dẫn Tích Hợp Pancake Chat API

Tài liệu này hướng dẫn cách sử dụng **Pancake Chat API** (thông qua nền tảng [pages.fm](https://pages.fm)) để kết nối, trích xuất dữ liệu cuộc trò chuyện và tin nhắn phục vụ cho quá trình phân tích.

---

## 1. Cơ Chế Xác Thực (Authentication)

Pancake Chat API sử dụng cơ chế xác thực qua Token được truyền trực tiếp dưới dạng **Query Parameter** trong URL (không dùng header `Authorization`).

Có hai loại Token chính:
1. **User Access Token (`access_token`):** Dùng cho các API cấp tài khoản (ví dụ: lấy danh sách các trang đang quản lý, tạo token cho từng trang).
2. **Page Access Token (`page_access_token`):** Dùng cho các API cấp trang (ví dụ: lấy hội thoại, tin nhắn, thông tin khách hàng). Token này không hết hạn trừ khi bạn chủ động thu hồi hoặc tạo mới.

### Cách lấy Token từ Giao Diện Pancake (pages.fm):
- **User Access Token:** Đăng nhập vào [pages.fm](https://pages.fm) -> Chọn **Cá nhân** (hoặc Avatar ở góc dưới bên trái) -> **Cấu hình cá nhân** -> Sao chép **API Access Token**.
- **Page Access Token:** Vào trang quản trị của fanpage cụ thể trên Pancake -> **Cài đặt** -> **Công cụ** -> Tạo và sao chép **Page Access Token**.

---

## 2. Các API Endpoints Quan Trọng

### 2.1. Lấy Danh Sách Trang (Pages)
Dùng để lấy danh sách các trang (Facebook Page, Zalo, Shopee...) mà tài khoản đang quản lý, từ đó lấy ra `page_id`.

* **Method:** `GET`
* **URL:** `https://pages.fm/api/v1/pages`
* **Query Parameters:**
  * `access_token` (Bắt buộc): User Access Token.
* **Response Example:**
  ```json
  {
    "success": true,
    "pages": [
      {
        "id": "100063548901234",
        "name": "Vietlife Clinic",
        "category": "Medical & Health",
        "provider": "facebook"
      }
    ]
  }
  ```

---

### 2.2. Lấy Danh Sách Cuộc Trò Chuyện (Conversations)
Dùng để quét và lấy danh sách các cuộc trò chuyện của một trang.

* **Method:** `GET`
* **URL:** `https://pages.fm/api/public_api/v1/pages/{page_id}/conversations`
* **Query Parameters:**
  * `page_access_token` (Bắt buộc): Page Access Token của trang đó.
  * `limit` (Tùy chọn): Số lượng cuộc trò chuyện trả về trên mỗi trang (mặc định: `20`, tối đa: `100`).
  * `page` (Tùy chọn): Số trang để phân trang (mặc định: `1`).
  * `type` (Tùy chọn): Lọc theo loại hội thoại. Nhận giá trị: `inbox` (tin nhắn), `comment` (bình luận), hoặc để trống để lấy cả hai.
  * `since` / `until` (Tùy chọn): Lọc theo thời gian cập nhật cuộc hội thoại (định dạng **Unix Timestamp**).
  * `tag` (Tùy chọn): Lọc theo ID của thẻ phân loại (tag).
* **Response Example:**
  ```json
  {
    "success": true,
    "conversations": [
      {
        "id": "t.100063548901234.9876543210",
        "page_id": "100063548901234",
        "type": "inbox",
        "updated_at": "2026-06-20T05:00:00Z",
        "customer": {
          "id": "9876543210",
          "name": "Nguyễn Văn A",
          "avatar": "https://example.com/avatar.jpg"
        },
        "tags": [
          {
            "id": "tag_001",
            "name": "Khách Quan Tâm",
            "color": "#FF5733"
          }
        ],
        "last_message": {
          "message": "Tôi muốn tư vấn về gói khám tổng quát",
          "created_at": "2026-06-20T05:00:00Z",
          "from": {
            "id": "9876543210",
            "name": "Nguyễn Văn A"
          }
        }
      }
    ]
  }
  ```

---

### 2.3. Lấy Danh Sách Tin Nhắn Trong Cuộc Trò Chuyện (Messages)
Dùng để lấy toàn bộ lịch sử tin nhắn của một cuộc hội thoại cụ thể để làm đầu vào cho AI phân tích.

* **Method:** `GET`
* **URL:** `https://pages.fm/api/public_api/v1/pages/{page_id}/conversations/{conversation_id}/messages`
* **Query Parameters:**
  * `page_access_token` (Bắt buộc): Page Access Token.
  * `limit` (Tùy chọn): Số lượng tin nhắn trả về (mặc định: `20`, tối đa: `100`).
  * `page` (Tùy chọn): Số trang phân trang.
* **Response Example:**
  ```json
  {
    "success": true,
    "messages": [
      {
        "id": "m_123456",
        "message": "Chào bạn, Vietlife có thể giúp gì cho bạn?",
        "created_at": "2026-06-20T04:58:00Z",
        "from": {
          "id": "100063548901234",
          "name": "Vietlife Clinic (Page)"
        }
      },
      {
        "id": "m_123457",
        "message": "Tôi muốn tư vấn về gói khám tổng quát",
        "created_at": "2026-06-20T05:00:00Z",
        "from": {
          "id": "9876543210",
          "name": "Nguyễn Văn A"
        }
      }
    ]
  }
  ```

---

### 2.4. Trả Lời Tin Nhắn (Reply Message)
Dùng trong trường hợp muốn tích hợp chatbot tự động tối ưu kịch bản trả lời khách hàng.

* **Method:** `POST`
* **URL:** `https://pages.fm/api/public_api/v1/pages/{page_id}/conversations/{conversation_id}/messages`
* **Query Parameters:**
  * `page_access_token` (Bắt buộc): Page Access Token.
* **Headers:**
  * `Content-Type: application/json`
* **Body (JSON):**
  ```json
  {
    "action": "reply_inbox",
    "message": "Cảm ơn anh A, gói khám bên em hiện đang có ưu đãi..."
  }
  ```
* **Response Example:**
  ```json
  {
    "success": true,
    "id": "m_123458"
  }
  ```

---

## 3. Nhận Dữ Liệu Thời Gian Thực (Webhook)

Nếu muốn hệ thống phân tích tin nhắn chạy tự động ngay khi khách hàng nhắn tin (real-time), bạn có thể cấu hình Webhook trong Pancake.

1. Vào Pancake -> **Cài đặt** -> **Webhook**.
2. Nhập URL máy chủ của bạn (ví dụ: `https://your-domain.com/webhook/pancake`).
3. Chọn các sự kiện muốn nhận tin:
   * `new_message`: Tin nhắn mới.
   * `new_comment`: Bình luận mới.
4. Khi có tin nhắn mới, Pancake sẽ gửi một request `POST` dạng JSON chứa thông tin tin nhắn đến URL của bạn.

---

## 4. Xử Lý Giới Hạn Tần Suất Gọi API (Rate Limits)

Pancake API có giới hạn số lượng request trong một khoảng thời gian nhất định để bảo vệ hệ thống. 
- **Khuyến nghị:** Khi thực hiện đồng bộ (sync) dữ liệu cũ với số lượng lớn, hãy thiết lập thời gian nghỉ (delay/sleep) từ **0.5s đến 1s** giữa mỗi request.
- **Xử lý lỗi:** Nếu nhận được HTTP Status Code `429 Too Many Requests`, hãy tạm dừng gửi yêu cầu trong ít nhất 1 phút trước khi thử lại.
