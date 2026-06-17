import sys
import os
import logging
from datetime import date

# Thêm thư mục 'files' vào sys.path để import crm_pipeline
workspace_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
files_dir = os.path.join(workspace_dir, "files")
sys.path.append(files_dir)

import crm_pipeline

# Cấu hình log rõ ràng
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s"
)
logger = logging.getLogger("sync_crm_all")

try:
    from config_crm import DOCTOR_SHEETS
    doctors_y_te = [k for k, v in DOCTOR_SHEETS.items() if v.get("report_group") == "Y tế"]
    
    start_date = "2025-01-01"
    end_date = date.today().strftime("%Y-%m-%d")
    
    logger.info(f"Bắt đầu chạy CRM Pipeline đồng bộ từ {start_date} đến {end_date} (Chỉ nhóm Y tế, không chạm vào Dược)...")
    
    res = crm_pipeline.run(
        start_date=start_date,
        end_date=end_date,
        doctors=doctors_y_te,
        versions=[2025, 2026]
    )
    
    logger.info("Đồng bộ thành công! Kết quả:")
    logger.info(f"Tổng số dòng đã insert: {res.get('total_inserted')}")
    for detail in res.get("details", []):
        logger.info(f" - {detail.get('doctor')}: trạng thái={detail.get('status')}, đọc={detail.get('rows_read')}, đã nạp={detail.get('inserted')}")
        if detail.get("status") == "error":
            logger.error(f"   Lỗi: {detail.get('message')}")
            
except Exception as e:
    logger.exception(f"Lỗi khi chạy CRM pipeline: {e}")
