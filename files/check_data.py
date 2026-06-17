"""
check_data.py — Truy vấn BigQuery để kiểm tra số lượng leads và doanh thu theo tháng cho nhóm Y tế.
"""

import logging
from google.cloud import bigquery
from config_crm import GCP_PROJECT_ID

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s — %(message)s")
logger = logging.getLogger("check_data")

def main():
    client = bigquery.Client(project=GCP_PROJECT_ID)
    
    sql = """
        SELECT 
            FORMAT_DATE('%Y-%m', lead_date) AS month, 
            report_group, 
            COUNT(*) AS total_leads, 
            COUNTIF(is_booking=True) AS total_bookings,
            COUNTIF(is_arrival=True) AS total_arrivals,
            SUM(IFNULL(revenue, 0.0)) AS total_revenue
        FROM `gen-lang-client-0738410622.marketing_data.botcake_leads`
        WHERE report_group = 'Y tế'
        GROUP BY 1, 2
        ORDER BY 1 DESC;
    """
    
    logger.info("Đang truy vấn BigQuery...")
    query_job = client.query(sql)
    rows = list(query_job.result())
    
    logger.info("=== KẾT QUẢ TRUY VẤN ===")
    logger.info(f"{'Tháng':<10} | {'Nhóm':<10} | {'Tổng Leads':<10} | {'Đặt lịch':<10} | {'Đến cửa':<10} | {'Doanh Thu (VNĐ)':<15}")
    logger.info("-" * 80)
    for r in rows:
        month = r.month or "None"
        rev = f"{r.total_revenue:,.0f}" if r.total_revenue else "0"
        logger.info(f"{month:<10} | {r.report_group:<10} | {r.total_leads:<10} | {r.total_bookings:<10} | {r.total_arrivals:<10} | {rev:<15}")

if __name__ == "__main__":
    main()
