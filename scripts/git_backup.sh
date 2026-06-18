#!/bin/bash
# =============================================================================
# git_backup.sh — Auto-backup script an toàn cho 2 người làm chung repo
# =============================================================================
# MỤC ĐÍCH: Push backup sang nhánh riêng, KHÔNG push thẳng lên main/develop
# CÁCH DÙNG:
#   Chạy tay:  bash /Users/daudau/VL/scripts/git_backup.sh
#   Tự động:   Thiết lập cron job (xem hướng dẫn ở cuối file)
# =============================================================================

set -euo pipefail

REPO_DIR="/Users/daudau/VL"
LOG_FILE="$HOME/.vl_backup.log"
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
DATE_TAG=$(date '+%Y%m%d')

log() {
    echo "[$TIMESTAMP] $*" | tee -a "$LOG_FILE"
}

cd "$REPO_DIR" || { log "❌ Không tìm thấy thư mục $REPO_DIR"; exit 1; }

# ─────────────────────────────────────────────────────────────────────────────
# KIỂM TRA: Đang ở nhánh nào?
# ─────────────────────────────────────────────────────────────────────────────
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
log "🌿 Đang ở nhánh: $CURRENT_BRANCH"

# ─────────────────────────────────────────────────────────────────────────────
# KHÔNG làm gì nếu đang ở main — bảo vệ production
# ─────────────────────────────────────────────────────────────────────────────
if [[ "$CURRENT_BRANCH" == "main" ]]; then
    log "⚠️  Đang ở nhánh 'main' — backup script sẽ không push trực tiếp."
    log "   Hãy chuyển sang nhánh develop hoặc feature/* trước khi làm việc."
    log "   Lệnh: git checkout develop"
    exit 0
fi

# ─────────────────────────────────────────────────────────────────────────────
# KIỂM TRA: Có thay đổi không?
# ─────────────────────────────────────────────────────────────────────────────
if git diff --quiet && git diff --staged --quiet && [ -z "$(git ls-files --others --exclude-standard)" ]; then
    log "✅ Không có thay đổi mới — bỏ qua backup."
    exit 0
fi

# ─────────────────────────────────────────────────────────────────────────────
# COMMIT: Nếu đang ở develop hoặc feature/* → commit bình thường
# ─────────────────────────────────────────────────────────────────────────────
if [[ "$CURRENT_BRANCH" == "develop" || "$CURRENT_BRANCH" == feature/* || "$CURRENT_BRANCH" == fix/* ]]; then
    log "💾 Commit vào nhánh '$CURRENT_BRANCH'..."
    git add -A
    git commit -m "chore: auto-backup $(date '+%Y-%m-%d %H:%M') [skip ci]"
    git push origin "$CURRENT_BRANCH"
    log "✅ Đã push lên origin/$CURRENT_BRANCH"

# ─────────────────────────────────────────────────────────────────────────────
# BACKUP BRANCH: Nhánh không xác định → tạo backup branch tạm
# ─────────────────────────────────────────────────────────────────────────────
else
    BACKUP_BRANCH="auto-backup/$DATE_TAG-$(hostname -s)"
    log "📦 Tạo backup branch: $BACKUP_BRANCH"
    git stash push -m "auto-backup $TIMESTAMP" 2>/dev/null || true
    git checkout -b "$BACKUP_BRANCH" 2>/dev/null || git checkout "$BACKUP_BRANCH"
    git stash pop 2>/dev/null || true
    git add -A
    git commit -m "chore: auto-backup từ $CURRENT_BRANCH lúc $(date '+%Y-%m-%d %H:%M') [skip ci]"
    git push origin "$BACKUP_BRANCH"
    git checkout "$CURRENT_BRANCH"
    log "✅ Backup xong tại origin/$BACKUP_BRANCH"
    log "   Nhánh hiện tại vẫn là: $CURRENT_BRANCH"
fi

log "─────────────────────────────────────────"

# =============================================================================
# HƯỚNG DẪN CÀI ĐẶT CRON JOB (chạy backup mỗi giờ)
# =============================================================================
# Mở crontab:  crontab -e
# Thêm dòng:   0 * * * * /bin/bash /Users/daudau/VL/scripts/git_backup.sh
# Kiểm tra log: tail -f ~/.vl_backup.log
# =============================================================================
