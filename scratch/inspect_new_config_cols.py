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
    
    spreadsheet_id = "1LOqw99AqWKh89BUdOgRdhZq5vN7jajVRuJ25mgqUDOQ"
    
    for name in ["MKT TH", "MKT TH2", "Data chung", "Trung tâm cột sống 2026"]:
        try:
            result = sheet_api.values().get(
                spreadsheetId=spreadsheet_id,
                range=f"'{name}'!A1:H2",
                valueRenderOption="FORMATTED_VALUE"
            ).execute()
            values = result.get("values", [])
            print(f"\n==================== {name} ====================")
            if values:
                print("Headers:", values[0])
                if len(values) > 1:
                    print("Sample row:", values[1])
            else:
                print("Empty sheet")
        except Exception as e:
            print(f"Lỗi đọc {name}: {e}")

if __name__ == "__main__":
    main()
