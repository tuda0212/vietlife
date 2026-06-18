import logging
from google.cloud import bigquery

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("verify_views")

def verify():
    project_id = "gen-lang-client-0738410622"
    dataset_id = "marketing_data"
    client = bigquery.Client(project=project_id)
    
    # Danh sách các view đang tồn tại
    views = [
        # View nền tảng
        "v_fb_ads_y_te",
        "v_sdt_page_bac_si",
        "v_crm_y_te",
        "v_fb_ads_duoc",
        "v_sdt_dat_mua",
        
        # View báo cáo đã được tái cấu trúc
        "v_report_y_te",
        "v_report_y_te_detail",
        "v_report_duoc",
        "v_report_duoc_detail"
    ]
    
    for view_name in views:
        logger.info(f"Đang kiểm tra view: {view_name}...")
        query = f"SELECT COUNT(*) as count FROM `{project_id}.{dataset_id}.{view_name}`"
        try:
            query_job = client.query(query)
            results = list(query_job.result())
            row_count = results[0]["count"]
            logger.info(f"-> View '{view_name}' hoạt động tốt. Số dòng: {row_count}")
        except Exception as e:
            logger.error(f"-> Lỗi khi truy vấn view '{view_name}': {e}")
            
    # Kiểm tra xem v_report đã biến mất chưa
    logger.info("Đang kiểm tra xem view 'v_report' đã bị xóa chưa...")
    try:
        client.get_table(f"{project_id}.{dataset_id}.v_report")
        logger.warning("-> Cảnh báo: View 'v_report' vẫn còn tồn tại trên BigQuery!")
    except Exception:
        logger.info("-> Xác nhận: View 'v_report' đã được xóa thành công!")

if __name__ == "__main__":
    verify()
