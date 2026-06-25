import re
import sys
import os
import requests
from googleapiclient.discovery import build
from google.auth import default as google_auth_default

def get_post_id(creative, ad_name=""):
    story_id = creative.get("effective_object_story_id", "")
    if story_id:
        if "_" in story_id:
            return story_id.split("_")[1]
        return story_id
    
    # Extract from ad_name
    if not ad_name:
        return ""
    nums = re.findall(r"\d{9,}", str(ad_name))
    return nums[0] if nums else ""

def get_thumbnail_url(creative):
    if creative.get("thumbnail_url"):
        return creative["thumbnail_url"]
    if creative.get("image_url"):
        return creative["image_url"]
    
    spec = creative.get("object_story_spec") or {}
    for path in [
        ("link_data",     "picture"),
        ("photo_data",    "url"),
        ("video_data",    "image_url"),
        ("template_data", "picture"),
    ]:
        val = spec.get(path[0], {}).get(path[1])
        if val:
            return val
    return ""

import argparse

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--google-token", help="Google Sheets OAuth2 Access Token")
    args = parser.parse_args()

    token = "EAAtyg8bAspcBRV3J9D9yZBErzbn0UteDCSBX9641yefznirlgVi1NNCHWPwwmP76AIGE0ju6xtO84pZC1ZAOQIk8ZApz67U6vNtZCZArtYpdpe0yJV0hkKY588JgCtsKZA6mY4pfmnqsvPenvkxtd4W4d5iAzZBc47mWHHhAvzl6LbZAY5iYXZA5bZAZAcDVDpDLj4iSjAZDZD"
    account_ids = [
        "act_696152742916012",
        "act_1491394528173951",
        "act_736221869292755",
        "act_2704042333126518",
        "act_2031624244397226",
        "act_1433365117712667"
    ]
    
    spreadsheet_id = "10sWUCv1uYk5X2CKfcwOqbd5K3JXjPmty00yb9IJkK0c"
    tab_name = "Bs Khanh"
    
    # De-duplication set based on post_id
    seen_post_ids = set()
    rows_to_add = []
    
    print("=== BAT DAU CAO DU LIEU FACEBOOK ADS ===")
    
    for act_id in account_ids:
        print(f"Dang quet tai khoan: {act_id}...")
        
        # Buoc 1: Lay thong tin ad co ban
        url = (
            f"https://graph.facebook.com/v19.0/{act_id}/ads"
            f"?fields=name,campaign{{name}},creative{{id}}"
            f"&limit=500&access_token={token}"
        )
        
        try:
            resp = requests.get(url, timeout=60)
            resp.raise_for_status()
            result = resp.json()
            
            if "error" in result:
                print(f"Loi tai khoan {act_id}: {result['error']['message']}")
                continue
                
            ads = result.get("data", [])
            print(f"Tim thay {len(ads)} ads trong tai khoan {act_id}.")
            
            # Buoc 2: Loc các ads thoa man ten campaign chua "Khanh"
            matched_ads = []
            for ad in ads:
                camp_name = ad.get("campaign", {}).get("name", "")
                if "khánh" in camp_name.lower() or "khanh" in camp_name.lower():
                    matched_ads.append(ad)
            
            if matched_ads:
                print(f"--> Co {len(matched_ads)} ads trung khop. Dang lay chi tiet creative...")
                
                # Buoc 3: Lay chi tiet creative cho tung ad va loc trung lap
                for ad in matched_ads:
                    ad_name = ad.get("name", "")
                    creative_id = ad.get("creative", {}).get("id")
                    if not creative_id:
                        continue
                    
                    creative_url = (
                        f"https://graph.facebook.com/v19.0/{creative_id}"
                        f"?fields=body,title,thumbnail_url,image_url,effective_object_story_id,object_story_spec"
                        f"&access_token={token}"
                    )
                    
                    try:
                        c_resp = requests.get(creative_url, timeout=20)
                        c_resp.raise_for_status()
                        creative = c_resp.json()
                        
                        # Lay ID Post (dong so) lam khoa dinh danh
                        post_id = get_post_id(creative, ad_name)
                        if not post_id:
                            continue
                            
                        # Neu ID Post da tung xuat hien, bo qua de tranh trung lap bài viết
                        if post_id in seen_post_ids:
                            continue
                        seen_post_ids.add(post_id)
                        
                        link = f"https://facebook.com/{post_id}"
                        content = creative.get("body") or creative.get("title") or ""
                        
                        thumb_url = get_thumbnail_url(creative)
                        thumb_formula = f'=IMAGE("{thumb_url}")' if thumb_url else ""
                        
                        # Columns: Thumbnail (A), Content (B), Link bài viết (C), Angle (D), Tên bài (E - chỉ điền dòng số ID Post)
                        rows_to_add.append([
                            thumb_formula,
                            content,
                            link,
                            "",
                            post_id  # Chi dien dong so dinh danh bài viết
                        ])
                    except Exception as ce:
                        print(f"Loi lay creative {creative_id}: {ce}")
                    
        except Exception as e:
            print(f"Loi fetch tai khoan {act_id}: {e}")
            
    print(f"\nTong so bai viet doc nhat cua Bs Khanh tim thay: {len(rows_to_add)}")
    if not rows_to_add:
        print("Khong tim thay ads nao phu hop.")
        return
        
    print("\n=== DANG GHI VAO GOOGLE SHEET ===")
    try:
        if args.google_token:
            from google.oauth2.credentials import Credentials
            credentials = Credentials(args.google_token)
        else:
            credentials, _ = google_auth_default(
                scopes=["https://www.googleapis.com/auth/spreadsheets"]
            )
        service = build("sheets", "v4", credentials=credentials, cache_discovery=False)
        sheet_api = service.spreadsheets()
        
        # 1. Clear dữ liệu cũ từ dòng 2
        real_tab_name = "Angle Bs Khánh"
        clear_range = f"'{real_tab_name}'!A2:E1000"
        print(f"Dang clear du lieu cu tai range: {clear_range}...")
        sheet_api.values().clear(
            spreadsheetId=spreadsheet_id,
            range=clear_range
        ).execute()
        
        # 2. Ghi dữ liệu mới
        write_range = f"'{real_tab_name}'!A2"
        print(f"Dang ghi du lieu moi vao range: {write_range}...")
        body = {
            "values": rows_to_add
        }
        sheet_api.values().update(
            spreadsheetId=spreadsheet_id,
            range=write_range,
            valueInputOption="USER_ENTERED",
            body=body
        ).execute()
        print("=== HOAN THANH GHI GOOGLE SHEET ===")
        
    except Exception as e:
        print(f"Loi ghi Google Sheet: {e}")

if __name__ == "__main__":
    main()
