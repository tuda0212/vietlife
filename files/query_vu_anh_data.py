import os
import logging
from google.cloud import bigquery
from config_crm import GCP_PROJECT_ID

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s — %(message)s")
logger = logging.getLogger("query_vu_anh")

def main():
    client = bigquery.Client(project=GCP_PROJECT_ID)
    
    # 1. Query tổng số lead, đặt lịch, đến cửa của BS Vũ Anh trong tháng 3/2026
    sql = """
        SELECT 
            doctor_name,
            COUNT(*) AS total_leads,
            COUNTIF(is_booking=True) AS total_bookings,
            COUNTIF(is_arrival=True) AS total_arrivals,
            SUM(IFNULL(revenue, 0.0)) AS total_revenue
        FROM `gen-lang-client-0738410622.marketing_data.botcake_leads`
        WHERE lead_date BETWEEN '2026-03-01' AND '2026-03-31'
          AND (doctor_name = 'BS Vũ Anh' OR page_id = '1IpRGhylPd4TENwT4tZq5mOZnTzLmttkn4l8FejWtNZE')
        GROUP BY 1;
    """
    logger.info("Chạy query kiểm tra dữ liệu BS Vũ Anh trong BigQuery...")
    try:
        query_job = client.query(sql)
        rows = list(query_job.result())
        print(f"Results for BS Vũ Anh (Month 3/2026):")
        if not rows:
            print("No data found.")
        for r in rows:
            print(f" - Doctor: {r.doctor_name}, Leads: {r.total_leads}, Bookings: {r.total_bookings}, Arrivals: {r.total_arrivals}, Revenue: {r.total_revenue:,.0f}")
            
        # 2. Query từ view v_report_y_te hoặc v_report_y_te_detail xem con số hiển thị thế nào
        sql_view = """
            SELECT 
                doctor_name,
                SUM(sdts) AS total_sdts,
                SUM(dat_lich) AS total_bookings,
                SUM(den_cua) AS total_arrivals,
                SUM(revenue) AS total_revenue
            FROM `gen-lang-client-0738410622.marketing_data.v_report_y_te_detail`
            WHERE start_date BETWEEN '2026-03-01' AND '2026-03-31'
              AND doctor_name = 'BS Vũ Anh'
            GROUP BY 1;
        """
        logger.info("Chạy query kiểm tra view v_report_y_te_detail cho BS Vũ Anh...")
        query_job_view = client.query(sql_view)
        rows_view = list(query_job_view.result())
        print(f"\nResults in v_report_y_te_detail for BS Vũ Anh (Month 3/2026):")
        if not rows_view:
            print("No data found.")
        for r in rows_view:
            print(f" - Doctor: {r.doctor_name}, SDTs: {r.total_sdts}, Bookings: {r.total_bookings}, Arrivals: {r.total_arrivals}, Revenue: {r.total_revenue:,.0f}")
            
    except Exception as e:
        logger.error(f"Error: {e}")

if __name__ == "__main__":
    main()
