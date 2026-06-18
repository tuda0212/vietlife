#!/usr/bin/env python3
"""
create_ba_messenger_campaign.py
Script lên chiến dịch tin nhắn cho Bình An Nano theo yêu cầu của người dùng.
"""

import os
import sys
import json
import logging
import requests
from datetime import datetime
from pathlib import Path

# Thêm đường dẫn helper vào sys.path
script_dir = Path(__file__).resolve().parent
workspace_root = script_dir.parent
helper_dir = workspace_root / ".agents" / "skills" / "facebook-ads-campaign" / "scripts"
sys.path.append(str(helper_dir))

import fb_creation_helper

# Cấu hình logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s"
)
logger = logging.getLogger("create_ba_messenger_campaign")

def get_page_id_from_post(token: str, post_id: str) -> str:
    """Gọi Graph API để lấy Page ID sở hữu bài viết."""
    url = f"https://graph.facebook.com/v20.0/{post_id}?fields=from&access_token={token}"
    resp = requests.get(url, timeout=20)
    resp.raise_for_status()
    data = resp.json()
    if "from" in data and "id" in data["from"]:
        page_id = data["from"]["id"]
        page_name = data["from"].get("name", "Bình An Nano")
        logger.info(f"Đã xác định Page sở hữu bài viết: {page_name} (ID: {page_id})")
        return page_id
    raise ValueError(f"Không thể lấy Page ID từ bài viết {post_id}. Phản hồi: {data}")

def main():
    fb_creation_helper.load_env()
    token = os.environ.get("FB_ACCESS_TOKEN")
    
    if not token or token.startswith("your_"):
        logger.error("❌ Thiếu FB_ACCESS_TOKEN hợp lệ trong file .env!")
        print("\n[HƯỚNG DẪN] Vui lòng cập nhật FB_ACCESS_TOKEN vào file .env ở thư mục gốc repo trước khi chạy script này.")
        sys.exit(1)
        
    ad_account_id = "act_2704042333126518" # Tài khoản Vững Cốt (Dược Nano) chứa chuyên khoa BA
    post_id = "1331283542404011"
    daily_budget = 300000 # 300k VND
    
    # Lấy ngày hiện tại để đặt tên
    date_str = datetime.now().strftime("%d%b%y") # Ví dụ: 19Jun26
    campaign_name = f"BA_Mess_BinhAnNano_{date_str}"
    adset_name = f"AdSet_BA_Mess_TargetMiendBac_35_65"
    creative_name = f"Creative_BA_Mess_Post_{post_id}"
    ad_name = f"Ad_BA_Mess_BinhAnNano_Post"
    
    try:
        # Bước 0: Tự động lấy Page ID từ Post ID qua API
        logger.info("Đang truy vấn Page ID từ bài viết...")
        page_id = get_page_id_from_post(token, post_id)
        
        # Bước 1: Tạo Campaign (Mục tiêu Tin nhắn - OUTCOME_ENGAGEMENT)
        campaign_id = fb_creation_helper.create_campaign(
            ad_account_id=ad_account_id,
            name=campaign_name,
            objective="OUTCOME_ENGAGEMENT",
            status="PAUSED"
        )
        
        # Bước 2: Thiết lập Targeting cho miền Bắc (độ tuổi 35-65+)
        # Danh sách mã vùng các tỉnh miền Bắc Việt Nam
        northern_regions = [
            {"key": "3840"},  # Hà Nội
            {"key": "3832"},  # Hải Phòng
            {"key": "3856"},  # Quảng Ninh
            {"key": "3859"},  # Vĩnh Phúc
            {"key": "3841"},  # Bắc Ninh
            {"key": "3844"},  # Hải Dương
            {"key": "3845"},  # Hưng Yên
            {"key": "3846"},  # Thái Bình
            {"key": "3848"},  # Nam Định
            {"key": "3849"},  # Ninh Bình
            {"key": "3843"},  # Hà Nam
            {"key": "3850"},  # Phú Thọ
            {"key": "3851"},  # Thái Nguyên
            {"key": "3852"},  # Bắc Giang
            {"key": "3853"},  # Hòa Bình
            {"key": "3854"},  # Sơn La
            {"key": "3855"},  # Điện Biên
            {"key": "3857"},  # Lai Châu
            {"key": "3858"},  # Lạng Sơn
            {"key": "3860"},  # Tuyên Quang
            {"key": "3861"},  # Hà Giang
            {"key": "3862"},  # Cao Bằng
            {"key": "3863"},  # Bắc Kạn
            {"key": "3864"},  # Yên Bái
            {"key": "3865"}   # Lào Cai
        ]
        
        targeting = {
            "geo_locations": {
                "regions": northern_regions
            },
            "age_min": 35,
            "age_max": 65
        }
        
        # Tạo Ad Set
        adset_id = fb_creation_helper.create_ad_set(
            ad_account_id=ad_account_id,
            campaign_id=campaign_id,
            name=adset_name,
            daily_budget=daily_budget,
            targeting=targeting,
            billing_event="IMPRESSIONS",
            optimization_goal="REPLIES", # Tối ưu hóa lượt phản hồi tin nhắn
            status="PAUSED"
        )
        
        # Bước 3: Tạo Ad Creative sử dụng bài viết có sẵn
        creative_id = fb_creation_helper.create_ad_creative_post(
            ad_account_id=ad_account_id,
            name=creative_name,
            page_id=page_id,
            post_id=post_id
        )
        
        # Bước 4: Tạo Ad thực tế
        ad_id = fb_creation_helper.create_ad(
            ad_account_id=ad_account_id,
            adset_id=adset_id,
            creative_id=creative_id,
            name=ad_name,
            status="PAUSED"
        )
        
        logger.info("\n🎉🎉 LÊN CHIẾN DỊCH QUẢNG CÁO TIN NHẮN THÀNH CÔNG! 🎉🎉")
        print(f"\n[KẾT QUẢ TẠO CHIẾN DỊCH]")
        print(f"- Campaign ID:    {campaign_id}")
        print(f"- Ad Set ID:      {adset_id}")
        print(f"- Creative ID:    {creative_id}")
        print(f"- Ad ID:          {ad_id}")
        print(f"- Trạng thái:     PAUSED (Tắt)")
        
    except Exception as e:
        logger.error(f"❌ Lỗi khi thực hiện tạo chiến dịch: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
