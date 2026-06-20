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
        range=f"'{tab_name}'!A1:AP15",
        valueRenderOption="FORMATTED_VALUE"
    ).execute()
    
    values = result.get("values", [])
    if not values:
        print("Không có dữ liệu!")
        return
        
    print(f"{'Dòng':<6} | {'SĐT (Col F)':<12} | {'Mã BN':<13} | {'Nguồn (Col W)':<20} | {'BS Chỉ định (AD)':<18} | {'SĐT MKT (AH)':<12} | {'Kênh (AI)':<10} | {'BS MKT (AJ)':<15}")
    print("-" * 115)
    for idx, row in enumerate(values[1:], start=2):
        # Pad row
        while len(row) < 38:
            row.append("")
        print(f"Row {idx:<2} | {row[5]:<12} | {row[3]:<13} | {row[22]:<20} | {row[29]:<18} | {row[33]:<12} | {row[34]:<10} | {row[35]:<15}")

if __name__ == "__main__":
    main()
