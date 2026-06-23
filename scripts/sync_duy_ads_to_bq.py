import sys
import os
import logging
from pathlib import Path

# Load biến môi trường từ file .env
workspace_root = Path(__file__).resolve().parent.parent
env_file = workspace_root / ".env"

if env_file.exists():
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                os.environ.setdefault(key.strip(), value.strip())

if not os.environ.get("FB_ACCESS_TOKEN"):
    raise EnvironmentError("❌ Thiếu FB_ACCESS_TOKEN trong .env!")

# Thêm thư mục 'files' vào sys.path
workspace_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
files_dir = os.path.join(workspace_dir, "files")
sys.path.append(files_dir)

import pipeline

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s"
)
logger = logging.getLogger("sync_duy_ads")

try:
    start_date = "2026-01-01"
    end_date = "2026-06-23"
    # Đồng bộ tài khoản act_2704042333126518 (Dược Nano / Vững Cốt)
    account_ids = ["act_2704042333126518"]
    
    logger.info(f"Bắt đầu chạy Facebook Ads Pipeline cho tài khoản act_2704042333126518 từ {start_date} đến {end_date}...")
    res = pipeline.run(
        start_date=start_date,
        end_date=end_date,
        account_ids=account_ids
    )
    logger.info(f"Đồng bộ Ads thành công! Kết quả: {res}")
except Exception as e:
    logger.exception(f"Lỗi khi chạy Facebook Ads pipeline: {e}")
