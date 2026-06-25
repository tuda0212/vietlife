"""
config.py — Cấu hình pipeline Facebook Ads → BigQuery
Chỉnh sửa file này để thêm/bớt tài khoản, bác sĩ, chuyên khoa.
"""

import os

# =================================================================
# GOOGLE CLOUD
# =================================================================
GCP_PROJECT_ID = os.environ.get("GCP_PROJECT_ID", "gen-lang-client-0738410622")
BQ_DATASET     = os.environ.get("BQ_DATASET", "marketing_data")
BQ_TABLE       = os.environ.get("BQ_TABLE", "fb_ad_insights")
BQ_TABLE_DEMOGRAPHICS = os.environ.get("BQ_TABLE_DEMOGRAPHICS", "fb_ad_insights_demographics")
GCS_BUCKET_NAME = os.environ.get("GCS_BUCKET_NAME", "vietlife-marketing-thumbnails")

# =================================================================
# FACEBOOK API
# =================================================================
FB_ACCESS_TOKEN  = os.environ.get("FB_ACCESS_TOKEN", "")
FB_GRAPH_VERSION = "v19.0"
FB_API_BASE      = f"https://graph.facebook.com/{FB_GRAPH_VERSION}"

# Số ad tối đa mỗi batch khi lấy creative/status
FB_BATCH_SIZE = 50

# =================================================================
# AD ACCOUNTS — map tài khoản theo chuyên khoa
# Thêm account mới: { "act_XXXXXXXXX": "CXK" }
# =================================================================
AD_ACCOUNTS = {
    "act_696152742916012": "TK",    # Thần Kinh
    "act_736221869292755": "CXK",   # Cơ Xương Khớp
    "act_1491394528173951": "CXK",  # Cơ Xương Khớp (Tài khoản mới tháng 3/2026)
    "act_2704042333126518": "VT",   # Vững Cốt (Dược Nano)
    "act_1433365117712667": "CS",   # Cột Sống (BS Tuyên)
    "act_2031624244397226": "CXK",  # Cơ Xương Khớp (Tài khoản mới - tạm map CXK)
}

# =================================================================
# CHUYÊN KHOA — map mã → tên đầy đủ
# =================================================================
SPECIALTY_NAMES = {
    "CXK": "Cơ Xương Khớp",
    "TK":  "Thần Kinh",
    "CS":  "Cột Sống",
    "TH":  "Tiêu Hóa",
    "VT":  "Vệ Tinh",
    "BA":  "Bình An",
}

# =================================================================
# FACEBOOK API FIELDS
# =================================================================
INSIGHTS_FIELDS = [
    "ad_id",
    "ad_name",
    "campaign_name",
    "date_start",
    "date_stop",
    "spend",
    "impressions",
    "clicks",
    "reach",
    "actions",
    "video_p25_watched_actions",
    "video_p50_watched_actions",
    "video_p75_watched_actions",
    "video_p95_watched_actions",
    "video_p100_watched_actions",
    "video_thruplay_watched_actions",
]

CREATIVE_FIELDS = (
    "status,effective_status,"
    "creative{body,title,effective_object_story_id,thumbnail_url,image_url,object_story_spec}"
)

# =================================================================
# PIPELINE BEHAVIOR
# =================================================================
# Số ngày nhìn lại mặc định nếu không truyền start_date/end_date
DEFAULT_LOOKBACK_DAYS = 7

# Xóa dữ liệu cũ cùng khoảng ngày trước khi insert (tránh trùng)
UPSERT_DELETE_BEFORE_INSERT = True
