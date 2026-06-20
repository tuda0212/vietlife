import os
import sys

# Cấu hình encoding UTF-8 cho stdout/stderr trên Windows console
if sys.platform.startswith('win'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

import re
import argparse
import subprocess
from datetime import datetime

# Tự động kiểm tra và cài đặt dependencies nếu thiếu
def install_dependencies():
    required = ["pandas", "openpyxl", "google-api-python-client", "google-auth"]
    missing = []
    for package in required:
        try:
            if package == "google-api-python-client":
                __import__("googleapiclient")
            elif package == "google-auth":
                __import__("google.auth")
            else:
                __import__(package)
        except ImportError:
            missing.append(package)
            
    if missing:
        print(f"Thư viện thiếu: {missing}. Đang tiến hành cài đặt tự động...")
        try:
            subprocess.run([sys.executable, "-m", "pip", "install"] + missing, check=True)
            print("Cài đặt thành công!")
        except Exception as e:
            print(f"Lỗi cài đặt thư viện: {e}")
            sys.exit(1)

install_dependencies()

import pandas as pd
from googleapiclient.discovery import build
from google.oauth2 import service_account
from google.oauth2.credentials import Credentials
import google.auth

# =================================================================
# ⚙️ HELPER FUNCTIONS & LOGIC CHUẨN HÓA
# =================================================================

def normalize_phone(phone):
    if phone is None:
        return ""
    cleaned = "".join(c for c in str(phone) if c.isdigit())
    if not cleaned:
        return ""
    return cleaned[-9:] if len(cleaned) >= 9 else cleaned

def format_to_ddmmyyyy(val):
    if val is None or pd.isna(val):
        return ""
    if hasattr(val, "strftime"):
        return val.strftime("%d/%m/%Y")
    val_str = str(val).strip()
    if not val_str:
        return ""
    val_str = val_str.split(" ")[0].split("T")[0]
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y"):
        try:
            dt = datetime.strptime(val_str, fmt)
            return dt.strftime("%d/%m/%Y")
        except ValueError:
            continue
    try:
        parsed = pd.to_datetime(val_str, errors='coerce')
        if not pd.isna(parsed):
            return parsed.strftime("%d/%m/%Y")
    except Exception:
        pass
    return val_str

def clean_phone_for_display(val):
    if val is None or pd.isna(val):
        return ""
    val_str = str(val).strip()
    if not val_str:
        return ""
    digits = "".join(c for c in val_str if c.isdigit())
    if not digits:
        return val_str
    if digits.startswith("0"):
        digits = digits[1:]
    return digits

def standardize_doctor(val, ds_bac_si):
    if not val:
        return ""
    val_str = str(val).strip().lower()
    for name in ds_bac_si:
        if name.lower() in val_str:
            return name
    return ""

def parse_date_only_str(val):
    if not val:
        return ""
    val_str = str(val).strip()
    if not val_str:
        return ""
    
    # Bỏ phần millisecond hoặc múi giờ nếu có dạng T00:00:00
    val_str = val_str.split(" ")[0].split("T")[0]
    
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y"):
        try:
            dt = datetime.strptime(val_str, fmt)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            continue
            
    try:
        parsed = pd.to_datetime(val_str, errors='coerce')
        if not pd.isna(parsed):
            return parsed.strftime("%Y-%m-%d")
    except Exception:
        pass
        
    return val_str

def get_timestamp(val):
    if not val:
        return 0
    if isinstance(val, (int, float)):
        try:
            if 30000 < float(val) < 60000:
                dt = pd.to_datetime(val, unit='D', origin='1899-12-30')
                return dt.timestamp()
            return float(val)
        except Exception:
            return 0
            
    val_str = str(val).strip()
    try:
        parsed = pd.to_datetime(val_str, errors='coerce')
        if not pd.isna(parsed):
            return parsed.timestamp()
    except Exception:
        pass
    return 0

# Parse dải ngày: e.g. 13-19Jun thành (2026-06-13, 2026-06-19)
def parse_timeframe_dates(timeframe_str):
    now = datetime.now()
    year = now.year
    
    # Tìm năm nếu được điền
    year_match = re.search(r"(\d{2,4})$", timeframe_str)
    if year_match:
        y_val = year_match.group(1)
        if len(y_val) == 2:
            year = 2000 + int(y_val)
        else:
            year = int(y_val)
        timeframe_str = timeframe_str[:-len(y_val)]
        
    # Match dạng 13-19Jun
    match = re.search(r"(\d+)-(\d+)\s*([a-zA-Z]+)", timeframe_str)
    if match:
        start_day = int(match.group(1))
        end_day = int(match.group(2))
        month_name = match.group(3).strip()
        
        months = {
            "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
            "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12
        }
        month_lower = month_name[:3].lower()
        month = months.get(month_lower, 6)
        
        start_date = datetime(year, month, start_day, 0, 0, 0)
        if end_day < start_day: # Vượt tháng
            if month == 12:
                end_date = datetime(year + 1, 1, end_day, 23, 59, 59)
            else:
                end_date = datetime(year, month + 1, end_day, 23, 59, 59)
        else:
            end_date = datetime(year, month, end_day, 23, 59, 59)
            
        return start_date, end_date
    return None, None

# =================================================================
# 🔑 XÁC THỰC GOOGLE API
# =================================================================

def get_sheets_service(credentials_path=None, token=None):
    if token:
        creds = Credentials(token)
        print("🔑 Xác thực bằng Access Token được cung cấp từ tham số --token.")
        return build("sheets", "v4", credentials=creds, cache_discovery=False)

    if credentials_path and os.path.exists(credentials_path):
        creds = service_account.Credentials.from_service_account_file(
            credentials_path,
            scopes=["https://www.googleapis.com/auth/spreadsheets"]
        )
        print(f"🔑 Xác thực bằng Service Account JSON từ: {credentials_path}")
        return build("sheets", "v4", credentials=creds, cache_discovery=False)
        
    env_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    if env_path and os.path.exists(env_path):
        creds = service_account.Credentials.from_service_account_file(
            env_path,
            scopes=["https://www.googleapis.com/auth/spreadsheets"]
        )
        print(f"🔑 Xác thực bằng Service Account JSON từ biến môi trường GOOGLE_APPLICATION_CREDENTIALS")
        return build("sheets", "v4", credentials=creds, cache_discovery=False)

    try:
        token_gcloud = subprocess.check_output(
            ["gcloud", "auth", "print-access-token"],
            text=True,
            stderr=subprocess.DEVNULL
        ).strip()
        if token_gcloud:
            creds = Credentials(token_gcloud)
            print("🔑 Xác thực bằng Access Token từ gcloud CLI thành công.")
            return build("sheets", "v4", credentials=creds, cache_discovery=False)
    except Exception:
        pass
        
    try:
        creds, _ = google.auth.default(
            scopes=["https://www.googleapis.com/auth/spreadsheets"]
        )
        print("🔑 Xác thực bằng Application Default Credentials (ADC) thành công.")
        return build("sheets", "v4", credentials=creds, cache_discovery=False)
    except Exception as e:
        print("\n❌ Không tìm thấy thông tin xác thực Google API. Vui lòng:")
        print("  1. Cấu hình gcloud CLI và chạy: gcloud auth application-default login")
        print("  2. Hoặc cấu hình file Service Account JSON và truyền qua tham số --credentials")
        raise e

# =================================================================
# 📊 ĐỐI SOÁT & XỬ LÝ DỮ LIỆU V12
# =================================================================

def build_lookup_map(sheet_api, spreadsheet_id):
    print("⏳ Đang tải dữ liệu cấu hình để dựng Lookup Map đối soát...")
    lookup_map = {}
    
    source_configs = [
        {"names": ["Data chung"], "date": 1, "phone": 3, "source": 5, "channel": 6, "range": "A2:G"},
        {"names": ["DATA Cũ"], "date": 0, "phone": 1, "source": 2, "channel": 4, "range": "A2:E"},
        {"names": ["Trung tâm cột sống 2026", "TTCS 2026"], "date": 1, "phone": 3, "source": 5, "channel": 6, "range": "A2:G"},
        {"names": ["Trung tâm CXK 2026", "TTCXK 2026"], "date": 1, "phone": 3, "source": 5, "channel": 6, "range": "A2:G"},
        {"names": ["Trung tâm Thần kinh 2026", "TTTK 2026"], "date": 1, "phone": 3, "source": 5, "channel": 6, "range": "A2:G"},
        {"names": ["Data 2024"], "date": 1, "phone": 4, "source": 5, "channel": 7, "range": "A2:J"},
        {"names": ["Data T1-T2"], "date": 1, "phone": 4, "source": 5, "channel": 7, "range": "A4:J"},
        {"names": ["Thầy"], "date": 1, "phone": 3, "source": 6, "channel": 7, "range": "A2:J"},
        {"names": ["Web"], "date": 0, "phone": 4, "source": 7, "channel": 7, "range": "A2:J"},
        {"names": ["CĐ"], "date": 3, "phone": 11, "source": 18, "channel": 20, "range": "A2:V"}
    ]
    
    for config in source_configs:
        rows = None
        sheet_name_used = None
        for name in config["names"]:
            range_notation = f"'{name}'!{config['range']}"
            try:
                result = sheet_api.values().get(
                    spreadsheetId=spreadsheet_id,
                    range=range_notation,
                    valueRenderOption="UNFORMATTED_VALUE"
                ).execute()
                rows = result.get("values", [])
                sheet_name_used = name
                break
            except Exception:
                continue
                
        if rows is None:
            print(f"⚠️ Cảnh báo: Không thể đọc cấu hình từ bất kỳ sheet nào trong nhóm {config['names']}.")
            continue
            
        print(f"  - Sheet '{sheet_name_used}': Đã đọc {len(rows)} dòng dữ liệu đối soát.")
        for row in rows:
            max_col = max(config["date"], config["phone"], config["source"], config["channel"])
            while len(row) <= max_col:
                row.append("")
                
            phone_raw = row[config["phone"]]
            phone_normalized = normalize_phone(phone_raw)
            
            if phone_normalized:
                raw_date = row[config["date"]]
                row_time = get_timestamp(raw_date)
                
                source_val = row[config["source"]]
                channel_val = row[config["channel"]]
                
                if phone_normalized not in lookup_map or row_time >= lookup_map[phone_normalized]["timestamp"]:
                    lookup_map[phone_normalized] = {
                        "source": source_val,
                        "channel": channel_val,
                        "timestamp": row_time
                    }
                    
    print(f"✅ Đã dựng Lookup Map thành công với {len(lookup_map)} số điện thoại đối soát.")
    return lookup_map

# Trích xuất toàn bộ lead MKT theo khoảng thời gian và vùng miền
def get_marketing_leads_for_week(sheet_api, config_ss_id, start_date, end_date, region):
    print(f"⏳ Đang lọc dữ liệu Marketing leads cho miền {region} từ {start_date.strftime('%Y-%m-%d')} đến {end_date.strftime('%Y-%m-%d')}...")
    mkt_leads = []
    
    source_configs = [
        {"names": ["Data chung"], "date": 1, "phone": 3, "source": 5, "channel": 6, "range": "A2:G"},
        {"names": ["DATA Cũ"], "date": 0, "phone": 1, "source": 2, "channel": 4, "range": "A2:G"},
        {"names": ["Trung tâm cột sống 2026", "TTCS 2026"], "date": 1, "phone": 3, "source": 5, "channel": 6, "range": "A2:G"},
        {"names": ["Trung tâm CXK 2026", "TTCXK 2026"], "date": 1, "phone": 3, "source": 5, "channel": 6, "range": "A2:G"},
        {"names": ["Trung tâm Thần kinh 2026", "TTTK 2026"], "date": 1, "phone": 3, "source": 5, "channel": 6, "range": "A2:G"}
    ]
    
    for config in source_configs:
        rows = None
        sheet_name_used = None
        for name in config["names"]:
            range_notation = f"'{name}'!{config['range']}"
            try:
                result = sheet_api.values().get(
                    spreadsheetId=config_ss_id,
                    range=range_notation,
                    valueRenderOption="UNFORMATTED_VALUE"
                ).execute()
                rows = result.get("values", [])
                sheet_name_used = name
                break
            except Exception:
                continue
                
        if rows is None:
            continue
            
        for row in rows:
            max_col = max(config["date"], config["phone"], config["source"], config["channel"])
            while len(row) <= max_col:
                row.append("")
                
            raw_date = row[config["date"]]
            row_time = get_timestamp(raw_date)
            if row_time == 0:
                continue
                
            row_dt = datetime.fromtimestamp(row_time)
            
            if start_date <= row_dt <= end_date:
                # Phân loại vùng miền dựa trên cột thành phố (mặc định index 4, trừ DATA Cũ là index 3)
                row_region = "MB"
                city_col = 3 if sheet_name_used == "DATA Cũ" else 4
                if len(row) > city_col:
                    city_str = str(row[city_col]).strip().lower()
                    for kw in ["hồ chí minh", "hcm", "sài gòn", "sg", "vũng tàu", "cần thơ", "đồng nai", "bình dương", "miền nam", "mn", "kiên giang", "long an", "an giang", "tiền giang"]:
                        if kw in city_str:
                            row_region = "MN"
                            break
                            
                if row_region == region:
                    phone_raw = str(row[config["phone"]]).strip()
                    phone_digits = "".join(c for c in phone_raw if c.isdigit())
                    if phone_digits.startswith("0"):
                        phone_digits = phone_digits[1:]
                        
                    source_val = row[config["source"]]
                    channel_val = row[config["channel"]]
                    
                    if phone_digits:
                        mkt_leads.append([phone_digits, source_val, channel_val])
                        
    print(f"✅ Đã lọc được {len(mkt_leads)} Marketing leads cho miền {region}.")
    return mkt_leads

def reconcile_data(rows, lookup_map):
    if len(rows) < 2:
        return rows, {}
        
    headers = rows[0]
    data_rows = rows[1:]
    
    ds_bac_si_chuuan = [
        "Đinh Trọng Tuyên", "Trần Sơn Tùng", "Nguyễn Lê Bảo Tiến", "Vũ Xuân Phước",
        "Kiều Đình Hùng", "Ngô Mạnh Hùng", "Phạm Duy", "Đỗ Vũ Anh", "Nguyễn Quốc Hùng",
        "Nguyễn Mộc Sơn", "Hoàng Ngọc Sơn", "Đỗ Văn Hải", "Tô Văn Quỳnh", "ĐỖ ANH VŨ",
        "TRẦN DẠ VƯƠNG", "DƯƠNG THANH TÙNG", "TRẦN LƯƠNG ANH", "VƯƠNG HỮU ĐỊNH",
        "HÀ VĂN TUẤN", "HOÀNG KHẮC XUÂN", "VÕ CHÂU DUYÊN", "PHẠM THẾ VŨ",
        "NGUYỄN MINH ĐỨC", "NGUYỄN KIM CHUNG", "NGUYỄN VĨNH KHANG", "VÕ VĂN SƠN",
        "NGUYỄN KIM NGÔI", "VÕ ĐĂNG SƠN", "NGÔ THỊ DIỆU MINH", "Nguyễn Xuân Trường", "Đinh Thị Thủy Lan"
    ]
    
    allowed_docs_special = ["Đinh Trọng Tuyên", "Kiều Đình Hùng", "Đỗ Vũ Anh"]
    
    patient_master_data = {}
    
    for row in data_rows:
        ma_bn = str(row[3]).strip() if row[3] is not None else "N/A"
        if not ma_bn:
            ma_bn = "N/A"
            
        if ma_bn not in patient_master_data:
            patient_master_data[ma_bn] = {
                "can_update": False,
                "is_re_exam": False,
                "final_source": "",
                "final_doctor": "",
                "is_google": False
            }
            
        # Ưu tiên điền bác sĩ chỉ định nội bộ (AC/AE -> AD)
        std_ac = standardize_doctor(row[28], ds_bac_si_chuuan)
        std_ad = standardize_doctor(row[29], ds_bac_si_chuuan)
        std_ae = standardize_doctor(row[30], ds_bac_si_chuuan)
        
        if not std_ad:
            if std_ae:
                std_ad = std_ae
            elif std_ac:
                std_ad = std_ac
                
        if not patient_master_data[ma_bn]["final_doctor"] and std_ad:
            patient_master_data[ma_bn]["final_doctor"] = std_ad
            
        col_b = str(row[1]).strip() if row[1] is not None else ""
        col_v = str(row[21]).strip() if row[21] is not None else ""
        col_i = str(row[8]).strip().lower() if row[8] is not None else ""
        col_w = str(row[22]).strip() if row[22] is not None else ""
        
        parsed_b = parse_date_only_str(col_b)
        parsed_v = parse_date_only_str(col_v)
        
        # Check tái khám: Mã hồ sơ (index 1) khác ID đăng ký lần đầu (index 21)
        is_re_exam = (parsed_b != "" and parsed_v != "" and parsed_b != parsed_v)
        has_special_service = ("cắt dây chằng" in col_i or "ngón tay" in col_i)
        if col_w.lower().startswith("tái khám -"):
            is_re_exam = True
            
        if is_re_exam:
            patient_master_data[ma_bn]["is_re_exam"] = True
            
        # Quyền cập nhật
        allow_update = (not is_re_exam) or (is_re_exam and has_special_service)
        
        # Check bảo vệ nguồn bác sĩ hợp tác
        if allow_update:
            is_coop_source = "Bs hợp tác: Bs ngoài Vietlife giới thiệu đến" in col_w
            is_friend_source = "Khách hàng/Bạn bè" in col_w
            
            if is_coop_source or is_friend_source:
                is_special_doc = False
                std_ad_current = patient_master_data[ma_bn]["final_doctor"]
                if std_ad_current:
                    for doc in allowed_docs_special:
                        if doc in std_ad_current:
                            is_special_doc = True
                            break
                if not is_special_doc:
                    allow_update = False
                    
        if allow_update:
            patient_master_data[ma_bn]["can_update"] = True
            
        # Tra cứu số điện thoại
        if allow_update:
            col_ac_raw = str(row[28]) if row[28] is not None else ""
            if "Bcare" in col_ac_raw or "Booking" in col_ac_raw:
                patient_master_data[ma_bn]["final_source"] = col_ac_raw
                
            phone_f = row[5]
            n_phone_f = normalize_phone(phone_f)
            
            if n_phone_f and n_phone_f in lookup_map:
                if not patient_master_data[ma_bn]["final_source"]:
                    patient_master_data[ma_bn]["final_source"] = lookup_map[n_phone_f]["source"]
                    
                final_src = patient_master_data[ma_bn]["final_source"]
                if final_src and str(final_src).strip().lower() == "google":
                    patient_master_data[ma_bn]["is_google"] = True
                    
                if not patient_master_data[ma_bn]["is_google"]:
                    target_channel = lookup_map[n_phone_f]["channel"]
                    std_channel = standardize_doctor(target_channel, ds_bac_si_chuuan)
                    if std_channel:
                        patient_master_data[ma_bn]["final_doctor"] = std_channel
                        
    backgrounds = {}
    for i, row in enumerate(data_rows):
        ma_bn = str(row[3]).strip() if row[3] is not None else "N/A"
        if not ma_bn:
            ma_bn = "N/A"
            
        master = patient_master_data.get(ma_bn)
        if not master:
            continue
            
        row_idx = i + 1  # 0-indexed row index including headers (headers is at index 0)
        
        # 1. Tô màu xám tái khám
        if master["is_re_exam"]:
            for j in range(33):
                backgrounds[(row_idx, j)] = "#D3D3D3"
                
        # 2. Cập nhật dữ liệu & tô màu vàng
        if master["can_update"]:
            if master["final_source"]:
                row[22] = master["final_source"]
                backgrounds[(row_idx, 22)] = "#FFFF00"
                
            if not master["is_google"] and master["final_doctor"]:
                row[28] = master["final_doctor"]
                row[29] = master["final_doctor"]
                row[30] = master["final_doctor"]
                
                backgrounds[(row_idx, 28)] = "#FFFF00"
                backgrounds[(row_idx, 29)] = "#FFFF00"
                backgrounds[(row_idx, 30)] = "#FFFF00"
                
    # Định dạng cột Ngày khám (index 0) và làm sạch SĐT (index 5) trước khi ghi ra Google Sheets
    for row in data_rows:
        row[0] = format_to_ddmmyyyy(row[0])
        row[5] = clean_phone_for_display(row[5])
        
    output_rows = [headers] + data_rows
    return output_rows, backgrounds

# =================================================================
# 💾 SAO CHÉP ĐỊNH DẠNG & GHI LÊN GOOGLE SHEET
# =================================================================

def get_sheet_id_by_title(sheet_api, spreadsheet_id, title):
    meta = sheet_api.get(spreadsheetId=spreadsheet_id).execute()
    for s in meta.get("sheets", []):
        if s["properties"]["title"] == title:
            return s["properties"]["sheetId"]
    return None

def delete_sheet_if_exists(sheet_api, spreadsheet_id, title):
    sheet_id = get_sheet_id_by_title(sheet_api, spreadsheet_id, title)
    if sheet_id is not None:
        print(f"🧹 Xóa Tab cũ '{title}'...")
        body = {
            "requests": [
                {
                    "deleteSheet": {
                        "sheetId": sheet_id
                    }
                }
            ]
        }
        sheet_api.batchUpdate(spreadsheetId=spreadsheet_id, body=body).execute()

def copy_template_and_rename(sheet_api, spreadsheet_id, template_sheet_id, new_title):
    print(f"➕ Sao chép định dạng từ tab 'Template' để tạo tab '{new_title}'...")
    body = {
        "destinationSpreadsheetId": spreadsheet_id
    }
    res = sheet_api.sheets().copyTo(
        spreadsheetId=spreadsheet_id,
        sheetId=template_sheet_id,
        body=body
    ).execute()
    
    copied_sheet_id = res["sheetId"]
    
    # Đổi tên và thiết lập kích thước
    body_update = {
        "requests": [
            {
                "updateSheetProperties": {
                    "properties": {
                        "sheetId": copied_sheet_id,
                        "title": new_title,
                        "gridProperties": {
                            "rowCount": 12000,
                            "columnCount": 45
                        }
                    },
                    "fields": "title,gridProperties.rowCount,gridProperties.columnCount"
                }
            }
        ]
    }
    sheet_api.batchUpdate(spreadsheetId=spreadsheet_id, body=body_update).execute()
    return copied_sheet_id

def write_sheet_values(sheet_api, spreadsheet_id, sheet_title, rows):
    body = {
        "values": [[str(cell) if cell is not None else "" for cell in row] for row in rows]
    }
    sheet_api.values().update(
        spreadsheetId=spreadsheet_id,
        range=f"'{sheet_title}'!A2",  # Bắt đầu viết từ A2 để giữ nguyên hàng tiêu đề của Template
        valueInputOption="RAW",
        body=body
    ).execute()

# Viết dữ liệu marketing và các công thức liên quan vào cột AH-AP
def write_marketing_leads_and_formulas(sheet_api, spreadsheet_id, sheet_title, mkt_leads):
    if not mkt_leads:
        print("ℹ️ Không có Marketing leads để ghi.")
        return
        
    mkt_rows = []
    for idx, lead in enumerate(mkt_leads):
        row_num = idx + 2  # Dữ liệu bắt đầu từ dòng 2
        # Cột AH (33), AI (34), AJ (35) ghi dữ liệu tĩnh. Cột AK-AP (36-41) ghi công thức.
        mkt_rows.append([
            lead[0],  # AH: Số điện thoại
            lead[1],  # AI: Kênh MKT
            lead[2],  # AJ: Bác sĩ MKT
            f"=vlookup(AH{row_num};F:AD;18;0)",  # AK: Nguồn micom (vlookup cột 18)
            f"=vlookup(AH{row_num};F:AD;25;0)",  # AL: BS bổ sung (vlookup cột 25)
            f"=countif(F:F;AH{row_num})",        # AM: Tổng số xuất hiện
            f"=countifs(F:F;AH{row_num};W:W;AK{row_num})",
            f"=countifs(F:F;AH{row_num};AD:AD;AL{row_num})",
            f"=if(AM{row_num}<>AO{row_num};\"check\";\"\")" # AP: Trạng thái check
        ])
        
    body = {
        "values": mkt_rows
    }
    # Ghi vào cột AH (cột thứ 34, tức index 33) từ dòng 2
    sheet_api.values().update(
        spreadsheetId=spreadsheet_id,
        range=f"'{sheet_title}'!AH2:AP{len(mkt_leads) + 1}",
        valueInputOption="USER_ENTERED",  # Cần thiết để Google Sheet tự động biên dịch công thức
        body=body
    ).execute()

def write_sheet_formatting(sheet_api, spreadsheet_id, sheet_id, num_rows, num_cols, backgrounds):
    if not backgrounds:
        return
        
    def hex_to_rgb(hex_str):
        hex_str = hex_str.lstrip('#')
        return {
            "red": int(hex_str[0:2], 16) / 255.0,
            "green": int(hex_str[2:4], 16) / 255.0,
            "blue": int(hex_str[4:6], 16) / 255.0
        }
        
    row_data_list = []
    # Lưu ý: dữ liệu chính bắt đầu viết từ hàng 2 (dòng index 1), hàng 1 là tiêu đề đã có định dạng sẵn của Template
    for r in range(num_rows):
        values = []
        for c in range(num_cols):
            color = backgrounds.get((r + 1, c)) # backgrounds tính cả header, nhưng ở đây r bắt đầu từ 0
            if color:
                rgb = hex_to_rgb(color)
                cell_format = {
                    "userEnteredFormat": {
                        "backgroundColor": rgb
                    }
                }
                values.append(cell_format)
            else:
                values.append({})
        row_data_list.append({"values": values})
        
    request = {
        "updateCells": {
            "rows": row_data_list,
            "fields": "userEnteredFormat.backgroundColor",
            "range": {
                "sheetId": sheet_id,
                "startRowIndex": 1,  # Bắt đầu tô màu từ dòng 2 (hàng index 1)
                "endRowIndex": num_rows + 1,
                "startColumnIndex": 0,
                "endColumnIndex": num_cols
            }
        }
    }
    
    body = {"requests": [request]}
    sheet_api.batchUpdate(spreadsheetId=spreadsheet_id, body=body).execute()

# =================================================================
# 📂 ĐỌC & GỘP FILE EXCEL
# =================================================================

def extract_timeframe(folder_path, file_map):
    pattern = r"(\d{1,2}(?:-\d{1,2})?\s*[_ -]?\s*[a-zA-Z]{3,4}(?:\d{2,4})?)"
    
    for key, fp in file_map.items():
        if fp:
            fname = os.path.basename(fp)
            match = re.search(pattern, fname)
            if match:
                return match.group(1).replace("_", "").replace(" ", "")
                
    folder_name = os.path.basename(os.path.normpath(folder_path))
    match = re.search(pattern, folder_name)
    if match:
        return match.group(1).replace("_", "").replace(" ", "")
        
    return "Recent"

def is_summary_or_footer_row(row):
    if not row:
        return True
    # Duyệt qua các ô đầu tiên của dòng để check chữ cộng, tổng, người lập...
    for cell in row[:10]:
        val_str = str(cell).strip().lower()
        if any(kw in val_str for kw in ["cộng", "tổng", "bằng chữ", "người lập", "người duyệt", "giám đốc"]):
            return True
    
    # Check trường hợp dòng trống thông tin chính nhưng chứa chữ cộng/tổng ở cột khác
    col_0_empty = not str(row[0]).strip() if len(row) > 0 else True
    col_1_empty = not str(row[1]).strip() if len(row) > 1 else True
    col_4_empty = not str(row[4]).strip() if len(row) > 4 else True
    if col_0_empty and col_1_empty and col_4_empty:
        row_str = " ".join(str(c) for c in row if c).lower()
        if "cộng" in row_str or "tổng" in row_str:
            return True
    return False

def read_and_merge(file_paths):
    merged_rows = []
    headers = None
    
    for fp in file_paths:
        if not fp or not os.path.exists(fp):
            continue
        try:
            print(f"📖 Đang đọc dữ liệu từ file Excel: {fp}...")
            df = pd.read_excel(fp, header=None, engine="openpyxl")
            rows = df.fillna("").values.tolist()
            if not rows:
                continue
            
            # Tự động tìm dòng chứa tiêu đề chuẩn (bỏ qua các dòng trống hoặc nhãn phụ)
            header_row_idx = 0
            for idx in range(min(5, len(rows))):
                first_cell = str(rows[idx][0]).strip().lower()
                if "ngày khám" in first_cell or "ngay kham" in first_cell:
                    header_row_idx = idx
                    break
                    
            print(f"  - Phát hiện dòng tiêu đề ở dòng index: {header_row_idx}")
            
            file_headers = rows[header_row_idx]
            file_data = rows[header_row_idx + 1:]
            
            if headers is None:
                headers = file_headers
                headers_padded = list(headers)
                while len(headers_padded) < 33:
                    headers_padded.append("")
                headers_padded = headers_padded[:33]
                merged_rows.append(headers_padded)
                
            for r in file_data:
                # Loại bỏ dòng tổng cộng / footer
                if is_summary_or_footer_row(r):
                    continue
                padded_r = list(r)
                while len(padded_r) < 33:
                    padded_r.append("")
                padded_r = padded_r[:33]
                merged_rows.append(padded_r)
        except Exception as e:
            print(f"❌ Lỗi khi đọc file Excel {fp}: {e}")
            
    return merged_rows

# =================================================================
# 🚀 MAIN FLOW
# =================================================================

def main():
    parser = argparse.ArgumentParser(description="Gộp file Excel & Đối soát V12 dữ liệu Vietlife")
    parser.add_argument("folder_path", type=str, help="Đường dẫn đến thư mục chứa 4 file Excel (SVH, NCT, LTN, TBT)")
    parser.add_argument("--spreadsheet-id", type=str, default="1BIMzw4aUhrvOFbKZsj3s4Zu6n2qb_MFI9qakt9DDsec", help="Spreadsheet ID của Google Sheets đối soát")
    parser.add_argument("--config-spreadsheet-id", type=str, default="1LOqw99AqWKh89BUdOgRdhZq5vN7jajVRuJ25mgqUDOQ", help="Spreadsheet ID chứa dữ liệu cấu hình đối soát")
    parser.add_argument("--credentials", type=str, default=None, help="Đường dẫn tới file Service Account JSON (Xác thực)")
    parser.add_argument("--token", type=str, default=None, help="Google API Access Token để xác thực trực tiếp")
    parser.add_argument("--timeframe", type=str, default=None, help="Tùy chỉnh khoảng thời gian (Ví dụ: 13-19Jun)")
    
    args = parser.parse_args()
    
    folder = args.folder_path
    if not os.path.exists(folder):
        print(f"❌ Thư mục không tồn tại: {folder}")
        sys.exit(1)
        
    print(f"🔍 Quét thư mục: {folder}")
    files = os.listdir(folder)
    excel_files = [f for f in files if f.endswith(('.xlsx', '.xls'))]
    
    file_map = {"SVH": None, "NCT": None, "LTN": None, "TBT": None}
    for f in excel_files:
        name_upper = f.upper()
        if "SVH" in name_upper:
            file_map["SVH"] = os.path.join(folder, f)
        elif "NCT" in name_upper:
            file_map["NCT"] = os.path.join(folder, f)
        elif "LTN" in name_upper:
            file_map["LTN"] = os.path.join(folder, f)
        elif "TBT" in name_upper:
            file_map["TBT"] = os.path.join(folder, f)
            
    print("\n📋 Báo cáo quét tệp tin nguồn:")
    for k, v in file_map.items():
        status = f"Tìm thấy ({os.path.basename(v)})" if v else "❌ KHÔNG TÌM THẤY"
        print(f"  - {k}: {status}")
        
    timeframe = args.timeframe
    if not timeframe:
        timeframe = extract_timeframe(folder, file_map)
    print(f"📅 Khoảng thời gian (timeframe) được chọn: {timeframe}")
    
    # Phân tích ngày bắt đầu / kết thúc tuần đối soát
    start_date, end_date = parse_timeframe_dates(timeframe)
    if start_date and end_date:
        print(f"📅 Khoảng ngày đối soát: {start_date.strftime('%Y-%m-%d')} -> {end_date.strftime('%Y-%m-%d')}")
    else:
        print("⚠️ Cảnh báo: Không thể xác định dải ngày từ timeframe. Sẽ không lọc được leads MKT theo tuần!")
        
    groups = {
        "MN": [file_map["SVH"], file_map["NCT"]],
        "MB": [file_map["LTN"], file_map["TBT"]]
    }
    
    # Xác thực Google Sheets API
    try:
        service = get_sheets_service(args.credentials, args.token)
        sheet_api = service.spreadsheets()
    except Exception as e:
        print(f"❌ Không thể khởi tạo kết nối Google Sheets API: {e}")
        sys.exit(1)
        
    # Lấy ID của tab Template
    template_sheet_id = get_sheet_id_by_title(sheet_api, args.spreadsheet_id, "Template")
    if template_sheet_id is None:
        print("❌ Lỗi: Không tìm thấy tab 'Template' trong bảng tính đối soát mục tiêu!")
        sys.exit(1)
        
    # Tạo Lookup Map từ các sheet cấu hình
    lookup_map = build_lookup_map(sheet_api, args.config_spreadsheet_id)
    
    for region, paths in groups.items():
        valid_paths = [p for p in paths if p is not None]
        if not valid_paths:
            print(f"\n⚠️ Bỏ qua miền {region} vì không có file Excel hợp lệ.")
            continue
            
        print(f"\n==================================================")
        print(f"🚀 BẮT ĐẦU XỬ LÝ MIỀN {region} ({timeframe})")
        print(f"==================================================")
        
        # 1. Đọc và gộp file Excel (skipping Row 0 label)
        merged_rows = read_and_merge(valid_paths)
        if len(merged_rows) < 2:
            print(f"⚠️ Không có dữ liệu để xử lý cho miền {region}.")
            continue
            
        print(f"✅ Gộp thành công {len(merged_rows) - 1} dòng dữ liệu bệnh viện.")
        
        # 2. Chạy logic đối soát V12 cho dữ liệu bệnh viện (A-AG)
        print("⏳ Đang đối soát và xử lý logic V12 cho dữ liệu bệnh viện...")
        reconciled_rows, backgrounds = reconcile_data(merged_rows, lookup_map)
        
        # 3. Tạo dữ liệu Marketing leads bằng cách đối chiếu SĐT bệnh viện (cột F) với Lookup Map cấu hình
        mkt_leads = []
        seen_phones = set()
        for row in reconciled_rows[1:]:
            phone_raw = row[5] # Cột Số điện thoại bệnh nhân (index 5)
            phone_norm = normalize_phone(phone_raw)
            if phone_norm and phone_norm not in seen_phones:
                seen_phones.add(phone_norm)
                if phone_norm in lookup_map:
                    source_val = lookup_map[phone_norm]["source"]
                    channel_val = lookup_map[phone_norm]["channel"]
                    mkt_leads.append([phone_norm, source_val, channel_val])
            
        # 4. Sao chép định dạng Template và ghi dữ liệu lên Google Sheet
        sheet_title = f"{region} {timeframe}"
        
        # Thêm dấu cách giữa vùng miền và dải ngày giống như template (e.g. MB 13-19 Jun thay vì MB 13-19Jun)
        space_timeframe = timeframe
        match_space = re.search(r"(\d+)-(\d+)([a-zA-Z]+)", timeframe)
        if match_space:
            space_timeframe = f"{match_space.group(1)}-{match_space.group(2)} {match_space.group(3)}"
        sheet_title = f"{region} {space_timeframe}"
        
        try:
            # Xóa tab cũ nếu có
            delete_sheet_if_exists(sheet_api, args.spreadsheet_id, sheet_title)
            
            # Copy template mới
            sheet_id = copy_template_and_rename(sheet_api, args.spreadsheet_id, template_sheet_id, sheet_title)
            
            # Ghi dữ liệu chính (bỏ hàng tiêu đề ra vì đã có sẵn từ template, ghi từ dòng 2)
            data_to_write = reconciled_rows[1:]
            print(f"💾 Đang ghi {len(data_to_write)} dòng dữ liệu bệnh viện vào cột A-AG...")
            write_sheet_values(sheet_api, args.spreadsheet_id, sheet_title, data_to_write)
            
            # Ghi dữ liệu MKT và công thức (AH-AP)
            if mkt_leads:
                print(f"💾 Đang ghi {len(mkt_leads)} dòng dữ liệu marketing và các công thức đối soát vào cột AH-AP...")
                write_marketing_leads_and_formulas(sheet_api, args.spreadsheet_id, sheet_title, mkt_leads)
                
            # Tô màu nền dòng tái khám và ô cập nhật đối soát
            if backgrounds:
                num_rows_to_color = len(data_to_write)
                print(f"🎨 Đang tô màu nền ({len(backgrounds)} ô)...")
                write_sheet_formatting(sheet_api, args.spreadsheet_id, sheet_id, num_rows_to_color, 33, backgrounds)
                
            print(f"🎉 HOÀN THÀNH: Đã đối soát và đẩy dữ liệu lên tab '{sheet_title}' thành công!")
        except Exception as e:
            print(f"❌ Gặp lỗi khi ghi dữ liệu lên Google Sheet: {e}")
            
    print("\n🌟 Toàn bộ quy trình hoàn tất!")

if __name__ == "__main__":
    main()
