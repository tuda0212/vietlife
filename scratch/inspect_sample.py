import json
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
    
    spreadsheet_id = "1BIMzw4aUhrvOFbKZsj3s4Zu6n2qb_MFI9qakt9DDsec"
    tab_name = "MB 08-14 Jun"
    
    # Đọc 5 dòng đầu
    result = sheet_api.values().get(
        spreadsheetId=spreadsheet_id,
        range=f"'{tab_name}'!A1:AZ5",
        valueRenderOption="FORMATTED_VALUE"
    ).execute()
    
    values = result.get("values", [])
    if not values:
        print("Không tìm thấy dữ liệu!")
        return
        
    print(f"Tổng số cột: {len(values[0])}")
    print("\n--- TIÊU ĐỀ CÁC CỘT (0-indexed) ---")
    for idx, header in enumerate(values[0]):
        print(f"Index {idx}: {header}")
        
    print("\n--- DÒNG DỮ LIỆU MẪU 1 ---")
    if len(values) > 1:
        print(values[1])
        
if __name__ == "__main__":
    main()
