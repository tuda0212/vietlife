# Vietlife Data Pipelines & Reports

Dự án này là hệ thống thu thập, xử lý và lưu trữ tập trung dữ liệu Marketing & CRM cho **Vietlife** vào **Google BigQuery**, từ đó tạo các View làm nguồn cấp dữ liệu cho báo cáo **Looker Studio Dashboard**.

---

## 📂 Cấu trúc thư mục dự án

```text
├── files/                       # Thư mục chứa mã nguồn chính của pipelines
│   ├── main.py                  # Entrypoint Flask app (chạy trên Cloud Run)
│   ├── pipeline.py              # Bộ điều phối Pipeline 1: Facebook Ads -> BigQuery
│   ├── crm_pipeline.py          # Bộ điều phối Pipeline 2: Google Sheets CRM -> BigQuery
│   ├── fb_api.py                # Giao tiếp Facebook Ads API (song song)
│   ├── sheets_reader.py         # Trình đọc Google Sheets API v4
│   ├── transform.py             # Chuẩn hóa dữ liệu Ads & CRM
│   ├── bq_loader.py             # Load dữ liệu batch (JSON) lên BigQuery
│   ├── config.py                # Cấu hình Ad Accounts & chuyên khoa
│   └── config_crm.py            # Cấu hình Google Sheets CRM bác sĩ & Dược Nano
│
├── scripts/                     # Các công cụ kiểm tra và deploy cục bộ
│   ├── deploy_view.py           # Deploy hàng loạt cả 3 SQL views lên BigQuery
│   ├── verify_view.py           # Xác thực và lấy mẫu dữ liệu từ các view
│   ├── run_crm_local.py         # Chạy thử pipeline CRM cục bộ
│   ├── analyze_invalid_rows.py  # Kiểm tra định dạng ngày/sđt lỗi trên Google Sheets
│   ├── inspect_bq.py            # Kiểm tra schema hiện tại trong BigQuery
│   ├── inspect_bq_view.py       # Xuất định nghĩa view hiện tại từ BigQuery
│   ├── inspect_data.py          # Kiểm tra phân bổ dữ liệu thực tế trong các bảng
│   └── inspect_duoc_nano_headers.py # Kiểm tra headers của Google Sheet CRM Dược
│
├── Google-Trends-Tracker/       # Module tracking Google Trends & TikTok (Google Apps Script)
│   ├── Code.gs                  # Code Apps Script Google Trends
│   ├── TikTok-Tracker.gs        # Code Apps Script TikTok
│   └── HUONG-DAN-CAI-DAT.md     # Hướng dẫn setup trigger
│
├── v_report.sql                 # View SQL tổng hợp toàn bộ Ads + CRM
├── v_report_y_te.sql            # View SQL tổng hợp riêng cho mảng Y tế (specialty_code: CS, TK, CXK, TH)
└── v_report_duoc.sql            # View SQL tổng hợp riêng cho mảng Dược Nano (VT, BA - FULL OUTER JOIN)
```

---

## 🛠️ Hướng dẫn vận hành

### 1. Deploy các View SQL lên BigQuery
Khi có bất kỳ thay đổi nào trong các file định nghĩa view `.sql` ở thư mục gốc, hãy chạy script sau để deploy lại lên Google BigQuery:
```bash
python3 scripts/deploy_view.py
```

### 2. Xác thực và kiểm tra dữ liệu trong View
Để xem tổng số dòng và một vài dòng dữ liệu mẫu của từng view trên BigQuery:
```bash
python3 scripts/verify_view.py
```

### 3. Đồng bộ dữ liệu cục bộ (Local Sync)
Để chạy thử pipeline CRM cục bộ trên máy cá nhân:
```bash
python3 scripts/run_crm_local.py
```

### 4. Phân tích các dòng lỗi trên Google Sheets CRM
Nếu dữ liệu CRM từ Google Sheet không vào BigQuery, có thể do định dạng ngày hoặc ad_id không hợp lệ. Hãy chạy công cụ phân tích:
```bash
python3 scripts/analyze_invalid_rows.py
```

---

## ⚙️ Cấu hình pipelines trên Cloud Run
Pipelines được triển khai dưới dạng Flask App trên Cloud Run:
- **Service URL**: `https://fb-pipeline-751502323356.asia-southeast1.run.app`
- **Các API Endpoints**:
  - `GET /health`: Health check.
  - `POST /run`: Chạy pipeline Facebook Ads (hỗ trợ `{"start_date": "YYYY-MM-DD", "end_date": "YYYY-MM-DD"}`).
  - `POST /run-crm`: Chạy pipeline Google Sheets CRM (hỗ trợ `{"start_date": "YYYY-MM-DD", "end_date": "YYYY-MM-DD", "doctors": ["Định", "Tuyên"]}`).
  - `POST /run-all`: Chạy tuần tự cả 2 pipelines.

Các Pipeline này được tự động kích hoạt hàng ngày bởi **Cloud Scheduler** lúc **7:00** và **7:30** sáng.
