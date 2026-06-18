#!/bin/bash
# =============================================================================
# setup_branch_protection.sh — Bật Branch Protection cho nhánh main
# =============================================================================
# CÁCH DÙNG:
#   1. Tạo GitHub Personal Access Token tại: https://github.com/settings/tokens
#      → Cần quyền: repo (hoặc repo:write)
#   2. Chạy: GITHUB_TOKEN=ghp_xxx bash /Users/daudau/VL/scripts/setup_branch_protection.sh
# =============================================================================

set -euo pipefail

REPO="tuda0212/vietlife"
BRANCH="main"

if [[ -z "${GITHUB_TOKEN:-}" ]]; then
    echo "❌ Thiếu GITHUB_TOKEN!"
    echo "   Tạo token tại: https://github.com/settings/tokens/new"
    echo "   Tick quyền: repo"
    echo "   Rồi chạy: GITHUB_TOKEN=ghp_xxx bash $0"
    exit 1
fi

echo "🔐 Đang bật Branch Protection cho nhánh '$BRANCH' trên '$REPO'..."

curl -s -X PUT \
  -H "Authorization: Bearer $GITHUB_TOKEN" \
  -H "Accept: application/vnd.github+json" \
  -H "X-GitHub-Api-Version: 2022-11-28" \
  "https://api.github.com/repos/$REPO/branches/$BRANCH/protection" \
  -d '{
    "required_status_checks": {
      "strict": true,
      "contexts": ["CI — Kiểm Tra Code Tự Động"]
    },
    "enforce_admins": false,
    "required_pull_request_reviews": {
      "required_approving_review_count": 1,
      "dismiss_stale_reviews": true
    },
    "restrictions": null,
    "allow_force_pushes": false,
    "allow_deletions": false
  }' | python3 -m json.tool 2>/dev/null | grep -E '"url"|"name"|"enabled"' | head -10

echo ""
echo "✅ Branch Protection đã được bật cho nhánh '$BRANCH'!"
echo "   → Từ giờ mọi thay đổi lên main phải qua Pull Request"
echo "   → Cần ít nhất 1 người approve"
echo "   → CI phải pass trước khi merge"
