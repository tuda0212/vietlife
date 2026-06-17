"""
backfill_crm.py — Script chạy đồng bộ dữ liệu lịch sử từ 2025-01-01 tới nay (2026-06-17)
"""

import logging
from crm_pipeline import run as run_crm_pipeline

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s — %(message)s")
logger = logging.getLogger("backfill_crm")

def main():
    logger.info("=== STARTING HISTORICAL BACKFILL ===")
    
    start_date = "2025-01-01"
    end_date = "2026-06-17"
    
    # Không truyền versions để crm_pipeline tự động suy luận versions = [2025, 2026]
    result = run_crm_pipeline(start_date=start_date, end_date=end_date)
    
    logger.info("=== BACKFILL RESULT ===")
    logger.info(f"Status: {result.get('status')}")
    logger.info(f"Total inserted: {result.get('total_inserted')}")
    for detail in result.get("details", []):
        logger.info(f" - Config: {detail.get('doctor')}, Read: {detail.get('rows_read')}, Inserted: {detail.get('inserted')}, Status: {detail.get('status')}")
        if detail.get("status") == "error":
            logger.error(f"   Error Message: {detail.get('message')}")

if __name__ == "__main__":
    main()
