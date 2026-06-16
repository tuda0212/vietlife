"""
sheets_reader.py — Đọc Google Sheet CRM qua Google Sheets API.
Dùng Application Default Credentials (ADC) trên Cloud Run.
Port logic từ buildCrmAdIdMapFromSpreadsheet_() trong Apps Script.
"""

import logging
import re
import unicodedata
from datetime import datetime, timezone

from google.oauth2 import service_account
from googleapiclient.discovery import build
from google.auth import default as google_auth_default

from config_crm import (
    BOOKING_KEYWORDS,
    ARRIVAL_KEYWORDS,
    CRM_HEADER_ROWS,
    CRM_READ_CHUNK,
)

logger = logging.getLogger(__name__)

_sheets_service = None


def _get_sheets_service():
    global _sheets_service
    if _sheets_service is None:
        credentials, _ = google_auth_default(
            scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"]
        )
        _sheets_service = build("sheets", "v4", credentials=credentials, cache_discovery=False)
    return _sheets_service


def read_crm_sheet(
    spreadsheet_id: str,
    start_date: str,
    end_date: str,
    sheet_type: str = "doctor",
    sheet_title: str = None,
) -> list[dict]:
    """
    Đọc tab đầu tiên hoặc tab chỉ định của Google Sheet CRM.
    - Với doctor: đọc cột A:N, lọc theo start_date -> end_date.
    - Với duoc_nano: đọc cột A:AH để lấy thêm Doanh số (col 22), số lượng BA (col 18), IP VNM (col 19).
    """
    from config import SPECIALTY_NAMES

    service   = _get_sheets_service()
    sheet_api = service.spreadsheets()

    # Lấy thông tin metadata và tìm tên tab + số dòng
    meta = sheet_api.get(spreadsheetId=spreadsheet_id).execute()
    if sheet_title:
        first_sheet = sheet_title
        total_rows = 10000
        for s in meta["sheets"]:
            if s["properties"]["title"] == sheet_title:
                total_rows = s["properties"]["gridProperties"].get("rowCount", 10000)
                break
    else:
        first_sheet = meta["sheets"][0]["properties"]["title"]
        total_rows = meta["sheets"][0]["properties"]["gridProperties"].get("rowCount", 10000)

    logger.info(f"[Sheets] {spreadsheet_id}: Tab cần đọc = '{first_sheet}', tổng số dòng = {total_rows}")
    data_start = CRM_HEADER_ROWS + 1  # bỏ qua header

    rows = []
    end_col = "AH" if sheet_type == "duoc_nano" else "N"
    
    for chunk_start in range(data_start, total_rows + 1, CRM_READ_CHUNK):
        chunk_end = min(chunk_start + CRM_READ_CHUNK - 1, total_rows)
        range_notation = f"'{first_sheet}'!A{chunk_start}:{end_col}{chunk_end}"

        result = sheet_api.values().get(
            spreadsheetId=spreadsheet_id,
            range=range_notation,
            valueRenderOption="UNFORMATTED_VALUE",
            dateTimeRenderOption="FORMATTED_STRING",
        ).execute()

        values = result.get("values", [])
        if not values:
            break

        for row in values:
            if sheet_type == "duoc_nano":
                # Pad row đủ 34 cột (A đến AH)
                while len(row) < 34:
                    row.append("")

                date_raw  = str(row[1]).strip() # Col 1: Ngày nhập liệu
                phone_raw = str(row[3]).strip() # Col 3: Số điện thoại
                
                lead_date = parse_date_robust(date_raw)
                phone     = normalize_phone(phone_raw)

                if not lead_date or not phone:
                    continue

                if lead_date < start_date or lead_date > end_date:
                    continue

                # Doanh số (Col 22)
                rev_raw = str(row[22]).strip()
                rev_clean = rev_raw.replace(".", "")
                try:
                    revenue = float(rev_clean)
                except ValueError:
                    revenue = 0.0

                # Chuyên khoa động theo sản phẩm
                ba_qty = str(row[18]).strip()
                ip_qty = str(row[19]).strip()

                if ip_qty and ip_qty != "0":
                    specialty_code = "VT"
                elif ba_qty and ba_qty != "0":
                    specialty_code = "BA"
                else:
                    channel = str(row[7]).strip().lower()
                    if "binh an" in channel or "đau dau" in channel or "dau dau" in channel:
                        specialty_code = "BA"
                    else:
                        specialty_code = "BA"

                specialty_name = SPECIALTY_NAMES.get(specialty_code, specialty_code)

                rows.append({
                    "lead_date":      lead_date,
                    "phone":          phone,
                    "ad_id":          "",
                    "subscriber_id":  "",
                    "booking_status": "",
                    "arrival_status": "",
                    "is_booking":     False,
                    "is_arrival":     False,
                    "revenue":        revenue,
                    "specialty_code": specialty_code,
                    "specialty_name": specialty_name,
                })
            else:
                # Pad row đủ 14 cột (A đến N)
                while len(row) < 14:
                    row.append("")

                # A: psid, D: SĐT, E: SĐT chuẩn hóa, G: ad_id, H: Ngày đăng ký
                # I: Tháng, J: Ngày, K: SĐT crm, L: Tình trạng, M: Đến cửa, N: ad_id_crm
                psid        = str(row[0]).strip()
                phone_raw   = str(row[4]).strip() or str(row[3]).strip() or str(row[10]).strip()
                ad_id_raw   = str(row[6]).strip() or str(row[13]).strip()
                date_raw    = str(row[7]).strip() # Ngày đăng ký
                booking_val = row[11]  # L: Đặt lịch
                arrival_val = row[12]  # M: Đến cửa

                # Fallback ngày nếu cột H trống
                if not date_raw:
                    month_val = str(row[8]).strip()
                    day_val   = str(row[9]).strip()
                    if parse_date_robust(day_val):
                        date_raw = day_val
                    elif month_val and day_val:
                        date_raw = f"2026-{month_val.zfill(2)}-{day_val.zfill(2)}"

                lead_date = parse_date_robust(date_raw)
                if not lead_date:
                    continue
                if lead_date < start_date or lead_date > end_date:
                    continue

                ad_id = normalize_ad_id(ad_id_raw)
                phone      = normalize_phone(phone_raw)
                is_booking = is_booking_status(booking_val)
                is_arrival = is_arrival_status(arrival_val)

                rows.append({
                    "lead_date":      lead_date,
                    "phone":          phone,
                    "ad_id":          ad_id,
                    "subscriber_id":  psid,
                    "booking_status": normalize_status_text(booking_val),
                    "arrival_status": normalize_status_text(arrival_val),
                    "is_booking":     is_booking,
                    "is_arrival":     is_arrival,
                    "revenue":        0.0,
                })

        logger.info(
            f"[Sheets] {spreadsheet_id}: đọc đến dòng {chunk_end}, "
            f"tích lũy {len(rows)} dòng hợp lệ"
        )

        if len(values) < CRM_READ_CHUNK:
            break

    logger.info(f"[Sheets] {spreadsheet_id}: tổng {len(rows)} dòng trong khoảng ngày")
    return rows


# =================================================================
# NORMALIZE HELPERS (port từ Apps Script)
# =================================================================

def serial_to_date(serial) -> str:
    try:
        serial_num = float(serial)
        base_date = datetime(1899, 12, 30)
        delta = timedelta(days=serial_num)
        return (base_date + delta).strftime("%Y-%m-%d")
    except Exception:
        return ""


def parse_date_robust(date_val) -> str:
    if not date_val:
        return ""
    val_str = str(date_val).strip()

    # Thử parse số serial ngày của Google Sheets
    date_from_serial = serial_to_date(val_str)
    if date_from_serial:
        return date_from_serial

    # Định dạng YYYY-MM-DD
    if re.match(r"^\d{4}-\d{2}-\d{2}$", val_str):
        return val_str

    # Định dạng DD/MM/YYYY
    m = re.match(r"^(\d{1,2})/(\d{1,2})/(\d{4})$", val_str)
    if m:
        return f"{m.group(3)}-{m.group(2).zfill(2)}-{m.group(1).zfill(2)}"

    # Thử parse các định dạng thông dụng khác
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"):
        try:
            return datetime.strptime(val_str, fmt).strftime("%Y-%m-%d")
        except ValueError:
            pass

    return ""


def normalize_crm_date(month_val, day_val) -> str:
    # Không còn dùng trực tiếp vì đã chuyển sang parse_date_robust
    return ""


def normalize_ad_id(value) -> str:
    if not value:
        return ""
    text = str(value).strip().lstrip("'")
    nums = re.findall(r"\d{6,}", text)
    return nums[0] if nums else ""


def normalize_phone(value) -> str:
    if not value:
        return ""
    digits = re.sub(r"\D", "", str(value))
    return digits if digits else ""


def normalize_status_text(value) -> str:
    text = str(value or "").strip().lower()
    text = unicodedata.normalize("NFD", text)
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    text = text.replace("đ", "d").replace("D", "d")
    return re.sub(r"\s+", " ", text).strip()


def is_booking_status(value) -> bool:
    norm = normalize_status_text(value)
    return any(kw in norm for kw in BOOKING_KEYWORDS)


def is_arrival_status(value) -> bool:
    norm = normalize_status_text(value)
    return any(kw in norm for kw in ARRIVAL_KEYWORDS)
