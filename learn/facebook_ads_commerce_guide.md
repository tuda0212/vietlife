# Hướng Dẫn Tích Hợp Facebook Ads & Commerce Platform

Tài liệu này hướng dẫn chi tiết cách tích hợp, cấu hình và sử dụng **Facebook Marketing API** cùng **Commerce Platform API** (Catalog, Shops) để tự động hóa chiến dịch quảng cáo, đồng bộ danh mục sản phẩm, đo lường chuyển đổi và tối ưu hóa hiệu quả tiếp thị.

---

## 1. Tổng Quan Hệ Thống (Platform Overview)

Meta cung cấp hai hệ sinh thái API chính phục vụ cho các nhà phát triển xây dựng ứng dụng quảng cáo và thương mại điện tử:

1. **Meta Marketing API:** Giúp quản lý tài khoản quảng cáo, tạo chiến dịch (`Campaign`), nhóm quảng cáo (`Ad Set`), mẫu thiết kế quảng cáo (`Ad Creative`), quảng cáo thực tế (`Ad`), và kéo báo cáo hiệu suất tự động qua **Ads Insights API**.
2. **Meta Commerce Platform (Commerce Manager):** Giúp quản lý danh mục sản phẩm (`Product Catalog`), đồng bộ kho hàng thông qua **Catalog API** hoặc **Product Feeds**, kết nối với Facebook/Instagram Shop và triển khai các chiến dịch **Advantage+ Catalog Ads** (Quảng cáo động dựa trên catalog).

```
   [Hệ Thống Doanh Nghiệp]
      │
      ├─(Marketing API)─────► [Tạo Campaign/Ad Set/Ad/Insights] ─────► Facebook Ads
      │
      ├─(Catalog API)───────► [Đồng Bộ Product Feeds/Catalog] ──────► Meta Commerce Manager
      │
      └─(Conversions API)───► [Gửi Sự Kiện Server-side Events] ────► Meta Pixel (Signals)
```

---

## 2. Xác Thực & Phân Quyền (Authentication & Permissions)

Để gọi các API của Meta, bạn cần sử dụng **Access Token** hợp lệ. Đối với các ứng dụng tự động chạy trên máy chủ (background scripts/ETL pipelines), khuyến nghị sử dụng **System User Access Token** thay vì Token cá nhân để tránh hết hạn.

### 2.1. Thiết Lập System User (Người Dùng Hệ Thống)
1. Truy cập **Trình quản lý doanh nghiệp (Business Manager)** -> **Cài đặt doanh nghiệp**.
2. Vào mục **Người dùng hệ thống (System Users)** -> Nhấp **Thêm** để tạo một System User mới (loại Quản trị viên).
3. Chỉ định tài sản (Assign Assets): Gán quyền quản lý cho System User này đối với **Trang (Pages)**, **Tài khoản quảng cáo (Ad Accounts)**, và **Danh mục sản phẩm (Catalogs)** cần tích hợp.
4. Nhấp **Tạo mã (Generate Token)**, chọn ứng dụng của bạn và đánh dấu tích chọn các quyền cần thiết.

### 2.2. Các Quyền API Quan Trọng (Scopes)
* `ads_management`: Quyền tạo, chỉnh sửa, xóa chiến dịch quảng cáo và các thành phần liên quan.
* `ads_read`: Quyền đọc dữ liệu cấu hình quảng cáo và dữ liệu hiệu suất (Insights).
* `catalog_management`: Quyền quản lý Catalog, thêm/chỉnh sửa sản phẩm và nguồn cấp dữ liệu sản phẩm.
* `pages_read_engagement` & `pages_manage_ads`: Quyền quản lý nội dung bài viết và chạy quảng cáo đại diện cho Trang (Pages).

---

## 3. Quản Lý Chiến Dịch Quảng Cáo (Marketing API)

Cấu trúc quảng cáo Meta chuẩn gồm 4 thực thể liên kết tuần tự:

```
  Ad Account (Tài khoản)
     └── Campaign (Chiến dịch)
            └── Ad Set (Nhóm quảng cáo)
                   └── Ad (Quảng cáo thực tế) ◄── Linked ── Ad Creative (Mẫu quảng cáo)
```

### 3.1. Bước 1: Tạo Campaign (Chiến dịch)
Xác định mục tiêu chính của chiến dịch (ví dụ: `OUTCOME_LEADS` cho chiến dịch thu thập khách hàng tiềm năng, `OUTCOME_TRAFFIC` cho chiến dịch tăng lưu lượng truy cập).

* **Method:** `POST`
* **URL:** `https://graph.facebook.com/v20.0/act_<AD_ACCOUNT_ID>/campaigns`
* **Body (JSON):**
  ```json
  {
    "name": "VL_Camp_TuVanSucKhoe_2026",
    "objective": "OUTCOME_LEADS",
    "status": "PAUSED",
    "special_ad_categories": "[]"
  }
  ```
* **Response:**
  ```json
  {
    "id": "120205849301234567"
  }
  ```

### 3.2. Bước 2: Tạo Ad Set (Nhóm quảng cáo)
Thiết lập ngân sách (`daily_budget` hoặc `lifetime_budget`), lịch chạy, vị trí hiển thị (Placement), đối tượng mục tiêu (`targeting`) và mục tiêu tối ưu hóa.

* **Method:** `POST`
* **URL:** `https://graph.facebook.com/v20.0/act_<AD_ACCOUNT_ID>/adsets`
* **Body (JSON):**
  ```json
  {
    "name": "VL_AdSet_Target_Hanoi_HCM",
    "campaign_id": "120205849301234567",
    "daily_budget": "100000",
    "billing_event": "IMPRESSIONS",
    "optimization_goal": "LEADS",
    "bid_strategy": "LOWEST_COST_WITHOUT_CAP",
    "targeting": "{\"geo_locations\": {\"countries\": [\"VN\"], \"cities\": [{\"key\": \"3840\", \"radius\": 20, \"distance_unit\": \"kilometer\"}]}}",
    "status": "PAUSED"
  }
  ```
  > [!IMPORTANT]
  > Ngân sách `daily_budget` được tính theo đơn vị tiền tệ nhỏ nhất của tài khoản. Đối với VND, giá trị `100000` là 100,000 VNĐ. Nhưng đối với tài khoản USD, `100000` tương đương 1,000 USD (do đơn vị nhỏ nhất là cents).

### 3.3. Bước 3: Tạo Ad Creative (Mẫu thiết kế quảng cáo)
Định nghĩa nội dung quảng cáo sẽ hiển thị bao gồm: hình ảnh, video, tiêu đề, mô tả và nút kêu gọi hành động (CTA). Bạn có thể tạo mẫu quảng cáo mới hoặc sử dụng bài viết có sẵn trên Trang (`object_story_id`).

#### Cách A: Sử dụng bài viết có sẵn trên Fanpage
* **Method:** `POST`
* **URL:** `https://graph.facebook.com/v20.0/act_<AD_ACCOUNT_ID>/adcreatives`
* **Body (JSON):**
  ```json
  {
    "name": "VL_Creative_PagePost_123",
    "object_story_id": "100063548901234_987654321012345"
  }
  ```

#### Cách B: Tạo mẫu quảng cáo mới với liên kết hình ảnh
* **Method:** `POST`
* **URL:** `https://graph.facebook.com/v20.0/act_<AD_ACCOUNT_ID>/adcreatives`
* **Body (JSON):**
  ```json
  {
    "name": "VL_Creative_TuVan_NewLink",
    "object_story_spec": {
      "page_id": "100063548901234",
      "link_data": {
        "image_hash": "e8a9462fcb43de129c54e015d836d83a",
        "link": "https://vietlife.edu.vn",
        "message": "Đăng ký tư vấn sức khỏe chủ động ngay hôm nay!",
        "call_to_action": {
          "type": "LEARN_MORE",
          "value": {
            "link": "https://vietlife.edu.vn"
          }
        }
      }
    }
  }
  ```

### 3.4. Bước 4: Tạo Ad (Quảng cáo thực tế)
Liên kết Nhóm quảng cáo (`adset_id`) với Mẫu thiết kế quảng cáo (`creative_id`) để hoàn thành cấu hình chiến dịch.

* **Method:** `POST`
* **URL:** `https://graph.facebook.com/v20.0/act_<AD_ACCOUNT_ID>/ads`
* **Body (JSON):**
  ```json
  {
    "name": "VL_Ad_TuVan_Mau1",
    "adset_id": "120205849301234568",
    "creative": "{\"creative_id\": \"120205849301234569\"}",
    "status": "PAUSED"
  }
  ```

---

## 4. Ads Insights API (Lấy Báo Cáo Hiệu Suất)

Để lấy dữ liệu báo cáo hiệu suất (lượt hiển thị, chi phí, lượt click, tin nhắn...) từ chiến dịch quảng cáo, hãy sử dụng Ads Insights API.

* **Method:** `GET`
* **URL:** `https://graph.facebook.com/v20.0/act_<AD_ACCOUNT_ID>/insights`
* **Query Parameters:**
  * `level`: Cấp độ dữ liệu muốn lấy (`campaign`, `adset`, `ad`, `account`).
  * `fields`: Các chỉ số cần lấy, ví dụ: `campaign_name`, `impressions`, `clicks`, `spend`, `actions`.
  * `date_preset`: Khoảng thời gian (ví dụ: `today`, `yesterday`, `this_month`).
* **Response Example:**
  ```json
  {
    "data": [
      {
        "impressions": "15420",
        "clicks": "452",
        "spend": "250000",
        "actions": [
          { "action_type": "link_click", "value": "310" },
          { "action_type": "onsite_conversion.messaging_first_reply", "value": "42" }
        ],
        "date_start": "2026-06-20",
        "date_stop": "2026-06-20"
      }
    ]
  }
  ```

---

## 5. Commerce Manager & Catalog API

Commerce Manager giúp doanh nghiệp quản lý thông tin sản phẩm và đồng bộ lên cửa hàng Facebook/Instagram Shop.

### 5.1. Cấu Trúc Catalog
* **Product Catalog:** Nơi chứa toàn bộ kho sản phẩm của doanh nghiệp.
* **Product Feed:** File chứa dữ liệu danh sách sản phẩm (định dạng CSV, XML, TSV) được đồng bộ tự động theo chu kỳ (Scheduled Feed).
* **Product Set:** Các bộ sưu tập sản phẩm nhỏ hơn được lọc từ Catalog chính dựa trên danh mục, giá tiền, thương hiệu để chạy chiến dịch quảng cáo sản phẩm động.

### 5.2. Đồng Bộ Sản Phẩm Qua Feed API
Thay vì tải lên thủ công, bạn có thể thiết lập nguồn cấp dữ liệu sản phẩm tự động cập nhật mỗi ngày từ website của mình.

1. **Chuẩn bị Product Feed file (XML/CSV):** File cần có các thuộc tính bắt buộc của Meta như: `id`, `title`, `description`, `availability` (in stock), `condition` (new), `price`, `link`, `image_link`, `brand`.
2. **Đăng ký Product Feed qua API:**
   * **Method:** `POST`
   * **URL:** `https://graph.facebook.com/v20.0/<PRODUCT_CATALOG_ID>/product_feeds`
   * **Body (JSON):**
     ```json
     {
       "name": "VL_Main_Product_Feed",
       "schedule": {
         "interval": "DAILY",
         "url": "https://vietlife.edu.vn/feeds/products.xml",
         "hour": 2
       }
     }
     ```

### 5.3. Trạng Thái Đồng Bộ (Diagnostics & Batch Items)
Bạn có thể cập nhật nhanh danh mục sản phẩm (hoặc thay đổi trạng thái tồn kho, giá bán tức thời) thông qua **Batch Items API**:

* **Method:** `POST`
* **URL:** `https://graph.facebook.com/v20.0/<PRODUCT_CATALOG_ID>/items_batch`
* **Body (JSON):**
  ```json
  {
    "requests": [
      {
        "method": "UPDATE",
        "data": {
          "id": "SP_NANO_001",
          "price": "450000 VND",
          "availability": "in stock"
        }
      }
    ]
  }
  ```

---

## 6. Conversions API (Đo Lường Chuyển Đổi Từ Máy Chủ)

Khi cookie trình duyệt bị hạn chế (do iOS 14+ hoặc các trình chặn quảng cáo), việc đo lường bằng Meta Pixel ở Client sẽ bị sai lệch. **Conversions API (CAPI)** cho phép bạn gửi trực tiếp các sự kiện chuyển đổi (khách đăng ký khám thành công, chốt đơn) từ server của bạn tới server Meta.

### 6.1. Endpoint Gửi Sự Kiện
* **Method:** `POST`
* **URL:** `https://graph.facebook.com/v20.0/<PIXEL_ID>/events`
* **Body (JSON):**
  ```json
  {
    "data": [
      {
        "event_name": "Lead",
        "event_time": 1782186970,
        "event_source_url": "https://vietlife.edu.vn/tu-van-thanh-cong",
        "action_source": "website",
        "user_data": {
          "em": "f660ab912ec121d1b1e928a0bb4bc61b15f5ad44d5efdc4e1c92a25e99b8e44a",
          "ph": "45a9ea64fc4b3de129c54e015d836d83a15f5ad44d5efdc4e1c92a25e99b8e44a"
        },
        "custom_data": {
          "value": 150000,
          "currency": "VND"
        }
      }
    ]
  }
  ```
  > [!TIP]
  > Dữ liệu người dùng nhạy cảm như Email (`em`), Số điện thoại (`ph`) **phải được mã hóa dưới dạng SHA-256** trước khi gửi lên Meta API để bảo mật thông tin cá nhân.

---

## 7. Các Lỗi Thường Gặp & Cách Xử Lý

1. **Lỗi `Invalid OAuth Access Token` (Code 190 / Subcode 490):**
   * *Nguyên nhân:* Access Token hết hạn, bị thu hồi hoặc đổi mật khẩu tài khoản quản trị.
   * *Giải pháp:* Đăng nhập Trình quản lý doanh nghiệp và tạo lại System User Token mới.

2. **Lỗi `Invalid Targeting Spec` (Code 100):**
   * *Nguyên nhân:* Cú pháp JSON của trường `targeting` không hợp lệ hoặc sai cấu trúc địa lý (ví dụ: dùng sai ID của thành phố).
   * *Giải pháp:* Sử dụng `targeting_search` API để tìm đúng mã `key` của địa phương trước khi đưa vào cấu trúc `targeting`.

3. **Lỗi `Budget Too Low` (Code 100 / Subcode 1885016):**
   * *Nguyên nhân:* Giá trị ngân sách thiết lập nhỏ hơn ngân sách tối thiểu cho phép (khoảng 1 USD/ngày).
   * *Giải pháp:* Tăng ngân sách hoặc kiểm tra xem tài khoản đang cấu hình tiền tệ là VND hay USD để truyền giá trị đúng đơn vị.
