import sys
import io
import re
import json
import argparse
import requests
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

# Cấu hình UTF-8 cho console để tránh lỗi Encoding cp1252 trên Windows
try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except AttributeError:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

def get_sheet_mapping(google_token, spreadsheet_id, tab_name):
    """
    Đọc dữ liệu từ Google Sheets và tạo map: id_post -> (angle, ten_bai)
    """
    print(f"[*] Dang ket noi toi Google Sheet: {spreadsheet_id}...")
    credentials = Credentials(google_token)
    service = build("sheets", "v4", credentials=credentials, cache_discovery=False)
    
    # Doc toan bo bang tinh
    read_range = f"'{tab_name}'!A1:E1000"
    result = service.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id,
        range=read_range
    ).execute()
    
    rows = result.get("values", [])
    if not rows:
        print("[-] Khong co du lieu trong Google Sheet.")
        return {}
        
    header = rows[0]
    print(f"[*] Doc duoc {len(rows)} dong tu sheet. Header: {header}")
    
    # Kiem tra index cac cot
    link_idx = 2
    angle_idx = 3
    title_idx = 4
    
    for idx, col in enumerate(header):
        col_lower = col.lower().strip()
        if "link" in col_lower:
            link_idx = idx
        elif "angle" in col_lower:
            angle_idx = idx
        elif "tên bài" in col_lower or "ten bai" in col_lower:
            title_idx = idx
            
    print(f"[*] Mapping indexes: Link={link_idx}, Angle={angle_idx}, Title={title_idx}")
    
    mapping = {}
    for i, row in enumerate(rows[1:], start=2):
        if len(row) <= max(link_idx, angle_idx, title_idx):
            continue
            
        link = row[link_idx].strip() if len(row) > link_idx else ""
        angle = row[angle_idx].strip() if len(row) > angle_idx else ""
        title = row[title_idx].strip() if len(row) > title_idx else ""
        
        if not link:
            continue
            
        # Trich xuat ID Post tu link
        post_ids = re.findall(r"\d{9,}", link)
        if not post_ids:
            continue
        post_id = post_ids[0]
        
        mapping[post_id] = {
            "angle": angle,
            "title": title,
            "row_num": i
        }
        
    print(f"[+] Da tai thanh cong {len(mapping)} key mapping tu Google Sheet.")
    return mapping

def extract_post_id(ad_name):
    """
    Trich xuat ID Post (dong so tu 9 chu so tro len) tu ad_name
    """
    if not ad_name:
        return ""
    nums = re.findall(r"\d{9,}", str(ad_name))
    return nums[0] if nums else ""

def get_ads_with_filtering(act_id, fb_token):
    """
    Quét danh sách Ad của tài khoản sử dụng bộ lọc campaign.name trực tiếp trên API
    để tối ưu hóa số lượng requests và tránh dính Rate Limit.
    """
    ads_dict = {}
    
    # 2 bộ lọc cho chữ "Khánh" (có dấu) và "Khanh" (không dấu)
    filters = ["Khánh", "Khanh"]
    
    for filter_val in filters:
        filter_str = json.dumps([
            {
                "field": "campaign.name",
                "operator": "CONTAIN",
                "value": filter_val
            }
        ])
        
        url = (
            f"https://graph.facebook.com/v19.0/{act_id}/ads"
            f"?fields=id,name,campaign{{id,name}}"
            f"&filtering={filter_str}"
            f"&limit=500&access_token={fb_token}"
        )
        
        try:
            resp = requests.get(url, timeout=30)
            resp.raise_for_status()
            ads_data = resp.json().get("data", [])
            for ad in ads_data:
                ads_dict[ad["id"]] = ad
        except Exception as e:
            # Nếu một tài khoản bị Rate Limit (400), ta in thông báo chi tiết
            print(f"[-] Loi quet filter '{filter_val}' cho {act_id}: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"    Chi tiet loi API: {e.response.text}")
                
    return list(ads_dict.values())

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--google-token", required=True, help="Google Sheets OAuth2 Access Token")
    parser.add_argument("--fb-token", default="EAAtyg8bAspcBRV3J9D9yZBErzbn0UteDCSBX9641yefznirlgVi1NNCHWPwwmP76AIGE0ju6xtO84pZC1ZAOQIk8ZApz67U6vNtZCZArtYpdpe0yJV0hkKY588JgCtsKZA6mY4pfmnqsvPenvkxtd4W4d5iAzZBc47mWHHhAvzl6LbZAY5iYXZA5bZAZAcDVDpDLj4iSjAZDZD", help="Facebook Access Token")
    parser.add_argument("--dry-run", action="store_true", help="Chay thu khong thuc hien doi ten that tren Facebook")
    args = parser.parse_args()
    
    spreadsheet_id = "10sWUCv1uYk5X2CKfcwOqbd5K3JXjPmty00yb9IJkK0c"
    tab_name = "Angle Bs Khánh"
    account_ids = [
        "act_696152742916012",
        "act_736221869292755"
    ]
    
    # 1. Lay du lieu mapping tu Google Sheet
    sheet_map = get_sheet_mapping(args.google_token, spreadsheet_id, tab_name)
    if not sheet_map:
        print("[-] Khong co du lieu de thuc hien doi ten. Huy bo.")
        return
        
    # 2. Quet cac Ad tu tung campaign va doi ten
    print("\n=== BAT DAU SCAN ADS GOI FB MARKETING API WITH FILTERING ===")
    if args.dry_run:
        print("[!] CHE DO CHAY THU (DRY-RUN) - SE KHONG CO THAY DOI THUC TE TREN FACEBOOK")
        
    total_found = 0
    total_mapped = 0
    total_renamed = 0
    
    for act_id in account_ids:
        print(f"\n[*] Dang quet tai khoan: {act_id}...")
        
        # Quét ad của tài khoản sử dụng bộ lọc API tối ưu
        ads = get_ads_with_filtering(act_id, args.fb_token)
        print(f"[*] Tim thay {len(ads)} ads phu hop voi bo loc chien dich Bs Khanh.")
        
        for ad in ads:
            total_found += 1
            ad_id = ad.get("id")
            ad_name_old = ad.get("name", "")
            camp_name = ad.get("campaign", {}).get("name", "")
            
            # Trich xuat ID Post tu ad_name cu
            post_id = extract_post_id(ad_name_old)
            if not post_id:
                print(f"  [X] Khong the trich xuat ID Post tu ad_name cu: '{ad_name_old}' (Ad ID: {ad_id})")
                continue
                
            # Tra cuu trong map
            if post_id not in sheet_map:
                print(f"  [X] ID Post '{post_id}' (tu ad_name cu: '{ad_name_old}') khong ton tai trong Google Sheet.")
                continue
                
            total_mapped += 1
            sheet_info = sheet_map[post_id]
            angle = sheet_info["angle"]
            title = sheet_info["title"]
            
            if not angle or not title:
                print(f"  [!] ID Post '{post_id}' co Angle hoac Ten bai bi trong tren sheet (Dong {sheet_info['row_num']}). Bo qua.")
                continue
                
            ad_name_new = f"{angle}_{title}_{ad_name_old}"
            
            if ad_name_old == ad_name_new:
                print(f"  [-] Ad '{ad_name_old}' da dung dinh dang. Bo qua.")
                continue
                
            print(f"  [->] MAPPED: Dong {sheet_info['row_num']}")
            print(f"       Ad ID:       {ad_id}")
            print(f"       Campaign:    {camp_name}")
            print(f"       Ten cu:      {ad_name_old}")
            print(f"       Ten moi:     {ad_name_new}")
            
            if not args.dry_run:
                update_url = f"https://graph.facebook.com/v19.0/{ad_id}"
                update_payload = {
                    "name": ad_name_new,
                    "access_token": args.fb_token
                }
                try:
                    u_resp = requests.post(update_url, data=update_payload, timeout=20)
                    u_resp.raise_for_status()
                    result = u_resp.json()
                    if result.get("success"):
                        print("       [OK] Doi ten thanh cong!")
                        total_renamed += 1
                    else:
                        print(f"       [ERR] Doi ten that bai. Phan hoi: {result}")
                except Exception as ue:
                    print(f"       [ERR] Doi ten that bai. Loi: {ue}")
            else:
                total_renamed += 1
            
    print("\n================ TONG KET CHUONG TRINH ================")
    print(f"[*] Tong so Ad Bs Khanh tim thay: {total_found}")
    print(f"[*] Tong so Ad khop voi Google Sheet: {total_mapped}")
    if args.dry_run:
        print(f"[!] So Ad du kien se doi ten: {total_renamed}")
        print("[!] Chay o che do Dry-run. Chua co thay doi nao tren Facebook.")
    else:
        print(f"[*] Tong so Ad da doi ten thanh cong: {total_renamed}")
    print("=======================================================")

if __name__ == "__main__":
    main()
