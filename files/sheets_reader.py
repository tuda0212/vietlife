"""
sheets_reader.py — Đọc Google Sheet CRM qua Google Sheets API.
Dùng Application Default Credentials (ADC) trên Cloud Run.
Port logic từ buildCrmAdIdMapFromSpreadsheet_() trong Apps Script.
"""

import os
import logging
import re
import unicodedata
from datetime import datetime, timezone, timedelta

import subprocess
from google.oauth2 import service_account
from google.oauth2.credentials import Credentials
from google.protobuf import symbol_database as _symbol_database
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
_arrival_cache = {}


def _get_sheets_service():
    global _sheets_service
    if _sheets_service is None:
        # 1. Thử dùng Service Account chỉ định bởi GOOGLE_APPLICATION_CREDENTIALS trước
        sa_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
        if sa_path and os.path.exists(sa_path):
            try:
                credentials = service_account.Credentials.from_service_account_file(
                    sa_path,
                    scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"]
                )
                _sheets_service = build("sheets", "v4", credentials=credentials, cache_discovery=False)
                logger.info(f"[Sheets] Sử dụng Service Account từ {sa_path} thành công.")
                return _sheets_service
            except Exception as e:
                logger.warning(f"[Sheets] Không dùng được Service Account từ {sa_path}: {e}")

        # 2. Thử lấy access token từ gcloud CLI (chạy local)
        try:
            token = subprocess.check_output(
                ["gcloud", "auth", "print-access-token"],
                text=True,
                stderr=subprocess.DEVNULL
            ).strip()
            if token:
                # Không lưu vào global _sheets_service nếu dùng access token thô của gcloud CLI vì nó sẽ hết hạn sau 1 tiếng.
                # Trả về service instance tạm thời để lần sau gọi lại gcloud tạo token mới.
                credentials = Credentials(token)
                service = build("sheets", "v4", credentials=credentials, cache_discovery=False)
                logger.info("[Sheets] Sử dụng access token tạm thời từ gcloud CLI.")
                return service
        except Exception as e:
            logger.warning(f"[Sheets] Không lấy được token từ gcloud CLI: {e}")

        # 3. Fallback sang ADC mặc định
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
    val_str = str(value).strip()
    if val_str.endswith(".0"):
        val_str = val_str[:-2]
    digits = re.sub(r"\D", "", val_str)
    if len(digits) == 9 and not digits.startswith("0"):
        digits = "0" + digits
    if digits.startswith("84") and len(digits) == 11:
        digits = "0" + digits[2:]
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


def parse_arrival_date(ma_quan_ly: str) -> str:
    if not ma_quan_ly:
        return ""
    ma_str = str(ma_quan_ly).strip()
    m = re.search(r"_BA(\d{2})(\d{2})(\d{2})", ma_str)
    if m:
        return f"20{m.group(1)}-{m.group(2)}-{m.group(3)}"
    return ""


def read_center_crm_sheet(
    spreadsheet_id: str,
    main_tab: str,
    arrival_tab: str,
    start_date: str,
    end_date: str,
    specialty_code: str,
    version: int
) -> list[dict]:
    """
    Đọc dữ liệu từ bảng tính Trung tâm CRM (gồm tab data chính và tab data đến cửa).
    Thực hiện ghép nối hai tab bằng SĐT ở trong bộ nhớ.
    """
    global _arrival_cache
    cache_key = (spreadsheet_id, arrival_tab)

    service = _get_sheets_service()
    sheet_api = service.spreadsheets()

    # Lấy thông tin metadata của sheet trước
    meta = sheet_api.get(spreadsheetId=spreadsheet_id).execute()

    if cache_key in _arrival_cache:
        arrival_map = _arrival_cache[cache_key]
        logger.info(f"[Sheets] Tái sử dụng arrival_map từ cache cho {cache_key}")
    else:
        arrival_map = {}
        has_arrival = False
        for s in meta["sheets"]:
            if s["properties"]["title"] == arrival_tab:
                has_arrival = True
                break

        if has_arrival:
            try:
                # Đọc dòng đầu tiên để lấy header
                header_res = sheet_api.values().get(
                    spreadsheetId=spreadsheet_id,
                    range=f"'{arrival_tab}'!A1:Z1",
                    valueRenderOption="UNFORMATTED_VALUE"
                ).execute()
                headers = [str(h).strip().lower() for h in header_res.get("values", [[]])[0]]
                
                # Mặc định index cũ
                phone_idx = 0
                rev_idx = 6
                
                # Tìm kiếm cột SĐT và Thành tiền động
                for idx, h in enumerate(headers):
                    if "so_dien_thoai" in h or "so dien thoai" in h or "sdt" in h:
                        phone_idx = idx
                    elif "thanh_tien" in h or "thanh tien" in h or "doanh thu" in h:
                        rev_idx = idx
                
                max_idx = max(phone_idx, rev_idx)
                logger.info(f"[Sheets] Tab đến cửa '{arrival_tab}': SĐT=cột {phone_idx}, Doanh thu=cột {rev_idx}")
                
                # Đọc tối đa 200,000 dòng vì tab 'Data Đến Cửa' chung rất lớn (~141,000 dòng)
                result = sheet_api.values().get(
                    spreadsheetId=spreadsheet_id,
                    range=f"'{arrival_tab}'!A2:Z200000",
                    valueRenderOption="UNFORMATTED_VALUE"
                ).execute()
                values = result.get("values", [])
                
                seen_ma_ql = set()
                for row in values:
                    # Đảm bảo hàng có độ dài tối thiểu 5 cột
                    while len(row) < 5:
                        row.append("")
                    
                    if arrival_tab == "Data Đến Cửa":
                        ma_ql = str(row[1]).strip()
                    else:
                        ma_ql = str(row[0]).strip()

                    if not ma_ql:
                        continue
                    # Lọc trùng theo Mã quản lý để tránh nhân đôi doanh thu
                    if ma_ql in seen_ma_ql:
                        continue
                    seen_ma_ql.add(ma_ql)
                    
                    # Xử lý lệch cột đặc biệt cho tab 'Data Đến Cửa' của sheet mới
                    if arrival_tab == "Data Đến Cửa" and len(row) >= 5:
                        val_col2 = str(row[2]).strip()  # Cột C (SĐT không 0 hoặc có 0)
                        val_col3 = str(row[3]).strip()  # Cột D (SĐT có 0 hoặc doanh thu)
                        val_col4 = str(row[4]).strip()  # Cột E (Doanh thu hoặc chữ)
                        
                        phone_2 = normalize_phone(val_col2)
                        phone_3 = normalize_phone(val_col3)
                        
                        # Nếu cột D cũng chứa SĐT hợp lệ (sau khi chuẩn hóa)
                        if phone_3 and (phone_2 == phone_3 or (phone_3.startswith("0") and len(phone_3) >= 9)):
                            phone = phone_3
                            rev_raw = val_col4
                        else:
                            phone = phone_2 if phone_2 else phone_3
                            rev_raw = val_col3
                    else:
                        # Logic bình thường cho các sheet khác
                        while len(row) <= max_idx:
                            row.append("")
                        phone_raw = str(row[phone_idx]).strip()
                        phone = normalize_phone(phone_raw)
                        rev_raw = row[rev_idx]

                    if not phone:
                        continue

                    rev_clean = str(rev_raw).replace(".", "").replace(",", "").strip()
                    # Kiểm tra an toàn: nếu doanh thu trông giống số điện thoại (ví dụ: bắt đầu bằng 0 và dài >= 9 số)
                    # thì gán doanh thu = 0 để tránh nhận diện nhầm SĐT thành doanh thu khổng lồ
                    if rev_clean.startswith("0") and len(rev_clean) >= 9:
                        revenue = 0.0
                    else:
                        try:
                            revenue = float(rev_clean)
                        except ValueError:
                            revenue = 0.0

                    arr_date = parse_arrival_date(ma_ql)
                    if phone not in arrival_map:
                        arrival_map[phone] = []
                    arrival_map[phone].append({
                        "date": arr_date,
                        "revenue": revenue
                    })
                # Lưu vào cache sau khi đọc xong
                _arrival_cache[cache_key] = arrival_map
            except Exception as e:
                logger.warning(f"[Sheets] Không đọc được tab đến cửa '{arrival_tab}' từ {spreadsheet_id}: {e}")

    # 2. Đọc tab data chính
    rows = []
    
    # Tìm tổng số dòng từ metadata
    total_rows = 10000
    for s in meta["sheets"]:
        if s["properties"]["title"] == main_tab:
            total_rows = s["properties"]["gridProperties"].get("rowCount", 10000)
            break

    data_start = 2 # Bỏ qua header dòng 1
    end_col = "M" if version == 2026 else "L"
    booking_idx = 12 if version == 2026 else 11

    logger.info(f"[Sheets] Đọc tab chính '{main_tab}' từ {spreadsheet_id}, tổng {total_rows} dòng")

    for chunk_start in range(data_start, total_rows + 1, CRM_READ_CHUNK):
        chunk_end = min(chunk_start + CRM_READ_CHUNK - 1, total_rows)
        range_notation = f"'{main_tab}'!A{chunk_start}:{end_col}{chunk_end}"

        try:
            result = sheet_api.values().get(
                spreadsheetId=spreadsheet_id,
                range=range_notation,
                valueRenderOption="UNFORMATTED_VALUE",
                dateTimeRenderOption="FORMATTED_STRING"
            ).execute()
        except Exception as e:
            logger.error(f"[Sheets] Lỗi đọc chunk {range_notation}: {e}")
            break

        values = result.get("values", [])
        if not values:
            break

        for row in values:
            while len(row) < (booking_idx + 1):
                row.append("")

            date_raw = str(row[1]).strip()     # Col 1: Ngày nhập liệu
            phone_raw = str(row[3]).strip()    # Col 3: Số điện thoại
            channel = str(row[6]).strip()      # Col 6: Kênh/Bác sĩ
            booking_val = row[booking_idx]     # Col 11 hoặc 12: Kết quả liên hệ

            lead_date_str = parse_date_robust(date_raw)
            phone = normalize_phone(phone_raw)

            if not lead_date_str or not phone:
                continue

            # Lọc theo khoảng ngày cần đồng bộ
            if lead_date_str < start_date or lead_date_str > end_date:
                continue

            is_booking = is_booking_status(booking_val)
            
            # Khớp doanh thu & đến cửa theo logic ngày khám trong vòng 30 ngày kể từ lead_date
            is_arrival = False
            revenue = 0.0
            
            if phone in arrival_map:
                try:
                    lead_date_dt = datetime.strptime(lead_date_str, "%Y-%m-%d")
                    valid_visits = []
                    for visit in arrival_map[phone]:
                        if visit["date"]:
                            try:
                                arr_date_dt = datetime.strptime(visit["date"], "%Y-%m-%d")
                                # Chỉ tính ca khám xảy ra từ ngày đăng ký lead đến 30 ngày sau đó
                                if arr_date_dt >= lead_date_dt and arr_date_dt <= lead_date_dt + timedelta(days=30):
                                    valid_visits.append(visit)
                            except ValueError:
                                pass
                    if valid_visits:
                        is_arrival = True
                        revenue = sum(v["revenue"] for v in valid_visits)
                except Exception:
                    pass

            rows.append({
                "lead_date": lead_date_str,
                "phone": phone,
                "channel": channel,
                "booking_status": normalize_status_text(booking_val),
                "arrival_status": "Đến cửa" if is_arrival else "Chưa đến cửa",
                "is_booking": is_booking,
                "is_arrival": is_arrival,
                "revenue": revenue
            })

        if len(values) < CRM_READ_CHUNK:
            break

    logger.info(f"[Sheets] {spreadsheet_id}: Đã trích xuất {len(rows)} leads hợp lệ")
    return rows
