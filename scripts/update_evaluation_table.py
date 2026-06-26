#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script tổng hợp dữ liệu từ fb_ad_insights và botcake_leads
sau đó ghi đè trực tiếp vào bảng ad_content_evaluation trong BigQuery.
"""

import os
import sys
import logging
import argparse
from pathlib import Path
from datetime import date, timedelta
from google.cloud import bigquery

# 1. Load biến môi trường từ file .env
workspace_root = Path(__file__).resolve().parent.parent
env_file = workspace_root / ".env"
if not env_file.exists():
    env_file = Path("/Users/daudau/VL/.env")

if env_file.exists():
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                os.environ.setdefault(key.strip(), value.strip())

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s"
)
logger = logging.getLogger("update_evaluation")

def run_update(start_date: str, end_date: str):
    project_id = os.getenv("GCP_PROJECT_ID", "gen-lang-client-0738410622")
    dataset_id = os.getenv("BQ_DATASET", "marketing_data")
    table_name = "ad_content_evaluation"
    table_ref = f"{project_id}.{dataset_id}.{table_name}"

    client = bigquery.Client(project=project_id)

    logger.info(f"[*] Bắt đầu cập nhật bảng {table_ref} từ {start_date} đến {end_date}...")

    # Step 1: Xóa dữ liệu cũ trong khoảng ngày
    delete_sql = f"""
        DELETE FROM `{table_ref}`
        WHERE date BETWEEN '{start_date}' AND '{end_date}'
    """
    logger.info(f"[1/2] Đang xóa dữ liệu cũ: {start_date} ➔ {end_date}...")
    delete_job = client.query(delete_sql)
    delete_job.result()
    logger.info(f"[1/2] Xóa thành công.")

    # Step 2: Tổng hợp và chèn dữ liệu mới
    insert_sql = f"""
        INSERT INTO `{table_ref}` (
          date, specialty_name, doctor_name, ad_id, ad_name, angle, ad_post_name, ad_format,
          impressions, clicks, ctr, fb_mess, thruplay, video_views, thruplay_rate, retention_rate,
          spend, pancake_chats, qualified_chats, reply_rate, leads, lead_rate, inserted_at,
          fb_comment, fb_lead, pancake_comment, pancake_lead, cost_per_lead, cost_per_phone
        )
        WITH ads_daily AS (
          SELECT
            start_date AS date,
            ad_id,
            MAX(ad_name) AS ad_name,
            MAX(specialty_name) AS specialty_name,
            MAX(doctor_name) AS doctor_name,
            SUM(spend) AS spend,
            SUM(clicks) AS clicks,
            SUM(impressions) AS impressions,
            SUM(mes) AS mes,
            SUM(cmt) AS cmt,
            SUM(video_views) AS video_views,
            SUM(thruplay) AS thruplay,
            SUM(video_100) AS video_100
          FROM `{project_id}.{dataset_id}.fb_ad_insights`
          WHERE start_date BETWEEN '{start_date}' AND '{end_date}'
          GROUP BY start_date, ad_id
        ),
        crm_daily AS (
          SELECT
            lead_date AS date,
            COALESCE(ad_id, 'organic') AS ad_id,
            MAX(doctor_name) AS doctor_name,
            MAX(specialty_name) AS specialty_name,
            COUNT(DISTINCT phone) AS phone_count
          FROM `{project_id}.{dataset_id}.botcake_leads`
          WHERE lead_date BETWEEN '{start_date}' AND '{end_date}'
          GROUP BY lead_date, COALESCE(ad_id, 'organic')
        ),
        all_keys AS (
          SELECT date, ad_id FROM ads_daily
          UNION DISTINCT
          SELECT date, ad_id FROM crm_daily
        ),
        combined AS (
          SELECT
            k.date,
            COALESCE(a.specialty_name, c.specialty_name, 'Unknown') AS specialty_name,
            COALESCE(a.doctor_name, c.doctor_name, 'Unknown') AS doctor_name,
            k.ad_id,
            COALESCE(a.ad_name, 'Organic') AS ad_name,
            
            CASE 
              WHEN a.ad_name = 'Organic' THEN 'Organic'
              WHEN ARRAY_LENGTH(SPLIT(a.ad_name, '_')) >= 2 THEN SPLIT(a.ad_name, '_')[OFFSET(0)]
              WHEN REGEXP_CONTAINS(LOWER(COALESCE(a.ad_name, '')), 'feedback') THEN 'Feedback'
              WHEN REGEXP_CONTAINS(LOWER(COALESCE(a.ad_name, '')), 'chuyen_gia') THEN 'Chuyên gia'
              ELSE 'Unknown'
            END AS angle,
            
            CASE 
              WHEN a.ad_name = 'Organic' THEN 'Organic'
              WHEN ARRAY_LENGTH(SPLIT(a.ad_name, '_')) >= 2 THEN SPLIT(a.ad_name, '_')[OFFSET(1)]
              WHEN REGEXP_CONTAINS(COALESCE(a.ad_name, ''), 'Feedback_') THEN REGEXP_EXTRACT(a.ad_name, r'Feedback_(.*?)_')
              ELSE COALESCE(a.ad_name, 'Organic')
            END AS ad_post_name,
            
            CASE 
              WHEN REGEXP_CONTAINS(LOWER(COALESCE(a.ad_name, '')), 'video') THEN 'Video'
              ELSE 'Image'
            END AS ad_format,
            
            IFNULL(a.impressions, 0) AS impressions,
            IFNULL(a.clicks, 0) AS clicks,
            IFNULL(a.mes, 0) AS fb_mess,
            IFNULL(a.thruplay, 0) AS thruplay,
            IFNULL(a.video_views, 0) AS video_views,
            IFNULL(a.spend, 0.0) AS spend,
            
            -- pancake_chats: giả lập bằng mes + cmt
            IFNULL(a.mes, 0) + IFNULL(a.cmt, 0) AS pancake_chats,
            
            -- qualified_chats: giả lập bằng lead CRM
            IFNULL(c.phone_count, 0) AS qualified_chats,
            
            -- leads: số SĐT CRM
            IFNULL(c.phone_count, 0) AS leads,
            
            -- Cột mới nâng cấp:
            IFNULL(a.cmt, 0) AS fb_comment,
            IFNULL(a.mes, 0) + IFNULL(a.cmt, 0) AS fb_lead,
            IFNULL(a.cmt, 0) AS pancake_comment,
            IFNULL(a.mes, 0) + IFNULL(a.cmt, 0) AS pancake_lead
            
          FROM all_keys k
          LEFT JOIN ads_daily a ON k.ad_id = a.ad_id AND k.date = a.date
          LEFT JOIN crm_daily c ON k.ad_id = c.ad_id AND k.date = c.date
        )
        SELECT 
          date,
          specialty_name,
          doctor_name,
          ad_id,
          ad_name,
          angle,
          COALESCE(ad_post_name, ad_name) AS ad_post_name,
          ad_format,
          impressions,
          clicks,
          ROUND(SAFE_DIVIDE(clicks, impressions), 4) AS ctr,
          fb_mess,
          thruplay,
          video_views,
          ROUND(SAFE_DIVIDE(thruplay, video_views), 4) AS thruplay_rate,
          0.0 AS retention_rate,
          spend,
          pancake_chats,
          qualified_chats,
          ROUND(SAFE_DIVIDE(qualified_chats, pancake_chats), 4) AS reply_rate,
          leads,
          ROUND(SAFE_DIVIDE(leads, pancake_chats), 4) AS lead_rate,
          CURRENT_TIMESTAMP() AS inserted_at,
          fb_comment,
          fb_lead,
          pancake_comment,
          pancake_lead,
          ROUND(SAFE_DIVIDE(spend, pancake_lead), 2) AS cost_per_lead,
          ROUND(SAFE_DIVIDE(spend, leads), 2) AS cost_per_phone
        FROM combined
    """
    logger.info("[2/2] Đang chèn dữ liệu mới...")
    insert_job = client.query(insert_sql)
    insert_job.result()
    logger.info("[2/2] Chèn dữ liệu mới thành công.")
    logger.info("🎉 HOÀN THÀNH CẬP NHẬT BẢNG EVALUATION!")

def main():
    parser = argparse.ArgumentParser(description="Update BigQuery ad_content_evaluation table.")
    parser.add_argument("--start-date", help="Ngày bắt đầu (YYYY-MM-DD)")
    parser.add_argument("--end-date", help="Ngày kết thúc (YYYY-MM-DD)")
    args = parser.parse_args()

    # Mặc định lấy từ đầu tháng đến hiện tại nếu không chỉ định
    today = date.today()
    if not args.start_date:
        start_date = today.replace(day=1).strftime("%Y-%m-%d")
    else:
        start_date = args.start_date

    if not args.end_date:
        end_date = today.strftime("%Y-%m-%d")
    else:
        end_date = args.end_date

    run_update(start_date, end_date)

if __name__ == "__main__":
    main()
