import sys
if sys.platform.startswith('win'):
    sys.stdout.reconfigure(encoding='utf-8')

from googleapiclient.discovery import build
from google.oauth2 import service_account

def main():
    creds = service_account.Credentials.from_service_account_file(
        "google-credentials.json",
        scopes=["https://www.googleapis.com/auth/spreadsheets"]
    )
    service = build("sheets", "v4", credentials=creds)
    sheet_api = service.spreadsheets()
    
    spreadsheet_id = "15We9-LwI9yOF7Z951YAHKxzPF7X5-lx3DZ5Z7Rtw5jg"
    
    for name in ["TTCS 2026", "TTCXK 2026", "TTTK 2026", "DATA Cũ"]:
        try:
            result = sheet_api.values().get(
                spreadsheetId=spreadsheet_id,
                range=f"'{name}'!A2:G"
            ).execute()
            rows = result.get("values", [])
            hcm_count = 0
            for r in rows:
                if len(r) > 4:
                    val_str = str(r[4]).lower()
                    if 'hồ chí minh' in val_str or 'hcm' in val_str or 'sài gòn' in val_str or 'sg' in val_str:
                        hcm_count += 1
            print(f"[{name}] Số dòng HCM: {hcm_count} / {len(rows)} tổng số dòng")
        except Exception as e:
            print(f"Lỗi đọc {name}: {e}")

if __name__ == "__main__":
    main()
