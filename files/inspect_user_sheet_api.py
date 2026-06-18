import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sheets_reader import _get_sheets_service

def main():
    sheet_id = "1guUru-qTB6Pug4Oc43fqoEw3UUVmFXs2R7MAUr3AIGY"
    print(f"Connecting to Google Sheets API for spreadsheet: {sheet_id}")
    try:
        service = _get_sheets_service()
        sheet_api = service.spreadsheets()
        
        # Lấy metadata
        meta = sheet_api.get(spreadsheetId=sheet_id).execute()
        print("Spreadsheet Title:", meta.get("properties", {}).get("title"))
        sheets = meta.get("sheets", [])
        print("Sheets in this spreadsheet:")
        for s in sheets:
            props = s.get("properties", {})
            print(f" - Title: {props.get('title')}, GID: {props.get('sheetId')}, Grid: {props.get('gridProperties')}")
            
            # Đọc 20 dòng đầu của sheet này để kiểm tra
            title = props.get('title')
            result = sheet_api.values().get(
                spreadsheetId=sheet_id,
                range=f"'{title}'!A1:Z30",
                valueRenderOption="UNFORMATTED_VALUE"
            ).execute()
            
            values = result.get("values", [])
            print(f"   Read {len(values)} rows:")
            for i, row in enumerate(values[:20]):
                clean_row = [str(cell)[:30] if cell is not None else "" for cell in row]
                if any(clean_row):
                    print(f"     Row {i+1}: {clean_row[:10]}")
                    
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
