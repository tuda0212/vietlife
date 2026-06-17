"""
deploy_views.py — Deploy views v_report_y_te và v_report_y_te_detail lên BigQuery.
"""

import os
import logging
from google.cloud import bigquery
from config_crm import GCP_PROJECT_ID

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s — %(message)s")
logger = logging.getLogger("deploy_views")

def deploy():
    client = bigquery.Client(project=GCP_PROJECT_ID)
    
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 1. Deploy v_report_y_te_detail
    detail_path = os.path.join(current_dir, "v_report_y_te_detail.sql")
    logger.info(f"Đọc file SQL: {detail_path}")
    with open(detail_path, "r", encoding="utf-8") as f:
        detail_sql = f.read()
        
    logger.info("Đang tạo view v_report_y_te_detail trên BigQuery...")
    client.query(detail_sql).result()
    logger.info("Đã tạo view v_report_y_te_detail thành công!")
    
    # 2. Deploy v_report_y_te
    general_path = os.path.join(current_dir, "v_report_y_te.sql")
    logger.info(f"Đọc file SQL: {general_path}")
    with open(general_path, "r", encoding="utf-8") as f:
        general_sql = f.read()
        
    logger.info("Đang tạo view v_report_y_te trên BigQuery...")
    client.query(general_sql).result()
    logger.info("Đã tạo view v_report_y_te thành công!")

if __name__ == "__main__":
    deploy()
