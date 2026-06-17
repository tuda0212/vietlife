import sys
import os
import logging

# Thêm thư mục 'files' vào sys.path để import sheets_reader
workspace_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
files_dir = os.path.join(workspace_dir, "files")
sys.path.append(files_dir)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("inspect_new_sheet")

from sheets_reader import _get_sheets_service

NEW_SHEET_ID = "15We9-LwI9yOF7Z951YAHKxzPF7X5-lx3DZ5Z7Rtw5jg"

def inspect():
    service = _get_sheets_service()
    sheet_api = service.spreadsheets()
    
    print(f"\n==================================================")
    print(f"Inspecting Unified CRM Sheet: {NEW_SHEET_ID}")
    try:
        meta = sheet_api.get(spreadsheetId=NEW_SHEET_ID).execute()
        print(f"Spreadsheet Title: {meta['properties']['title']}")
        for s in meta['sheets']:
            title = s['properties']['title']
            grid = s['properties']['gridProperties']
            print(f"\n  - Tab: '{title}' (rows={grid.get('rowCount')}, cols={grid.get('columnCount')})")
            
            # Fetch first 2 rows (headers & sample)
            try:
                result = sheet_api.values().get(
                    spreadsheetId=NEW_SHEET_ID,
                    range=f"'{title}'!A1:Z3",
                    valueRenderOption="FORMATTED_VALUE"
                ).execute()
                vals = result.get("values", [])
                if vals:
                    print(f"    Header: {vals[0]}")
                    for i, row in enumerate(vals[1:], start=1):
                        print(f"    Sample Row {i}: {row}")
            except Exception as e_sheet:
                print(f"    Error reading data: {e_sheet}")
    except Exception as e:
        print(f"Error inspecting spreadsheet: {e}")

if __name__ == "__main__":
    inspect()
