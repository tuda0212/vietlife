"""
sync_all_fb_ads.py — Script chạy đồng bộ dữ liệu Facebook Ads cho 6 tài khoản từ 2025-01-01 đến nay.
"""

import os
import sys
import logging

# Thiết lập token Facebook
os.environ["FB_ACCESS_TOKEN"] = "EAAtyg8bAspcBRV3J9D9yZBErzbn0UteDCSBX9641yefznirlgVi1NNCHWPwwmP76AIGE0ju6xtO84pZC1ZAOQIk8ZApz67U6vNtZCZArtYpdpe0yJV0hkKY588JgCtsKZA6mY4pfmnqsvPenvkxtd4W4d5iAzZBc47mWHHhAvzl6LbZAY5iYXZA5bZAZAcDVDpDLj4iSjAZDZD"

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import pipeline

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s — %(message)s")
logger = logging.getLogger("sync_all_fb_ads")

def main():
    logger.info("=== BẮT ĐẦU ĐỒNG BỘ DỮ LIỆU FACEBOOK ADS ===")
    
    start_date = "2025-01-01"
    end_date = "2026-06-18"
    
    account_ids = [
        "act_696152742916012",
        "act_1491394528173951",
        "act_736221869292755",
        "act_2704042333126518",
        "act_2031624244397226",
        "act_1433365117712667"
    ]
    
    logger.info(f"Đồng bộ từ {start_date} đến {end_date} cho {len(account_ids)} accounts...")
    
    try:
        result = pipeline.run(
            start_date=start_date,
            end_date=end_date,
            account_ids=account_ids
        )
        logger.info("=== ĐỒNG BỘ HOÀN TẤT ===")
        logger.info(f"Status: {result.get('status')}")
        logger.info(f"Accounts processed: {result.get('accounts')}")
        logger.info(f"Insights count: {result.get('insights_count')}")
        logger.info(f"Inserted rows: {result.get('inserted_rows')}")
    except Exception as e:
        logger.exception(f"Lỗi đồng bộ: {e}")

if __name__ == "__main__":
    main()
