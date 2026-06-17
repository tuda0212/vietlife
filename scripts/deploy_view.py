import logging
import os
from google.cloud import bigquery

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("deploy_view")

def deploy():
    project_id = "gen-lang-client-0738410622"
    dataset_id = "marketing_data"
    
    views = {
        "v_report": "v_report.sql",
        "v_report_y_te": "v_report_y_te.sql",
        "v_report_y_te_detail": "v_report_y_te_detail.sql",
        "v_report_duoc": "v_report_duoc.sql"
    }
    
    client = bigquery.Client(project=project_id)
    
    # Lấy thư mục gốc (thư mục cha của thư mục chứa script này)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.dirname(script_dir)
    
    for view_name, sql_filename in views.items():
        sql_path = os.path.join(root_dir, sql_filename)
        if not os.path.exists(sql_path):
            logger.warning(f"File SQL {sql_path} không tồn tại. Bỏ qua...")
            continue
            
        logger.info(f"Đang đọc định nghĩa view từ {sql_filename}...")
        with open(sql_path, "r", encoding="utf-8") as f:
            sql = f.read()
            
        logger.info(f"Đang tạo/ghi đè view {project_id}.{dataset_id}.{view_name}...")
        try:
            query_job = client.query(sql)
            query_job.result()  # Chờ job hoàn thành
            logger.info(f"Đã deploy thành công view '{view_name}' lên BigQuery!")
        except Exception as e:
            logger.error(f"Lỗi khi deploy view '{view_name}': {e}")

if __name__ == "__main__":
    deploy()
