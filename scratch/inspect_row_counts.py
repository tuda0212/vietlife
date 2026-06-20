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
    
    result = sheet_api.values().get(
        spreadsheetId=spreadsheet_id,
        range=f"'{tab_name}'!A1:AP10000",
        valueRenderOption="FORMATTED_VALUE"
    ).execute()
    
    values = result.get("values", [])
    if not values:
        print("Không có dữ liệu!")
        return
        
    total_rows = len(values)
    non_empty_col_a = sum(1 for r in values if len(r) > 0 and r[0] != "")
    non_empty_col_f = sum(1 for r in values if len(r) > 5 and r[5] != "")
    non_empty_col_ah = sum(1 for r in values if len(r) > 33 and r[33] != "")
    
    print(f"Tổng số dòng đọc được: {total_rows}")
    print(f"Số dòng có dữ liệu cột A (Ngày khám): {non_empty_col_a}")
    print(f"Số dòng có dữ liệu cột F (SĐT chính): {non_empty_col_f}")
    print(f"Số dòng có dữ liệu cột AH (SĐT MKT): {non_empty_col_ah}")

if __name__ == "__main__":
    main()
