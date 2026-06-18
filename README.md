# Vietlife Data Pipelines & Reports

Hệ thống thu thập, xử lý và lưu trữ tập trung dữ liệu Marketing & CRM cho **Vietlife** vào **Google BigQuery**, từ đó tạo các View làm nguồn cấp dữ liệu cho báo cáo **Looker Studio Dashboard**.

---

## 🏗️ Kiến Trúc Hệ Thống

```
Facebook Ads API ──┐
                   ├──► Cloud Run (Flask) ──► BigQuery ──► Looker Studio
Google Sheets CRM ─┘    (7:00 & 7:30)
```

**Cloud Run Service:** `https://fb-pipeline-751502323356.asia-southeast1.run.app`

---

## 👥 Cộng Tác 2 Người

### Quy trình Git

```
main ──────────────────────► Production (Cloud Run tự động deploy)
  │
  └─► develop ──────────────► Staging / Tích hợp chung
          │
          ├─► feature/ten-task   (mỗi tính năng mới)
          └─► fix/mo-ta-bug      (sửa bug)
```

**Quy tắc bắt buộc:**
- ❌ Không bao giờ push trực tiếp lên `main`
- ✅ Mọi thay đổi phải qua Pull Request → cần 1 người review
- ✅ CI phải pass trước khi merge

### Workflow hàng ngày

```bash
# Bắt đầu task mới
git checkout develop && git pull origin develop
git checkout -b feature/ten-task

# Làm xong → commit → push → tạo PR
git add -p
git commit -m "feat: mô tả rõ ràng"
git push origin feature/ten-task
# → Vào GitHub tạo Pull Request
```

### Commit Convention

| Prefix | Khi nào |
|--------|---------|
| `feat:` | Tính năng mới |
| `fix:` | Sửa bug |
| `sql:` | Thay đổi SQL view/query |
| `config:` | Thay đổi cấu hình |
| `docs:` | Cập nhật tài liệu |
| `chore:` | Maintenance |

---

## 🚀 Setup Máy Mới

Xem hướng dẫn chi tiết tại **[docs/ONBOARDING.md](docs/ONBOARDING.md)**

Tóm tắt nhanh:
```bash
git clone https://github.com/tuda0212/vietlife.git && cd vietlife
python3 -m venv .venv && source .venv/bin/activate
pip install -r files/requirements.txt
cp .env.example .env   # → Điền token thật vào .env
```

---

## 📂 Cấu Trúc Thư Mục

```
├── files/                       # Mã nguồn chính — chạy trên Cloud Run
│   ├── main.py                  # Flask entrypoint
│   ├── pipeline.py              # Pipeline Facebook Ads → BigQuery
│   ├── crm_pipeline.py          # Pipeline Google Sheets CRM → BigQuery
│   ├── fb_api.py                # Facebook Ads API client
│   ├── sheets_reader.py         # Google Sheets API reader
│   ├── transform.py             # Chuẩn hóa dữ liệu
│   ├── bq_loader.py             # Load lên BigQuery
│   ├── config.py                # Cấu hình Ad Accounts & chuyên khoa
│   ├── config_crm.py            # Cấu hình Google Sheets CRM
│   └── requirements.txt
│
├── scripts/                     # Công cụ phát triển cục bộ
│   ├── git_backup.sh            # Auto-backup an toàn (không push lên main)
│   ├── deploy_view.py           # Deploy SQL views lên BigQuery
│   ├── verify_view.py           # Xác thực dữ liệu trong view
│   ├── sync_crm_all.py          # Sync CRM toàn bộ Y tế
│   ├── sync_fb_ads.py           # Sync Facebook Ads (đọc token từ .env)
│   └── analyze_invalid_rows.py  # Phân tích dòng lỗi trên Sheets
│
├── sql/                         # SQL Views BigQuery
│   ├── v_report_duoc.sql        # Báo cáo Dược Nano
│   ├── v_report_duoc_detail.sql # Chi tiết Dược Nano
│   ├── v_report_y_te.sql        # Báo cáo Y tế
│   └── v_report_y_te_detail.sql # Chi tiết Y tế
│
├── docs/                        # Tài liệu
│   └── ONBOARDING.md            # Hướng dẫn setup máy mới
│
├── Google-Trends-Tracker/       # Apps Script Trends & TikTok
│
├── .github/
│   ├── workflows/
│   │   ├── ci.yml               # CI: Lint + Security + Syntax check
│   │   └── deploy.yml           # CD: Auto-deploy Cloud Run khi merge main
│   └── PULL_REQUEST_TEMPLATE.md
│
├── .env.example                 # Template biến môi trường (không có giá trị thật)
└── .gitignore                   # Bảo vệ .env, credentials, .venv
```

---

## ⚙️ Vận Hành

### Deploy SQL Views lên BigQuery
```bash
python3 scripts/deploy_view.py
```

### Xác thực dữ liệu View
```bash
python3 scripts/verify_view.py
```

### Chạy CRM Pipeline cục bộ
```bash
python3 scripts/run_crm_local.py
```

### Phân tích dòng lỗi CRM
```bash
python3 scripts/analyze_invalid_rows.py
```

---

## 🔐 Bảo Mật

- **Không bao giờ** hardcode token/key trong code
- Secrets được lưu trong file `.env` (liệt kê trong `.gitignore`)
- Xem `.env.example` để biết cách tạo file `.env`
- Trên Cloud Run: dùng biến môi trường trong cấu hình service

---

## 🤖 CI/CD Tự Động

| Trigger | Action |
|---------|--------|
| Tạo Pull Request vào `main`/`develop` | CI chạy: lint + security scan + syntax check |
| Merge vào `main` (có thay đổi `files/`) | CD chạy: tự động deploy lên Cloud Run |

**Cloud Scheduler:** Pipeline tự động chạy hàng ngày lúc 7:00 và 7:30 sáng.

**API Endpoints:**
- `GET /health` — Health check
- `POST /run` — Chạy Facebook Ads pipeline
- `POST /run-crm` — Chạy CRM pipeline
- `POST /run-all` — Chạy cả 2 pipeline
