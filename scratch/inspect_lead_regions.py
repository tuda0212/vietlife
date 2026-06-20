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
    
    # 1. Đọc danh sách SĐT MKT từ MB 08-14 Jun
    result = sheet_api.values().get(
        spreadsheetId="1BIMzw4aUhrvOFbKZsj3s4Zu6n2qb_MFI9qakt9DDsec",
        range="'MB 08-14 Jun'!AH2:AH500",
        valueRenderOption="FORMATTED_VALUE"
    ).execute()
    
    mkt_phones = [row[0] for row in result.get("values", []) if row and row[0]]
    print(f"Số lượng SĐT MKT đọc được: {len(mkt_phones)}")
    
    # 2. Đọc từ TTTK 2026, TTCS 2026, TTCXK 2026 để xem cột Tỉnh thành (index 4)
    config_ss_id = "15We9-LwI9yOF7Z951YAHKxzPF7X5-lx3DZ5Z7Rtw5jg"
    cities = {}
    
    for name in ["TTCS 2026", "TTCXK 2026", "TTTK 2026"]:
        try:
            res = sheet_api.values().get(
                spreadsheetId=config_ss_id,
                range=f"'{name}'!A2:G"
            ).execute()
            rows = res.get("values", [])
            for row in rows:
                if len(row) > 4:
                    phone = "".join(c for c in str(row[3]) if c.isdigit())[-9:]
                    city = str(row[4]).strip()
                    if phone:
                        cities[phone] = (city, name)
        except Exception as e:
            print(f"Lỗi đọc {name}: {e}")
            
    # Đối chiếu
    matched = 0
    city_counts = {}
    for p in mkt_phones:
        norm_p = "".join(c for c in p if c.isdigit())[-9:]
        if norm_p in cities:
            matched += 1
            city, sheet_name = cities[norm_p]
            city_counts[city] = city_counts.get(city, 0) + 1
            
    print(f"\nKhớp thành công {matched}/{len(mkt_phones)} SĐT với thông tin Tỉnh thành.")
    print("Thống kê Tỉnh thành:")
    for city, count in city_counts.items():
        print(f"  - {city}: {count} leads")

if __name__ == "__main__":
    main()
