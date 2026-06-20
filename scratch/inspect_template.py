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
    tab_name = "Template"
    
    # Đọc tiêu đề và dòng đầu tiên
    result = sheet_api.values().get(
        spreadsheetId=spreadsheet_id,
        range=f"'{tab_name}'!A1:AZ5",
        valueRenderOption="FORMULA"
    ).execute()
    
    values = result.get("values", [])
    print(f"Tổng số dòng trong Template A1:AZ5: {len(values)}")
    for idx, row in enumerate(values):
        print(f"Dòng {idx+1}: {row[:45]}")

if __name__ == "__main__":
    main()
