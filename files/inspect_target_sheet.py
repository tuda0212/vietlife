import sys
import os
import socket

# Thiết lập timeout lớn hơn để tránh lỗi
socket.setdefaulttimeout(90)

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sheets_reader import _get_sheets_service

def main():
    sheet_id = "1guUru-qTB6Pug4Oc43fqoEw3UUVmFXs2R7MAUr3AIGY"
    target_title = "Hiệu quả bài (T3)"
    print(f"Connecting to Google Sheets API and reading: {target_title}")
    try:
        service = _get_sheets_service()
        sheet_api = service.spreadsheets()
        
        # Đọc 150 dòng đầu tiên của sheet
        result = sheet_api.values().get(
            spreadsheetId=sheet_id,
            range=f"'{target_title}'!A1:T150",
            valueRenderOption="UNFORMATTED_VALUE"
        ).execute()
        
        values = result.get("values", [])
        print(f"Read {len(values)} rows:")
        for i, row in enumerate(values):
            clean_row = [str(cell) if cell is not None else "" for cell in row]
            if any(clean_row):
                print(f"Row {i+1}: {clean_row[:18]}")
                
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
