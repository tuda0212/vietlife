import sys
import os
import logging
from pathlib import Path
from datetime import date, timedelta

# ─────────────────────────────────────────────────────────────────────────────
# Load biến môi trường từ file .env
# ─────────────────────────────────────────────────────────────────────────────
workspace_root = Path(__file__).resolve().parent.parent
env_file = workspace_root / ".env"

if env_file.exists():
    with open(env_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                os.environ.setdefault(key.strip(), value.strip())

if not os.environ.get("FB_ACCESS_TOKEN"):
    raise EnvironmentError(
        "❌ Thiếu FB_ACCESS_TOKEN!\n"
        "   Hãy tạo file .env ở thư mục gốc repo và thêm dòng:\n"
        "   FB_ACCESS_TOKEN=your_token_here\n"
        "   (Xem .env.example để biết cú pháp)"
    )

# Thêm thư mục 'files' vào sys.path để import các module cốt lõi
files_dir = os.path.join(workspace_root, "files")
sys.path.append(files_dir)

import fb_api
import transform
import bq_loader
from config import AD_ACCOUNTS

# Cấu hình logger
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s"
)
logger = logging.getLogger("sync_fb_ad_demographics")

def main():
    logger.info("=== BẮT ĐẦU ĐỒNG BỘ DỮ LIỆU NHÂN KHẨU HỌC FACEBOOK ADS ===")
    
    # Cho phép chỉ định start_date, end_date và account_id cụ thể qua dòng lệnh
    start_date = sys.argv[1] if len(sys.argv) > 1 else "2025-01-01"
    end_date = sys.argv[2] if len(sys.argv) > 2 else date.today().strftime("%Y-%m-%d")
    
    target_account = sys.argv[3] if len(sys.argv) > 3 else None
    if target_account:
        account_ids = [target_account]
    else:
        account_ids = list(AD_ACCOUNTS.keys())
    
    logger.info(f"Thời gian đồng bộ: {start_date} → {end_date}")
    logger.info(f"Tổng số tài khoản: {len(account_ids)} ({', '.join(account_ids)})")
    logger.info("=" * 60)
    
    run_str = date.today().strftime("%Y-%m-%d")
    demo_rows = []
    
    for account_id in account_ids:
        try:
            logger.info(f"[{account_id}] 1. Lấy dữ liệu Độ tuổi & Giới tính (Age/Gender)...")
            raw_age_gender = fb_api.fetch_demographics_insights(
                account_id=account_id,
                start_date=start_date,
                end_date=end_date,
                breakdowns="age,gender"
            )
            age_gender_rows = transform.transform_demographics(
                insights=raw_age_gender,
                account_specialty_map=AD_ACCOUNTS,
                breakdown_type="age_gender",
                run_date=run_str
            )
            demo_rows.extend(age_gender_rows)
            logger.info(f"[{account_id}] Lấy được {len(age_gender_rows)} dòng dữ liệu Age/Gender")

            logger.info(f"[{account_id}] 2. Lấy dữ liệu Vùng miền (Region)...")
            raw_region = fb_api.fetch_demographics_insights(
                account_id=account_id,
                start_date=start_date,
                end_date=end_date,
                breakdowns="region"
            )
            region_rows = transform.transform_demographics(
                insights=raw_region,
                account_specialty_map=AD_ACCOUNTS,
                breakdown_type="region",
                run_date=run_str
            )
            demo_rows.extend(region_rows)
            logger.info(f"[{account_id}] Lấy được {len(region_rows)} dòng dữ liệu Region")

        except Exception as err:
            logger.error(f"❌ Lỗi khi lấy dữ liệu cho tài khoản {account_id}: {err}")
            
    if demo_rows:
        logger.info(f"Tổng số dòng demographics thu thập được: {len(demo_rows)}")
        logger.info("Bắt đầu nạp dữ liệu vào BigQuery...")
        try:
            inserted = bq_loader.upsert_demographics_rows(
                rows=demo_rows,
                start_date=start_date,
                end_date=end_date,
                account_ids=account_ids
            )
            logger.info(f"✅ Đồng bộ demographics thành công! Đã ghi {inserted} dòng vào bảng BigQuery.")
        except Exception as bq_err:
            logger.error(f"❌ Lỗi khi nạp dữ liệu vào BigQuery: {bq_err}")
    else:
        logger.warning("⚠️ Không thu thập được dữ liệu demographics nào để nạp.")
        
    logger.info("=== ĐỒNG BỘ HOÀN TẤT ===")

if __name__ == "__main__":
    main()
