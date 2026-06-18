# 🚀 Hướng Dẫn Setup Máy Mới — Project Vietlife

> Dành cho thành viên mới hoặc khi đổi máy tính.
> Thực hiện đúng thứ tự, mỗi bước đều quan trọng.

---

## Yêu Cầu Hệ Thống

| Tool | Version | Kiểm tra |
|------|---------|---------|
| Python | ≥ 3.11 | `python3 --version` |
| Git | ≥ 2.x | `git --version` |
| gcloud CLI | Mới nhất | `gcloud --version` |

---

## Bước 1: Clone Repository

```bash
git clone https://github.com/tuda0212/Vietlife.git
cd Vietlife
```

---

## Bước 2: Thiết Lập Python Environment

```bash
# Tạo virtual environment
python3 -m venv .venv

# Kích hoạt (macOS/Linux)
source .venv/bin/activate

# Cài đặt dependencies
pip install -r files/requirements.txt
```

> ⚠️ **Quan trọng:** Thư mục `.venv/` được liệt kê trong `.gitignore` — KHÔNG commit vào repo.

---

## Bước 3: Thiết Lập Biến Môi Trường

```bash
# Copy file mẫu
cp .env.example .env
```

Mở file `.env` và điền các giá trị thật:

```bash
# Lấy Facebook Access Token từ: https://developers.facebook.com
FB_ACCESS_TOKEN=EAA...your_token_here

# GCP Project (thường không cần đổi)
GCP_PROJECT_ID=gen-lang-client-0738410622
BQ_DATASET=marketing_data
BQ_TABLE=fb_ad_insights

# Đường dẫn Service Account (để NGOÀI thư mục repo)
GOOGLE_APPLICATION_CREDENTIALS=/Users/ten-ban/secrets/vietlife-sa.json
```

> 🔐 **Lấy credentials:** Xin từ thành viên khác trong team qua kênh bảo mật (Zalo riêng, không gửi qua email/Messenger công khai).

---

## Bước 4: Thiết Lập Google Service Account

```bash
# Tạo thư mục secrets NGOÀI repo
mkdir -p ~/secrets

# Đặt file JSON Service Account vào đây (nhận từ team)
# ~/secrets/vietlife-sa.json

# Xác nhận Google Cloud auth
gcloud auth application-default login
# HOẶC dùng service account:
export GOOGLE_APPLICATION_CREDENTIALS=~/secrets/vietlife-sa.json
```

---

## Bước 5: Verify Setup

```bash
# Kiểm tra kết nối BigQuery
python3 scripts/inspect_bq.py

# Kiểm tra views hiện tại
python3 scripts/verify_view.py
```

Nếu không có lỗi → setup thành công ✅

---

## Quy Trình Làm Việc Hàng Ngày

### Bắt đầu task mới

```bash
# 1. Đảm bảo đang ở develop và cập nhật mới nhất
git checkout develop
git pull origin develop

# 2. Tạo nhánh mới cho task
git checkout -b feature/ten-tinh-nang
# Ví dụ: git checkout -b feature/them-bao-cao-tiktok

# 3. Làm việc... làm việc... làm việc...

# 4. Commit theo convention
git add -p   # Review từng thay đổi trước khi add
git commit -m "feat: thêm báo cáo TikTok vào dashboard"

# 5. Push và tạo PR
git push origin feature/ten-tinh-nang
# → Vào GitHub tạo Pull Request → assign người kia review
```

### Commit Convention

| Prefix | Ví dụ |
|--------|-------|
| `feat:` | `feat: thêm sync dữ liệu TikTok` |
| `fix:` | `fix: lỗi parse ngày trong CRM pipeline` |
| `sql:` | `sql: cập nhật v_report_duoc thêm cột chi_phi` |
| `config:` | `config: thêm ad account mới cho Dược Nano` |
| `docs:` | `docs: cập nhật README hướng dẫn deploy` |
| `chore:` | `chore: cập nhật requirements.txt` |

---

## Cấu Trúc Nhánh Git

```
main        ← Production (Cloud Run tự động deploy từ đây)
  │
  └─ develop ← Staging / Tích hợp chung
       │
       ├─ feature/ten-ban/ten-task  ← Tính năng mới
       ├─ fix/mo-ta-bug              ← Sửa bug
       └─ hotfix/loi-cap-bac        ← Vá khẩn cấp production
```

**Quy tắc:**
- ✅ `main` chỉ nhận merge từ `develop` qua Pull Request
- ✅ Mỗi PR cần ít nhất 1 người review và approve
- ❌ Không bao giờ push trực tiếp lên `main`

---

## Xử Lý Merge Conflict

```bash
# Nếu bị conflict khi merge:
git fetch origin
git rebase origin/develop

# Mở file conflict, sửa phần được đánh dấu:
# <<<<<<< HEAD
# code của bạn
# =======
# code của người kia
# >>>>>>> origin/develop

git add <file-da-su-conflict>
git rebase --continue
```

---

## Liên Hệ Khi Gặp Vấn Đề

| Vấn đề | Người hỏi |
|--------|----------|
| Facebook API token hết hạn | Hỏi thành viên đang quản lý FB Ads |
| Lỗi BigQuery permission | Kiểm tra Service Account đã được cấp quyền chưa |
| Cloud Run không deploy | Xem logs tại: console.cloud.google.com → Cloud Run → fb-pipeline → Logs |
