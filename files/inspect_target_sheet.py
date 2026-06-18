import sys
import os
import socket

socket.setdefaulttimeout(15)

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sheets_reader import _get_sheets_service

def main():
    # Thử đọc sheet Vũ Anh (đã chạy thành công trước đó)
    sheet_id = "1IpRGhylPd4TENwT4tZq5mOZnTzLmttkn4l8FejWtNZE"
    print(f"Connecting to Google Sheets API and reading known working sheet: {sheet_id}")
    try:
        service = _get_sheets_service()
        sheet_api = service.spreadsheets()
        
        meta = sheet_api.get(spreadsheetId=sheet_id).execute()
        first_title = meta["sheets"][0]["properties"]["title"]
        print(f"First tab title: {first_title}")
        
        result = sheet_api.values().get(
            spreadsheetId=sheet_id,
            range=f"'{first_title}'!A1:D10",
            valueRenderOption="FORMATTED_VALUE"
        ).execute()
        
        values = result.get("values", [])
        print("Success! Read A1:D10:")
        for i, row in enumerate(values):
            print(f"Row {i+1}: {row}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
