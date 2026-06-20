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
    
    # Đọc giá trị và công thức của dòng 5 (dòng dữ liệu đầu tiên)
    result = sheet_api.values().get(
        spreadsheetId=spreadsheet_id,
        range=f"'{tab_name}'!AH1:AP10",
        valueRenderOption="FORMULA"
    ).execute()
    
    values = result.get("values", [])
    print(f"Số dòng đọc được từ cột AH (33): {len(values)}")
    for idx, row in enumerate(values):
        print(f"Dòng {idx+1}: {row}")

if __name__ == "__main__":
    main()
