import logging
from google.auth import default as google_auth_default
from googleapiclient.discovery import build
import os
import re
from datetime import datetime, timedelta

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("analyze_invalid")

# os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "/Users/daudau/.gemini/antigravity-ide/scratch/files/temp_sa_key.json"

SHEETS_TO_INSPECT = {
    "BS Tuyên": "1zEeuhBDiExB2cokMZlbWdqrcnoV9WjmwTin_Pssv3mM",
    "BS Kiều Đình Hùng": "1qqrBGbsxCemcYol3EEGo6DplnhOMsBewKEElVS3ERJQ"
}

def serial_to_date(serial) -> str:
    try:
        serial_num = float(serial)
        base_date = datetime(1899, 12, 30)
        delta = timedelta(days=serial_num)
        return (base_date + delta).strftime("%Y-%m-%d")
    except Exception:
        return ""

def parse_date(date_val) -> str:
    if not date_val:
        return ""
    val_str = str(date_val).strip()
    date_from_serial = serial_to_date(val_str)
    if date_from_serial:
        return date_from_serial
    if re.match(r"^\d{4}-\d{2}-\d{2}$", val_str):
        return val_str
    m = re.match(r"^(\d{1,2})/(\d{1,2})/(\d{4})$", val_str)
    if m:
        return f"{m.group(3)}-{m.group(2).zfill(2)}-{m.group(1).zfill(2)}"
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"):
        try:
            return datetime.strptime(val_str, fmt).strftime("%Y-%m-%d")
        except ValueError:
            pass
    return ""

def normalize_ad_id(value) -> str:
    if not value:
        return ""
    text = str(value).strip().lstrip("'")
    nums = re.findall(r"\d{6,}", text)
    return nums[0] if nums else ""

def analyze():
    credentials, _ = google_auth_default(
        scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"]
    )
    service = build("sheets", "v4", credentials=credentials, cache_discovery=False)
    
    for name, sheet_id in SHEETS_TO_INSPECT.items():
        print(f"\n====== Analyzing {name} ======")
        meta = service.spreadsheets().get(spreadsheetId=sheet_id).execute()
        first_sheet = meta["sheets"][0]["properties"]["title"]
        grid = meta["sheets"][0]["properties"]["gridProperties"]
        total_rows = grid.get("rowCount", 0)
        
        range_name = f"'{first_sheet}'!A1:N{total_rows}"
        result = service.spreadsheets().values().get(
            spreadsheetId=sheet_id,
            range=range_name,
            valueRenderOption="UNFORMATTED_VALUE"
        ).execute()
        
        values = result.get("values", [])
        total = len(values)
        
        empty_rows = 0
        before_range = 0
        within_range = 0
        after_range = 0
        invalid_date = 0
        missing_ad_id = 0
        valid_rows = 0
        
        start_date = "2025-08-12"
        end_date = "2026-06-12"
        
        for idx, row in enumerate(values[1:], start=2):
            while len(row) < 14:
                row.append("")
                
            psid = str(row[0]).strip()
            phone_raw = str(row[3]).strip() or str(row[4]).strip() or str(row[10]).strip()
            ad_id_raw = str(row[6]).strip() or str(row[13]).strip()
            date_raw = str(row[7]).strip()
            
            if not any(str(x).strip() for x in row):
                empty_rows += 1
                continue
                
            if not date_raw:
                month_val = str(row[8]).strip()
                day_val = str(row[9]).strip()
                if parse_date(day_val):
                    date_raw = day_val
                elif month_val and day_val:
                    date_raw = f"2026-{month_val.zfill(2)}-{day_val.zfill(2)}"
            
            lead_date = parse_date(date_raw)
            ad_id = normalize_ad_id(ad_id_raw)
            
            if not lead_date:
                invalid_date += 1
                continue
                
            if lead_date < start_date:
                before_range += 1
            elif lead_date > end_date:
                after_range += 1
            else:
                within_range += 1
                valid_rows += 1
                
        print(f"Total Rows: {total}")
        print(f"Empty rows: {empty_rows}")
        print(f"Invalid date format: {invalid_date}")
        print(f"Before range (< {start_date}): {before_range}")
        print(f"Within range ({start_date} -> {end_date}): {within_range}")
        print(f"After range (> {end_date}): {after_range}")
        print(f"Valid rows matching sync: {valid_rows}")

if __name__ == "__main__":
    analyze()
