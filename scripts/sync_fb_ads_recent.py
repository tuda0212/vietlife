import os
import sys
import logging
from pathlib import Path

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
    raise EnvironmentError("Thiếu FB_ACCESS_TOKEN!")

sys.path.append(os.path.join(workspace_root, "files"))
import pipeline

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s — %(message)s")
logger = logging.getLogger("sync_fb_ads_recent")

def main():
    logger.info("=== BẮT ĐẦU ĐỒNG BỘ DỮ LIỆU FACEBOOK ADS GẦN ĐÂY ===")
    
    start_date = "2026-05-15"
    end_date = "2026-06-19"
    
    account_ids = [
        "act_696152742916012",
        "act_1491394528173951",
        "act_736221869292755",
        "act_2704042333126518",
        "act_2031624244397226",
        "act_1433365117712667"
    ]
    
    try:
        result = pipeline.run(
            start_date=start_date,
            end_date=end_date,
            account_ids=account_ids
        )
        logger.info("=== ĐỒNG BỘ HOÀN TẤT ===")
        logger.info(f"Inserted rows: {result.get('inserted_rows')}")
    except Exception as e:
        logger.exception(f"Lỗi đồng bộ: {e}")

if __name__ == "__main__":
    main()
