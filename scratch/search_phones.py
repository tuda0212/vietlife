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
    phones_to_search = ["979765169", "904228357"]
    
    source_configs = [
        {"name": "DATA Cũ", "date": 0, "phone": 1, "source": 2, "channel": 4, "range": "A2:E"},
        {"name": "TTCS 2026", "date": 1, "phone": 3, "source": 5, "channel": 6, "range": "A2:G"},
        {"name": "TTCXK 2026", "date": 1, "phone": 3, "source": 5, "channel": 6, "range": "A2:G"},
        {"name": "TTTK 2026", "date": 1, "phone": 3, "source": 5, "channel": 6, "range": "A2:G"}
    ]
    
    for config in source_configs:
        name = config["name"]
        range_notation = f"'{name}'!{config['range']}"
        try:
            result = sheet_api.values().get(
                spreadsheetId=spreadsheet_id,
                range=range_notation,
                valueRenderOption="UNFORMATTED_VALUE"
            ).execute()
            rows = result.get("values", [])
            for idx, row in enumerate(rows, start=2):
                row_str = str(row)
                for phone in phones_to_search:
                    if phone in row_str:
                        print(f"[{name}] Dòng {idx}: {row}")
        except Exception as e:
            print(f"Lỗi đọc {name}: {e}")

if __name__ == "__main__":
    main()
