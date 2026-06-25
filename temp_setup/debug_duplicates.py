import re
import sys
import requests
import json

def get_post_id(creative, ad_name=""):
    story_id = creative.get("effective_object_story_id", "")
    if story_id:
        if "_" in story_id:
            return story_id.split("_")[1]
        return story_id
    if not ad_name:
        return ""
    nums = re.findall(r"\d{9,}", str(ad_name))
    return nums[0] if nums else ""

def main():
    token = "EAAtyg8bAspcBRV3J9D9yZBErzbn0UteDCSBX9641yefznirlgVi1NNCHWPwwmP76AIGE0ju6xtO84pZC1ZAOQIk8ZApz67U6vNtZCZArtYpdpe0yJV0hkKY588JgCtsKZA6mY4pfmnqsvPenvkxtd4W4d5iAzZBc47mWHHhAvzl6LbZAY5iYXZA5bZAZAcDVDpDLj4iSjAZDZD"
    account_ids = [
        "act_696152742916012",
        "act_1491394528173951",
        "act_736221869292755",
        "act_2704042333126518",
        "act_2031624244397226",
        "act_1433365117712667"
    ]
    
    matched_ads = []
    
    for act_id in account_ids:
        url = (
            f"https://graph.facebook.com/v19.0/{act_id}/ads"
            f"?fields=name,id,campaign{{name}},creative{{id}}"
            f"&limit=500&access_token={token}"
        )
        
        try:
            resp = requests.get(url, timeout=60)
            resp.raise_for_status()
            result = resp.json()
            ads = result.get("data", [])
            
            for ad in ads:
                camp_name = ad.get("campaign", {}).get("name", "")
                if "bs khánh" in camp_name.lower() or "bs khanh" in camp_name.lower():
                    matched_ads.append((act_id, ad))
        except Exception as e:
            pass

    # Gom nhóm theo creative_id để phân tích
    from collections import defaultdict
    creative_groups = defaultdict(list)
    
    for act_id, ad in matched_ads:
        ad_name = ad.get("name", "")
        ad_id = ad.get("id", "")
        camp_name = ad.get("campaign", {}).get("name", "")
        creative_id = ad.get("creative", {}).get("id")
        
        # Lấy chi tiết creative
        creative_url = (
            f"https://graph.facebook.com/v19.0/{creative_id}"
            f"?fields=body,title,thumbnail_url,image_url,effective_object_story_id"
            f"&access_token={token}"
        )
        try:
            c_resp = requests.get(creative_url, timeout=20)
            c_resp.raise_for_status()
            creative = c_resp.json()
        except:
            creative = {}
            
        post_id = get_post_id(creative, ad_name)
        
        creative_groups[creative_id].append({
            "account_id": act_id,
            "ad_id": ad_id,
            "ad_name": ad_name,
            "camp_name": camp_name,
            "post_id": post_id,
            "body": creative.get("body", "")[:60].replace("\n", " ")
        })

    # Ghi ra file debug
    with open("e:\\vietlife\\temp_setup\\ad_debug.txt", "w", encoding="utf-8") as f:
        f.write("=== PHAN TICH CHI TIET ADS TRUNG LAP ===\n\n")
        for creative_id, ads_list in creative_groups.items():
            f.write(f"CREATIVE ID: {creative_id} (Body: {ads_list[0]['body']}...)\n")
            f.write(f"Post ID: {ads_list[0]['post_id']}\n")
            f.write(f"So luong Ads dung chung: {len(ads_list)}\n")
            for idx, ad_info in enumerate(ads_list):
                f.write(f"  {idx+1}. Account: {ad_info['account_id']}\n")
                f.write(f"     Ad ID  : {ad_info['ad_id']}\n")
                f.write(f"     Ad Name: {ad_info['ad_name']}\n")
                f.write(f"     Camp   : {ad_info['camp_name']}\n")
            f.write("-" * 50 + "\n\n")

if __name__ == "__main__":
    main()
