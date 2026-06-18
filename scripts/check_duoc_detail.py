import logging
import os
from google.cloud import bigquery

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("check_duoc_detail")

def main():
    project_id = "gen-lang-client-0738410622"
    dataset_id = "marketing_data"
    client = bigquery.Client(project=project_id)
    
    # 1. Kiểm tra trong BigQuery
    dataset_ref = client.dataset(dataset_id)
    tables = [t.table_id for t in client.list_tables(dataset_ref)]
    logger.info(f"Danh sách các bảng/view hiện có trên BigQuery: {tables}")
    
    if "v_report_duoc_detail" in tables:
        logger.info("-> Tìm thấy view 'v_report_duoc_detail' trên BigQuery!")
        # In schema hoặc query definition
        table = client.get_table(f"{project_id}.{dataset_id}.v_report_duoc_detail")
        if table.table_type == "VIEW":
            logger.info("View SQL của v_report_duoc_detail:")
            print(table.view_query)
    else:
        logger.info("-> Không tìm thấy view 'v_report_duoc_detail' trên BigQuery.")
        
    # 2. Kiểm tra file cục bộ
    script_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.dirname(script_dir)
    files = os.listdir(root_dir)
    sql_files = [f for f in files if f.endswith(".sql")]
    logger.info(f"Các file SQL ở thư mục gốc: {sql_files}")

if __name__ == "__main__":
    main()
