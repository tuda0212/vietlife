"""
config_crm.py — Cấu hình Pipeline 2: Google Sheets CRM → BigQuery
Chỉnh sửa DOCTOR_SHEETS để thêm/bớt bác sĩ.
"""

import os

# =================================================================
# BIGQUERY
# =================================================================
GCP_PROJECT_ID  = os.environ.get("GCP_PROJECT_ID", "gen-lang-client-0738410622")
BQ_DATASET      = os.environ.get("BQ_DATASET", "marketing_data")
BQ_TABLE_LEADS  = os.environ.get("BQ_TABLE_LEADS", "botcake_leads")

# =================================================================
# GOOGLE SHEETS — map bác sĩ → Spreadsheet ID
# Cấu trúc sheet CRM (tab đầu tiên), cột I:N:
#   I = Tháng     (MM/YYYY hoặc YYYY-MM)
#   J = Ngày      (DD hoặc full date)
#   K = SĐT
#   L = Trạng thái Đặt lịch
#   M = Đến cửa
#   N = ad_id_crm
# =================================================================
DOCTOR_SHEETS = {
    # Y tế — Cột Sống
    "Định": {
        "spreadsheet_id": "1nqCLy44UKbqFlbDYwpnTGDQm4XRgHsSyvIbEQNHAOSc",
        "specialty_code": "CS",
        "specialty_name": "Cột Sống",
        "doctor_name":    "BS Định",
        "report_group":   "Y tế",
    },
    "Tuyên": {
        "spreadsheet_id": "1zEeuhBDiExB2cokMZlbWdqrcnoV9WjmwTin_Pssv3mM",
        "specialty_code": "CS",
        "specialty_name": "Cột Sống",
        "doctor_name":    "BS Tuyên",
        "report_group":   "Y tế",
    },
    # Y tế — Thần Kinh
    "Phạm Duy": {
        "spreadsheet_id": "10ZOIK84AcoDZI3_fVALadQ2euIXbXAXE6c9kw07u0bY",
        "specialty_code": "TK",
        "specialty_name": "Thần Kinh",
        "doctor_name":    "BS Phạm Duy",
        "report_group":   "Y tế",
    },
    "Kim Chung": {
        "spreadsheet_id": "17BLBBWBNGuhRt7zaQpVHvpi2AOLbUyDl5vGJN3VHtnc",
        "specialty_code": "TK",
        "specialty_name": "Thần Kinh",
        "doctor_name":    "BS Kim Chung",
        "report_group":   "Y tế",
    },
    "Kiều Đình Hùng": {
        "spreadsheet_id": "1qqrBGbsxCemcYol3EEGo6DplnhOMsBewKEElVS3ERJQ",
        "specialty_code": "TK",
        "specialty_name": "Thần Kinh",
        "doctor_name":    "BS Kiều Đình Hùng",
        "report_group":   "Y tế",
    },
    # Y tế — Cơ Xương Khớp
    "Vũ Anh": {
        "spreadsheet_id": "1IpRGhylPd4TENwT4tZq5mOZnTzLmttkn4l8FejWtNZE",
        "specialty_code": "CXK",
        "specialty_name": "Cơ Xương Khớp",
        "doctor_name":    "BS Vũ Anh",
        "report_group":   "Y tế",
    },
    # Dược Nano — Bình An & Vững Cốt
    "Dược Nano": {
        "spreadsheet_id": "1Y99VmZqvXEsBY8zII3bcY-qIYDNPuATpXWC01hwrzVI",
        "specialty_code": "BA",
        "specialty_name": "Bình An",
        "doctor_name":    "Dược Nano",
        "report_group":   "Dược Nano",
        "sheet_type":     "duoc_nano",
        "sheet_title":    "DATA NANO",
    },
}

# =================================================================
# TRẠNG THÁI CRM — normalize text để so khớp
# =================================================================
BOOKING_KEYWORDS = ["dat lich", "đặt lịch", "dat_lich"]
ARRIVAL_KEYWORDS = ["den cua", "đến cửa", "den_cua"]

# Số dòng header bỏ qua ở đầu sheet (mặc định 1 dòng tiêu đề)
CRM_HEADER_ROWS = 1

# Đọc theo chunk để tránh timeout với sheet lớn
CRM_READ_CHUNK  = 5000

# Xóa data cũ theo ngày trước khi insert (upsert)
UPSERT_DELETE_BEFORE_INSERT = True
