import sys
import os
import logging

# Thiết lập token lấy từ Secret Manager TRƯỚC khi import các module khác
os.environ["FB_ACCESS_TOKEN"] = "EAAtyg8bAspcBRV3J9D9yZBErzbn0UteDCSBX9641yefznirlgVi1NNCHWPwwmP76AIGE0ju6xtO84pZC1ZAOQIk8ZApz67U6vNtZCZArtYpdpe0yJV0hkKY588JgCtsKZA6mY4pfmnqsvPenvkxtd4W4d5iAzZBc47mWHHhAvzl6LbZAY5iYXZA5bZAZAcDVDpDLj4iSjAZDZD"

# Thêm thư mục 'files' vào sys.path để import pipeline
workspace_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
files_dir = os.path.join(workspace_dir, "files")
sys.path.append(files_dir)

import pipeline

# Cấu hình log rõ ràng
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s"
)
logger = logging.getLogger("sync_fb_ads")

try:
    start_date = "2026-01-01"
    end_date = "2026-03-31"
    account_ids = ["act_696152742916012", "act_736221869292755", "act_1491394528173951"] # Thần Kinh và Cơ Xương Khớp
    
    logger.info(f"Bắt đầu chạy Facebook Ads Pipeline cho Y tế từ {start_date} đến {end_date}...")
    res = pipeline.run(
        start_date=start_date,
        end_date=end_date,
        account_ids=account_ids
    )
    logger.info(f"Đồng bộ Ads thành công! Kết quả: {res}")
except Exception as e:
    logger.exception(f"Lỗi khi chạy Facebook Ads pipeline: {e}")
