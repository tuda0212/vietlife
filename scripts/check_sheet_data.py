import sys
import os
import logging
from datetime import datetime

# Thêm thư mục 'files' vào sys.path để import sheets_reader
workspace_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
files_dir = os.path.join(workspace_dir, "files")
sys.path.append(files_dir)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("check_sheet")

from sheets_reader import _get_sheets_service, parse_date_robust, normalize_phone, is_booking_status, normalize_status_text, normalize_ad_id
from config_crm import CENTER_CRM_SHEETS, DOCTOR_SHEETS, DOCTOR_METADATA
from crm_pipeline import _map_channel_to_doctor_meta

def main():
    service = _get_sheets_service()
    sheet_api = service.spreadsheets()
    
    # Cấu hình của TTCXK_2026
    cfg = CENTER_CRM_SHEETS["TTCXK_2026"]
    spreadsheet_id = cfg["spreadsheet_id"]
    main_tab = cfg["main_tab"]
    arrival_tab = cfg["arrival_tab"]
    
    # 1. Đọc tab đến cửa để map SĐT
    arrival_map = {}
    try:
        header_res = sheet_api.values().get(
            spreadsheetId=spreadsheet_id,
            range=f"'{arrival_tab}'!A1:Z1",
            valueRenderOption="UNFORMATTED_VALUE"
        ).execute()
        headers = [str(h).strip().lower() for h in header_res.get("values", [[]])[0]]
        
        phone_idx = 2  # Cột C cho sheet mới
        rev_idx = 3    # Cột D cho sheet mới
        
        # Tìm cột động
        for idx, h in enumerate(headers):
            if "so_dien_thoai" in h or "so dien thoai" in h or "sdt" in h:
                phone_idx = idx
            elif "thanh_tien" in h or "thanh tien" in h or "doanh thu" in h:
                rev_idx = idx
                
        result = sheet_api.values().get(
            spreadsheetId=spreadsheet_id,
            range=f"'{arrival_tab}'!A2:Z10000",
            valueRenderOption="UNFORMATTED_VALUE"
        ).execute()
        values = result.get("values", [])
        for row in values:
            while len(row) <= max(phone_idx, rev_idx):
                row.append("")
            phone_raw = str(row[phone_idx]).strip()
            phone = normalize_phone(phone_raw)
            if not phone:
                continue
            
            rev_raw = str(row[rev_idx]).strip() if row[rev_idx] is not None else "0"
            rev_clean = rev_raw.replace(".", "").replace(",", "")
            try:
                revenue = float(rev_clean)
            except ValueError:
                revenue = 0.0
                
            if phone in arrival_map:
                arrival_map[phone]["revenue"] += revenue
            else:
                arrival_map[phone] = {
                    "revenue": revenue,
                    "is_arrival": True
                }
    except Exception as e:
        print("Lỗi đọc tab đến cửa:", e)
        return

    # 2. Đọc tab chính TTCXK 2026
    print("\n--- Đếm số liệu trực tiếp từ Google Sheet cho tháng 3/2026 ---")
    try:
        result = sheet_api.values().get(
            spreadsheetId=spreadsheet_id,
            range=f"'{main_tab}'!A2:M10000",
            valueRenderOption="UNFORMATTED_VALUE"
        ).execute()
        values = result.get("values", [])
        
        total_leads = 0
        vu_anh_leads = 0
        vu_anh_booking = 0
        vu_anh_arrival = 0
        vu_anh_revenue = 0.0
        
        for idx, row in enumerate(values, start=2):
            while len(row) < 13:
                row.append("")
                
            date_raw = str(row[1]).strip()
            phone_raw = str(row[3]).strip()
            channel = str(row[6]).strip()
            booking_val = row[12] # Cột M
            
            lead_date = parse_date_robust(date_raw)
            phone = normalize_phone(phone_raw)
            
            if not lead_date or not phone:
                continue
                
            # Chỉ lọc tháng 3 năm 2026
            if not lead_date.startswith("2026-03"):
                continue
                
            total_leads += 1
            
            # Khớp tên bác sĩ
            meta_doc = _map_channel_to_doctor_meta(channel, "CXK")
            doc_name = meta_doc["doctor_name"] if meta_doc else ""
            
            if doc_name == "BS Vũ Anh":
                vu_anh_leads += 1
                is_booking = is_booking_status(booking_val)
                if is_booking:
                    vu_anh_booking += 1
                    
                arr_info = arrival_map.get(phone, {"revenue": 0.0, "is_arrival": False})
                if arr_info["is_arrival"]:
                    vu_anh_arrival += 1
                    vu_anh_revenue += arr_info["revenue"]
                    
        print(f"Tổng số lead tháng 3/2026 trên sheet: {total_leads}")
        print(f"Bác sĩ Vũ Anh:")
        print(f"  - Số leads: {vu_anh_leads}")
        print(f"  - Số đặt lịch: {vu_anh_booking}")
        print(f"  - Số đến cửa: {vu_anh_arrival}")
        print(f"  - Doanh thu: {vu_anh_revenue:,.0f} đ")
        
    except Exception as e:
        print("Lỗi đọc tab chính:", e)

if __name__ == "__main__":
    main()
