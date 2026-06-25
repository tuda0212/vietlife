import sys
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

def main():
    token = sys.argv[1]
    spreadsheet_id = "10sWUCv1uYk5X2CKfcwOqbd5K3JXjPmty00yb9IJkK0c"
    
    credentials = Credentials(token)
    service = build("sheets", "v4", credentials=credentials, cache_discovery=False)
    
    meta = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
    
    with open("e:\\vietlife\\temp_setup\\sheets_list.txt", "w", encoding="utf-8") as f:
        f.write("=== DANH SACH TAB NAMES ===\n")
        for sheet in meta.get("sheets", []):
            props = sheet.get("properties", {})
            f.write(f"Title: {props.get('title')}, Gid: {props.get('sheetId')}\n")

if __name__ == "__main__":
    main()
