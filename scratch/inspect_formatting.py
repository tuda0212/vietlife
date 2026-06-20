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
    
    # Đọc dữ liệu kèm định dạng
    result = sheet_api.get(
        spreadsheetId=spreadsheet_id,
        ranges=[f"'{tab_name}'!A1:AZ200"],
        includeGridData=True
    ).execute()
    
    sheet_data = result["sheets"][0]["data"][0]
    row_data = sheet_data.get("rowData", [])
    
    if not row_data:
        print("Không có dữ liệu!")
        return
        
    headers = [cell.get("formattedValue", "") for cell in row_data[0].get("values", [])]
    print(f"Tổng số cột: {len(headers)}")
    
    colored_cells = []
    for r_idx, row in enumerate(row_data[1:], start=2):
        cells = row.get("values", [])
        for c_idx, cell in enumerate(cells):
            bg = cell.get("userEnteredFormat", {}).get("backgroundColor", {})
            if bg:
                r = bg.get("red", 0)
                g = bg.get("green", 0)
                b = bg.get("blue", 0)
                # Lọc màu vàng (đỏ cao, xanh lá cao, xanh dương thấp)
                if r > 0.8 and g > 0.8 and b < 0.2:
                    r_val = int(r * 255)
                    g_val = int(g * 255)
                    b_val = int(b * 255)
                    hex_color = f"#{r_val:02X}{g_val:02X}{b_val:02X}"
                    
                    val = cell.get("formattedValue", "")
                    header = headers[c_idx] if c_idx < len(headers) else ""
                    colored_cells.append({
                        "row": r_idx,
                        "col": c_idx,
                        "header": header,
                        "value": val,
                        "color": hex_color
                    })
                
    # Hiển thị tất cả các ô màu vàng tìm thấy
    print(f"\nTìm thấy {len(colored_cells)} ô màu vàng (được cập nhật đối soát):")
    for cell in colored_cells[:50]:
        print(f"Dòng {cell['row']}, Cột {cell['col']} ({cell['header']}): giá trị='{cell['value']}', màu={cell['color']}")

if __name__ == "__main__":
    main()
