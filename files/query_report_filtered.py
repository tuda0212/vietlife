import os
import logging
from google.cloud import bigquery
from config_crm import GCP_PROJECT_ID

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s — %(message)s")
logger = logging.getLogger("query_report_filtered")

def main():
    client = bigquery.Client(project=GCP_PROJECT_ID)
    
    # 1. Query v_report_y_te (Tổng quan)
    sql_summary = """
        SELECT 
            date,
            specialty_name,
            doctor_name,
            spend,
            sdts,
            dat_lich,
            den_cua,
            revenue
        FROM `gen-lang-client-0738410622.marketing_data.v_report_y_te`
        WHERE date BETWEEN '2026-06-01' AND '2026-06-17'
          AND specialty_code = 'CXK'
        ORDER BY date DESC, doctor_name;
    """
    
    # 2. Query tổng hợp toàn bộ khoảng ngày
    sql_total = """
        SELECT 
            specialty_name,
            doctor_name,
            SUM(spend) AS total_spend,
            SUM(sdts) AS total_sdts,
            SUM(dat_lich) AS total_dat_lich,
            SUM(den_cua) AS total_den_cua,
            SUM(revenue) AS total_revenue
        FROM `gen-lang-client-0738410622.marketing_data.v_report_y_te`
        WHERE date BETWEEN '2026-06-01' AND '2026-06-17'
          AND specialty_code = 'CXK'
        GROUP BY 1, 2
        ORDER BY total_spend DESC;
    """
    
    try:
        print("=== TRUY VẤN BÁO CÁO TỔNG HỢP (01/06 - 17/06) ===")
        query_total = client.query(sql_total)
        rows_total = list(query_total.result())
        
        print("\n| Chuyên khoa | Bác sĩ | Chi phí (VNĐ) | Số SĐT | Đặt lịch | Đến cửa | Doanh thu (VNĐ) | ROI (%) |")
        print("|---|---|---|---|---|---|---|---|")
        for r in rows_total:
            roi = (r.total_revenue / r.total_spend * 100) if r.total_spend else 0
            spend_fmt = f"{r.total_spend:,.0f}"
            rev_fmt = f"{r.total_revenue:,.0f}"
            print(f"| {r.specialty_name} | {r.doctor_name} | {spend_fmt} | {r.total_sdts} | {r.total_dat_lich} | {r.total_den_cua} | {rev_fmt} | {roi:.1f}% |")
            
        print("\n\n=== CHI TIẾT THEO NGÀY (01/06 - 17/06) ===")
        query_summary = client.query(sql_summary)
        rows_summary = list(query_summary.result())
        
        print("\n| Ngày | Bác sĩ | Chi phí (VNĐ) | Số SĐT | Đặt lịch | Đến cửa | Doanh thu (VNĐ) |")
        print("|---|---|---|---|---|---|---|")
        for r in rows_summary:
            spend_fmt = f"{r.spend:,.0f}"
            rev_fmt = f"{r.revenue:,.0f}"
            print(f"| {r.date} | {r.doctor_name} | {spend_fmt} | {r.sdts} | {r.dat_lich} | {r.den_cua} | {rev_fmt} |")
            
    except Exception as e:
        logger.error(f"Error executing query: {e}")

if __name__ == "__main__":
    main()
