# 🏗️ Hệ Thống Cộng Tác — Project Vietlife (VL)
> **2 người · 2 máy · 1 repo GitHub · Đồng bộ hoàn hảo**

---

## 1. 🔍 Phân Tích Hiện Trạng

### Kiến trúc dữ liệu hiện tại
```
Facebook Ads API ──┐
                   ├──► Cloud Run (Flask)  ──► BigQuery ──► Looker Studio
Google Sheets CRM──┘       (7:00 & 7:30)
```

### Cấu trúc Repo
| Thư mục | Mục đích |
|---------|---------|
| `files/` | Mã nguồn chính – pipelines, Flask app, Docker |
| `scripts/` | Công cụ cục bộ – inspect, deploy, verify |
| `duoc/` | SQL cho mảng Dược Nano |
| `y_te/` | SQL cho mảng Y tế |
| `Google-Trends-Tracker/` | Apps Script – Google Trends + TikTok |

### Vấn đề nhận thấy ở git log
- Chỉ có 1 nhánh `main` — **không có nhánh feature/develop**
- Commit message không nhất quán: *"Auto-commit hourly"*, *"Manual commit as requested"*
- Không có **Pull Request workflow** → xung đột tiềm ẩn cao

---

## 2. ⚠️ Các Vấn Đề Rủi Ro Khi 2 Người Làm Việc

### 🔴 Rủi ro nghiêm trọng
| # | Vấn đề | Hệ quả |
|---|--------|--------|
| 1 | **Merge conflict** — 2 người cùng sửa `config_crm.py` hoặc SQL views | Code bị ghi đè, mất công việc |
| 2 | **Auto-commit hourly** ghi đè lên thay đổi chưa hoàn chỉnh của người kia | Deploy code lỗi lên Cloud Run |
| 3 | **Secret / credentials** bị commit vào repo | Lộ API key Facebook, Service Account GCP |
| 4 | **Không có code review** — push thẳng lên `main` | Bug production không được phát hiện |
| 5 | **`.venv/` có thể bị commit** | Repo phình to, conflict liên tục |

### 🟡 Rủi ro trung bình
| # | Vấn đề | Hệ quả |
|---|--------|--------|
| 6 | Không có `.gitignore` chuẩn | File rác, cache, credentials vào repo |
| 7 | Thiếu quy ước đặt tên branch | Khó quản lý công việc song song |
| 8 | Không có môi trường staging | Test thẳng trên production |
| 9 | Không rõ ai chịu trách nhiệm phần nào | Duplicated work hoặc bỏ sót |

---

## 3. 🏛️ Thiết Kế Hệ Thống Hoàn Chỉnh

### 3.1 Git Branching Strategy (Gitflow đơn giản hóa)

```
main ──────────────────────────────────────────► Production
  │
  └─► develop ────────────────────────────────► Staging / Testing
          │
          ├─► feature/ten-nguoi-dat-ten-tinh-nang  (mỗi tính năng)
          ├─► fix/mo-ta-bug
          └─► hotfix/loi-cap-bac (khi cần vá nhanh production)
```

**Quy tắc:**
- `main` → chỉ merge từ `develop` qua Pull Request, bắt buộc **1 người review**
- `develop` → branch tích hợp chung, tự động deploy lên Cloud Run staging
- `feature/*` → mỗi người làm 1 branch riêng, không bao giờ push thẳng lên `main`

---

### 3.2 Cấu Trúc Thư Mục Tối Ưu Cho 2 Người

```
VL/
├── .github/
│   ├── workflows/
│   │   ├── ci.yml              # Chạy lint + test tự động khi có PR
│   │   └── deploy.yml          # Auto-deploy lên Cloud Run khi merge vào main
│   └── PULL_REQUEST_TEMPLATE.md
│
├── files/                       # Pipeline code (production)
│   ├── main.py
│   ├── pipeline.py
│   ├── crm_pipeline.py
│   ├── fb_api.py
│   ├── sheets_reader.py
│   ├── transform.py
│   ├── bq_loader.py
│   ├── config.py               # KHÔNG chứa secret, chỉ chứa cấu hình
│   ├── config_crm.py
│   └── requirements.txt
│
├── sql/                         # Tập trung toàn bộ SQL ở đây
│   ├── views/
│   │   ├── v_report_duoc.sql
│   │   ├── v_report_duoc_detail.sql
│   │   ├── v_report_y_te.sql
│   │   └── v_report_y_te_detail.sql
│   └── queries/
│       ├── duoc/
│       └── y_te/
│
├── scripts/                     # Dev tools
│   └── (giữ nguyên)
│
├── docs/                        # Tài liệu dự án
│   ├── ARCHITECTURE.md
│   ├── ONBOARDING.md           # Hướng dẫn setup máy mới
│   └── RUNBOOK.md              # Quy trình vận hành
│
├── .env.example                 # Template biến môi trường (không có giá trị thật)
├── .gitignore                   # Đầy đủ
└── README.md
```

---

### 3.3 .gitignore Chuẩn

```gitignore
# Python
__pycache__/
*.py[cod]
.venv/
*.egg-info/
dist/
.pytest_cache/

# Environment & Secrets (QUAN TRỌNG NHẤT)
.env
*.json          # Service account keys
secrets/
credentials/

# macOS
.DS_Store
.AppleDouble

# IDE
.vscode/
.idea/
*.swp

# Dữ liệu cục bộ
*.csv
*.xlsx
files_local/
```

---

### 3.4 Quản Lý Secrets — Không Bao Giờ Commit Key

**Hiện tại (rủi ro):** Credentials có thể nằm trong `config.py` hoặc file `.json`

**Giải pháp:**
```
Mỗi máy               GitHub              Cloud Run
┌──────────┐          ┌──────┐           ┌──────────────┐
│ .env     │          │      │           │ Secret Mgr   │
│ key.json │ ──────X──│ Repo │  ────────►│ GCP          │
│ (local)  │          │      │           │ Env Variables│
└──────────┘          └──────┘           └──────────────┘
```

**Cách thực hiện:**
1. Tạo file `.env.example` (mẫu không có giá trị thật) → commit vào repo
2. Mỗi người tạo `.env` riêng trên máy → **không commit**
3. Trên Cloud Run → dùng **Google Secret Manager** hoặc biến môi trường
4. Thêm `*.json` và `.env` vào `.gitignore`

---

### 3.5 Tắt Auto-Commit Hourly Khi Làm Việc Chung

**Vấn đề:** Cron job auto-commit mỗi giờ có thể push code lỗi/dang dở lên `main`

**Giải pháp A — Branch bảo vệ:**
- Bật **Branch Protection** trên GitHub cho nhánh `main`
- Chặn push trực tiếp, bắt buộc qua PR

**Giải pháp B — Auto-commit chỉ trên nhánh riêng:**
```bash
# Sửa script auto-commit: push lên backup branch thay vì main
BRANCH="auto-backup-$(date +%Y%m%d)"
git checkout -b $BRANCH 2>/dev/null || git checkout $BRANCH
git add -A
git commit -m "Auto-backup: $(date '+%Y-%m-%d %H:%M')"
git push origin $BRANCH
git checkout main  # quay lại main để làm việc bình thường
```

---

### 3.6 GitHub Actions CI/CD Pipeline

**File: `.github/workflows/ci.yml`**
```yaml
name: CI — Lint & Test

on:
  pull_request:
    branches: [main, develop]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install flake8
      - run: flake8 files/ scripts/ --max-line-length=120

  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: pip install -r files/requirements.txt
      - run: python -m pytest tests/ -v
```

**File: `.github/workflows/deploy.yml`**
```yaml
name: Deploy to Cloud Run

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: google-github-actions/auth@v2
        with:
          credentials_json: ${{ secrets.GCP_SA_KEY }}
      - uses: google-github-actions/deploy-cloudrun@v2
        with:
          service: fb-pipeline
          region: asia-southeast1
          source: ./files
```

---

### 3.7 PR Template — Mỗi Tính Năng Phải Có Review

**File: `.github/PULL_REQUEST_TEMPLATE.md`**
```markdown
## 📋 Mô tả thay đổi
<!-- Giải thích bạn đã làm gì -->

## ✅ Checklist
- [ ] Đã test cục bộ
- [ ] Không commit secrets/credentials
- [ ] Đã cập nhật README nếu cần
- [ ] Không break pipeline đang chạy

## 🧪 Cách test
<!-- Hướng dẫn người review kiểm tra -->

## 📸 Screenshot (nếu có)
```

---

## 4. 🔄 Quy Trình Làm Việc Hàng Ngày

### Người A (Bắt đầu task mới)
```bash
git checkout develop
git pull origin develop          # Luôn pull trước khi làm
git checkout -b feature/ten-tinh-nang

# ... làm việc ...

git add -p                       # Add từng phần, không dùng git add .
git commit -m "feat: mô tả rõ ràng"
git push origin feature/ten-tinh-nang
# Tạo PR trên GitHub → tag Người B review
```

### Người B (Review & Merge)
```bash
# Trên GitHub: review PR, comment nếu cần
# Approve → Squash and Merge vào develop
# Khi đủ tính năng cho 1 release:
# develop → PR → main → tự động deploy
```

---

## 5. 🛠️ Setup Máy Mới (Onboarding)

Khi thêm người thứ 3 hoặc đổi máy:

```bash
# 1. Clone repo
git clone https://github.com/tuda0212/Vietlife.git
cd Vietlife

# 2. Setup Python env
python3 -m venv .venv
source .venv/bin/activate
pip install -r files/requirements.txt

# 3. Copy và điền credentials
cp .env.example .env
# → Điền API keys, Service Account path vào .env

# 4. Đặt service account key (KHÔNG commit file này)
# Đặt vào: ~/secrets/vietlife-sa.json (ngoài repo)
export GOOGLE_APPLICATION_CREDENTIALS=~/secrets/vietlife-sa.json

# 5. Verify setup
python3 scripts/inspect_bq.py
```

---

## 6. 📊 Commit Convention

Dùng **Conventional Commits** để lịch sử rõ ràng:

| Prefix | Khi nào dùng | Ví dụ |
|--------|-------------|-------|
| `feat:` | Tính năng mới | `feat: thêm sync dữ liệu TikTok` |
| `fix:` | Sửa bug | `fix: lỗi parse ngày trong CRM pipeline` |
| `sql:` | Thay đổi query/view | `sql: cập nhật v_report_duoc thêm cột chi_phi` |
| `config:` | Thay đổi cấu hình | `config: thêm ad account mới cho Dược Nano` |
| `docs:` | Cập nhật tài liệu | `docs: cập nhật README hướng dẫn deploy` |
| `chore:` | Maintenance | `chore: cập nhật requirements.txt` |

---

## 7. 🎯 Lộ Trình Triển Khai (Ưu Tiên)

### Tuần 1 — Nền Tảng An Toàn
- [ ] Thêm `.gitignore` đầy đủ (ngăn commit secrets)
- [ ] Kiểm tra và xóa secrets nếu đã commit vào repo
- [ ] Bật Branch Protection trên GitHub cho `main`
- [ ] Sửa script auto-commit: push sang branch `auto-backup` thay vì `main`

### Tuần 2 — Quy Trình Làm Việc
- [ ] Tạo nhánh `develop`
- [ ] Viết `docs/ONBOARDING.md`
- [ ] Tạo `.env.example`
- [ ] Thêm PR template

### Tuần 3 — Tự Động Hóa
- [ ] Thiết lập GitHub Actions CI (lint check)
- [ ] Thiết lập GitHub Actions CD (auto-deploy)
- [ ] Viết test cơ bản cho pipeline

---

## 8. 💡 Tóm Tắt Nguyên Tắc Vàng

> 1. **Không bao giờ push thẳng lên `main`** — luôn qua PR
> 2. **Không commit secrets** — `.env` và `*.json` phải trong `.gitignore`
> 3. **Pull trước khi làm** — `git pull` mỗi buổi sáng
> 4. **Branch nhỏ, commit thường xuyên** — dễ merge, ít conflict
> 5. **Auto-commit hourly chỉ trên backup branch** — không phá `main`
