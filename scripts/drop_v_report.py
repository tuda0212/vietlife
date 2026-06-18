import logging
import os
from google.cloud import bigquery

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("drop_v_report")

def main():
    project_id = "gen-lang-client-0738410622"
    dataset_id = "marketing_data"
    client = bigquery.Client(project=project_id)
    
    # 1. DROP VIEW trên BigQuery
    view_ref = f"{project_id}.{dataset_id}.v_report"
    logger.info(f"Đang thực hiện DROP VIEW {view_ref} trên BigQuery...")
    try:
        client.query(f"DROP VIEW IF EXISTS `{view_ref}`").result()
        logger.info(f"Đã drop view '{view_ref}' thành công!")
    except Exception as e:
        logger.error(f"Lỗi khi drop view: {e}")
        
    # 2. Xóa file v_report.sql cục bộ
    script_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.dirname(script_dir)
    sql_path = os.path.join(root_dir, "v_report.sql")
    
    if os.path.exists(sql_path):
        logger.info(f"Đang xóa file định nghĩa cục bộ tại {sql_path}...")
        try:
            os.remove(sql_path)
            logger.info("Đã xóa file v_report.sql thành công!")
        except Exception as e:
            logger.error(f"Lỗi khi xóa file: {e}")
    else:
        logger.info(f"File {sql_path} không tồn tại.")

if __name__ == "__main__":
    main()
