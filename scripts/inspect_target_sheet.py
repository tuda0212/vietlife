import os
import sys
import logging
from pathlib import Path

# Load env variables
workspace_root = Path(__file__).resolve().parent.parent
env_file = workspace_root / ".env"
if env_file.exists():
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                os.environ.setdefault(key.strip(), value.strip())

# Add files to path
workspace_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
files_dir = os.path.join(workspace_dir, "files")
sys.path.append(files_dir)

from sheets_reader import _get_sheets_service

logging.basicConfig(level=logging.INFO)

def main():
    spreadsheet_id = "10sWUCv1uYk5X2CKfcwOqbd5K3JXjPmty00yb9IJkK0c"
    
    service = _get_sheets_service()
    sheet_api = service.spreadsheets()
    
    print("Fetching spreadsheet metadata...")
    meta = sheet_api.get(spreadsheetId=spreadsheet_id).execute()
    
    print("\nAvailable sheets in spreadsheet:")
    for sheet in meta.get("sheets", []):
        props = sheet.get("properties", {})
        print(f"- {props.get('title')} (id: {props.get('sheetId')})")
    return
            
    if not target_sheet_title:
        print(f"Could not find sheet with gid {target_gid}. Available sheets:")
        for sheet in meta.get("sheets", []):
            props = sheet.get("properties", {})
            print(f"- {props.get('title')} (id: {props.get('sheetId')})")
        return
        
    # Read first 5 rows to see structure
    range_notation = f"'{target_sheet_title}'!A1:Z5"
    result = sheet_api.values().get(
        spreadsheetId=spreadsheet_id,
        range=range_notation
    ).execute()
    
    print("Raw API result:", result)
    values = result.get("values", [])
    print(f"\nFirst 5 rows of sheet '{target_sheet_title}':")
    for idx, row in enumerate(values):
        print(f"Row {idx+1}: {row}")

if __name__ == "__main__":
    main()
