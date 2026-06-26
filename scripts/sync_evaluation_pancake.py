#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script tổng hợp dữ liệu Facebook Ads (từ BigQuery) và Pancake Chats (gọi trực tiếp Pancake API)
để ghi vào bảng ad_content_evaluation trong BigQuery.
"""

import os
import sys
import time
import json
import logging
import argparse
import requests
import re
from pathlib import Path
from datetime import datetime, date, timedelta
from google.cloud import bigquery

# Regex để nhận diện số điện thoại
REGEX_PHONE = re.compile(r"0[35789]\d{8}|0[24]\d{8,9}")

# Thiết lập logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s"
)
logger = logging.getLogger("sync_evaluation_pancake")

PANCAKE_API_BASE = "https://pages.fm/api/public_api/v1"

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

def date_to_timestamp(date_str, is_end=False):
    if not date_str:
        return None
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        if is_end:
            dt = dt.replace(hour=23, minute=59, second=59)
        return int(dt.timestamp())
    except ValueError:
        return None

def split_date_range(start_date_str, end_date_str, max_days=15):
    start = datetime.strptime(start_date_str, "%Y-%m-%d").date()
    end = datetime.strptime(end_date_str, "%Y-%m-%d").date()
    
    ranges = []
    curr = start
    while curr <= end:
        next_curr = min(curr + timedelta(days=max_days - 1), end)
        ranges.append((curr.strftime("%Y-%m-%d"), next_curr.strftime("%Y-%m-%d")))
        curr = next_curr + timedelta(days=1)
    return ranges

def fetch_conversations(page_id, token, since_ts, until_ts, page=1, limit=100):
    url = f"{PANCAKE_API_BASE}/pages/{page_id}/conversations"
    params = {
        "page_access_token": token,
        "limit": limit,
        "page": page,
        "page_number": page,
        "since": since_ts,
        "until": until_ts
    }
    try:
        response = requests.get(url, params=params, timeout=15)
        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                return data.get("conversations", []), None
            else:
                msg = data.get("message", "Unknown error")
                logger.warning(f"[Pancake API] Lỗi từ API: {msg}")
                return [], msg
        elif response.status_code == 429:
            logger.warning("[Pancake API] Rate Limit. Đang đợi 30 giây...")
            time.sleep(30)
            return fetch_conversations(page_id, token, since_ts, until_ts, page, limit)
        else:
            return [], f"HTTP error {response.status_code}"
    except Exception as e:
        logger.error(f"[Pancake API] Lỗi kết nối: {e}")
        return [], str(e)

def analyze_pancake_data(start_date, end_date, pages_config):
    """
    Gọi Pancake API để lấy và phân tích các cuộc hội thoại
    Trả về: (pancake_stats, successful_pancake_doctors)
    """
    pancake_stats = {}
    successful_pancake_doctors = set()
    
    # Chia khoảng thời gian thành các khoảng nhỏ dưới 15 ngày để tránh giới hạn API
    date_ranges = split_date_range(start_date, end_date, max_days=15)
    logger.info(f"[*] Khoảng thời gian {start_date} ➔ {end_date} được chia thành các khoảng nhỏ để gọi Pancake API: {date_ranges}")

    for doc_key, cfg in pages_config.items():
        page_id = cfg.get("page_id")
        token = cfg.get("pancake_token")
        doctor_name = cfg.get("doctor_name")
        
        # Fallback to .env token if matches default page id
        env_page_id = os.getenv("PANCAKE_PAGE_ID")
        env_token = os.getenv("PANCAKE_PAGE_ACCESS_TOKEN") or os.getenv("FB_ACCESS_TOKEN")
        
        if (not token or "YOUR" in token) and page_id == env_page_id:
            token = env_token
            
        if not token or "YOUR" in token or not page_id:
            logger.info(f"[-] Bỏ qua Pancake cho {doctor_name} do thiếu API token hợp lệ.")
            continue
            
        logger.info(f"[*] Đang lấy dữ liệu Pancake cho {doctor_name} (Page ID: {page_id})...")
        
        has_api_error = False
        all_convs = []
        
        for sub_start, sub_end in date_ranges:
            since_ts = date_to_timestamp(sub_start)
            until_ts = date_to_timestamp(sub_end, is_end=True)
            
            page = 1
            while True:
                convs, err = fetch_conversations(page_id, token, since_ts, until_ts, page=page)
                if err:
                    logger.error(f"[-] Gặp lỗi khi gọi Pancake API cho {doctor_name}: {err}")
                    has_api_error = True
                    break
                if not convs:
                    break
                all_convs.extend(convs)
                if len(convs) < 100:
                    break
                page += 1
                time.sleep(0.3)
            
            if has_api_error:
                break
                
        if has_api_error:
            logger.warning(f"[-] Bỏ qua kết quả Pancake của {doctor_name} do API bị lỗi. Sẽ dùng SQL fallback riêng cho bác sĩ này.")
            continue
            
        successful_pancake_doctors.add(doctor_name)
        logger.info(f"   - Lấy thành công {len(all_convs)} cuộc hội thoại cho {doctor_name} từ {start_date} đến {end_date}.")
        
        # Phân tích từng cuộc hội thoại (lấy trực tiếp thông tin từ metadata của cuộc hội thoại, không gọi fetch_messages)
        for conv in all_convs:
            ads_list = conv.get("ads") or []
            # Chỉ phân tích các cuộc hội thoại có gắn với Ads (ad_id)
            if not ads_list:
                continue
                
            conv_type = conv.get("type", "inbox")
            
            # Lấy ngày hội thoại (UTC -> convert sang YYYY-MM-DD)
            inserted_at_str = conv.get("inserted_at")
            if not inserted_at_str:
                continue
            chat_date = inserted_at_str.split("T")[0]
            
            # Kiểm tra xem hội thoại có SĐT hay không trực tiếp từ trường của Pancake
            has_phone = conv.get("has_phone", False) or bool(conv.get("recent_phone_numbers"))
            
            # Kiểm tra xem Page đã trả lời chưa từ trường last_sent_by
            last_sent = conv.get("last_sent_by")
            has_reply = False
            if last_sent:
                if last_sent.get("id") == page_id or last_sent.get("admin_name"):
                    has_reply = True
            
            # Cập nhật thống kê theo từng ad_id và date
            for ad in ads_list:
                ad_id = ad.get("ad_id")
                if not ad_id:
                    continue
                
                key = (chat_date, ad_id)
                if key not in pancake_stats:
                    pancake_stats[key] = {
                        "pancake_chats": 0,
                        "qualified_chats": 0,
                        "leads": 0,
                        "pancake_comment": 0,
                        "reply_count": 0
                    }
                    
                stats = pancake_stats[key]
                stats["pancake_chats"] += 1
                
                if conv_type == "comment":
                    stats["pancake_comment"] += 1
                    
                if has_phone:
                    stats["qualified_chats"] += 1
                    stats["leads"] += 1
                    
                if has_reply:
                    stats["reply_count"] += 1

    return pancake_stats, successful_pancake_doctors

def fallback_sql_aggregation(client, project_id, dataset_id, table_ref, start_date, end_date):
    """
    Phương án dự phòng: Tổng hợp dữ liệu thuần túy bằng SQL từ fb_ad_insights và botcake_leads.
    """
    logger.info("[Fallback] Đang sử dụng cơ chế SQL để tổng hợp dữ liệu (do không có token Pancake)...")
    
    # Xóa dữ liệu cũ
    delete_sql = f"DELETE FROM `{table_ref}` WHERE date BETWEEN '{start_date}' AND '{end_date}'"
    client.query(delete_sql).result()
    
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
              WHEN REGEXP_CONTAINS(LOWER(COALESCE(a.ad_name, '')), 'feedback') THEN 'Feedback'
              WHEN REGEXP_CONTAINS(LOWER(COALESCE(a.ad_name, '')), 'chuyen_gia') THEN 'Chuyên gia'
              ELSE 'Unknown'
            END AS angle,
            
            CASE 
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
            
            IFNULL(a.mes, 0) + IFNULL(a.cmt, 0) AS pancake_chats,
            IFNULL(c.phone_count, 0) AS qualified_chats,
            IFNULL(c.phone_count, 0) AS leads,
            
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
    client.query(insert_sql).result()
    logger.info("[Fallback] Cập nhật bảng bằng cơ chế SQL thành công.")

def run_sync(start_date: str, end_date: str):
    project_id = os.getenv("GCP_PROJECT_ID", "gen-lang-client-0738410622")
    dataset_id = os.getenv("BQ_DATASET", "marketing_data")
    table_ref = f"{project_id}.{dataset_id}.ad_content_evaluation"

    client = bigquery.Client(project=project_id)

    # 1. Đọc pages_config.json
    config_path = workspace_root / ".agents" / "skills" / "ad-insight-alignment" / "scripts" / "pages_config.json"
    if not config_path.exists():
        example_path = config_path.with_suffix(".json.example")
        if example_path.exists():
            logger.info("[*] Đang copy file pages_config.json từ file mẫu...")
            config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(example_path, "r", encoding="utf-8") as f_ex:
                with open(config_path, "w", encoding="utf-8") as f_real:
                    f_real.write(f_ex.read())

    pages_config = {}
    if config_path.exists():
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                pages_config = json.load(f)
        except Exception as e:
            logger.error(f"Lỗi khi đọc file pages_config.json: {e}")

    # 2. Gọi Pancake API để lấy thống kê hội thoại thực tế
    pancake_stats = {}
    successful_pancake_doctors = set()
    try:
        pancake_stats, successful_pancake_doctors = analyze_pancake_data(start_date, end_date, pages_config)
    except Exception as e:
        logger.error(f"[Pancake API] Thất bại khi phân tích dữ liệu Pancake: {e}", exc_info=True)

    # Nếu không thu thập được bất kỳ bác sĩ nào thành công từ Pancake API, chuyển sang fallback dùng SQL thuần
    if not successful_pancake_doctors:
        logger.warning("[Pancake API] Không có bác sĩ nào lấy được dữ liệu thành công từ Pancake API. Sử dụng cơ chế SQL fallback.")
        fallback_sql_aggregation(client, project_id, dataset_id, table_ref, start_date, end_date)
        return

    # Luôn lấy dữ liệu CRM từ BigQuery để dùng cho hybrid fallback đối với những bác sĩ bị lỗi Pancake API
    logger.info(f"[*] Đang lấy dữ liệu CRM từ botcake_leads cho hybrid fallback...")
    crm_sql = f"""
        SELECT
          lead_date AS date,
          COALESCE(ad_id, 'organic') AS ad_id,
          doctor_name,
          COUNT(DISTINCT phone) AS phone_count
        FROM `{project_id}.{dataset_id}.botcake_leads`
        WHERE lead_date BETWEEN '{start_date}' AND '{end_date}'
        GROUP BY lead_date, COALESCE(ad_id, 'organic'), doctor_name
    """
    crm_map = {}
    try:
        crm_rows = [dict(r) for r in client.query(crm_sql).result()]
        for r in crm_rows:
            date_str = r['date'].strftime("%Y-%m-%d")
            doc_name_lower = r['doctor_name'].strip().lower() if r['doctor_name'] else ""
            crm_map[(date_str, r['ad_id'], doc_name_lower)] = r['phone_count']
        logger.info(f"   - Lấy được {len(crm_rows)} dòng CRM từ BigQuery để làm bản đồ fallback.")
    except Exception as e:
        logger.error(f"[-] Lỗi khi lấy dữ liệu CRM phục vụ fallback: {e}")

    # 3. Lấy dữ liệu Facebook Ads từ BigQuery
    logger.info(f"[*] Đang lấy dữ liệu Facebook Ads từ BigQuery: {start_date} ➔ {end_date}...")
    fb_sql = f"""
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
    """
    fb_rows = [dict(r) for r in client.query(fb_sql).result()]
    logger.info(f"   - Lấy được {len(fb_rows)} dòng quảng cáo từ BigQuery.")

    # 4. Gộp dữ liệu Facebook Ads và Pancake
    combined_data = []
    
    # Gom tất cả các key (date, ad_id) duy nhất
    all_keys = set((r["date"].strftime("%Y-%m-%d"), r["ad_id"]) for r in fb_rows)
    all_keys.update(pancake_stats.keys())
    
    # Map để tra cứu fb_rows nhanh
    fb_map = {(r["date"].strftime("%Y-%m-%d"), r["ad_id"]): r for r in fb_rows}
    
    # Tạo map bác sĩ từ pages_config để điền doctor/specialty cho dòng chỉ có ở Pancake
    page_to_doctor = {}
    for cfg in pages_config.values():
        p_id = cfg.get("page_id")
        if p_id:
            page_to_doctor[p_id] = {
                "doctor_name": cfg.get("doctor_name"),
                # Đoán chuyên khoa dựa trên tên bác sĩ hoặc gán mặc định
                "specialty_name": "Cột Sống" if "Tuyên" in cfg.get("doctor_name") or "Định" in cfg.get("doctor_name") else "Thần Kinh"
            }

    now_iso = datetime.utcnow().isoformat() + "Z"

    successful_pancake_doctors_lower = {name.lower().strip() for name in successful_pancake_doctors}

    for chat_date, ad_id in all_keys:
        fb_info = fb_map.get((chat_date, ad_id)) or {}
        doc_name = fb_info.get("doctor_name") or "Unknown"
        doc_name_lower = doc_name.strip().lower()
        
        # Kiểm tra xem bác sĩ của quảng cáo này có lấy dữ liệu Pancake API thành công không
        is_pancake_success = doc_name_lower in successful_pancake_doctors_lower
        p_info = pancake_stats.get((chat_date, ad_id))
        
        # Xác định doctor name và specialty
        spec_name = fb_info.get("specialty_name") or "Unknown"
        ad_name = fb_info.get("ad_name") or "Organic"
        
        # Parsing angles, format theo cú pháp mới: Angle_tên bài_id post fb
        # Ví dụ: HoiChungRuotKichThich_BaiViet1_1234567890
        parts = ad_name.split("_")
        
        if ad_name == "Organic":
            angle = "Organic"
            ad_post_name = "Organic"
        elif len(parts) >= 2:
            angle = parts[0].strip()
            ad_post_name = parts[1].strip()
        else:
            # Fallback logic cũ
            ad_name_lower = ad_name.lower()
            angle = "Unknown"
            if "feedback" in ad_name_lower:
                angle = "Feedback"
            elif "chuyen_gia" in ad_name_lower:
                angle = "Chuyên gia"
                
            ad_post_name = ad_name
            if "Feedback_" in ad_name:
                match = re.search(r"Feedback_(.*?)_", ad_name)
                if match:
                    ad_post_name = match.group(1)
                
        ad_format = "Video" if "video" in ad_name_lower else "Image"
        
        spend = fb_info.get("spend") or 0.0
        impressions = fb_info.get("impressions") or 0
        clicks = fb_info.get("clicks") or 0
        ctr = clicks / impressions if impressions > 0 else 0.0
        
        fb_mess = fb_info.get("mes") or 0
        fb_comment = fb_info.get("cmt") or 0
        fb_lead = fb_mess + fb_comment
        thruplay = fb_info.get("thruplay") or 0
        video_views = fb_info.get("video_views") or 0
        thruplay_rate = thruplay / video_views if video_views > 0 else 0.0

        if is_pancake_success and p_info:
            # Dùng dữ liệu Pancake API thật
            pancake_chats = p_info["pancake_chats"]
            qualified_chats = p_info["qualified_chats"]
            leads = p_info["leads"]
            pancake_comment = p_info["pancake_comment"]
            pancake_lead = pancake_chats  # Tổng chats
            reply_count = p_info["reply_count"]
        else:
            # Fallback sang SQL/CRM cho bác sĩ bị lỗi hoặc thiếu Pancake token
            pancake_chats = fb_mess + fb_comment
            pancake_comment = fb_comment
            pancake_lead = pancake_chats
            
            # Tra cứu CRM phone count làm số điện thoại
            leads = crm_map.get((chat_date, ad_id, doc_name_lower), 0)
            qualified_chats = leads
            reply_count = qualified_chats # Giả lập reply
            
        reply_rate = reply_count / pancake_chats if pancake_chats > 0 else 0.0
        lead_rate = leads / pancake_chats if pancake_chats > 0 else 0.0
        
        cost_per_lead = spend / pancake_lead if pancake_lead > 0 else 0.0
        cost_per_phone = spend / leads if leads > 0 else 0.0

        row = {
            "date": chat_date,
            "specialty_name": spec_name,
            "doctor_name": doc_name,
            "ad_id": ad_id,
            "ad_name": ad_name,
            "angle": angle,
            "ad_post_name": ad_post_name,
            "ad_format": ad_format,
            "impressions": impressions,
            "clicks": clicks,
            "ctr": ctr,
            "fb_mess": fb_mess,
            "thruplay": thruplay,
            "video_views": video_views,
            "thruplay_rate": thruplay_rate,
            "retention_rate": 0.0,
            "spend": spend,
            "pancake_chats": pancake_chats,
            "qualified_chats": qualified_chats,
            "reply_rate": reply_rate,
            "leads": leads,
            "lead_rate": lead_rate,
            "inserted_at": now_iso,
            "fb_comment": fb_comment,
            "fb_lead": fb_lead,
            "pancake_comment": pancake_comment,
            "pancake_lead": pancake_lead,
            "cost_per_lead": cost_per_lead,
            "cost_per_phone": cost_per_phone
        }
        combined_data.append(row)

    # 5. Ghi dữ liệu vào BigQuery
    logger.info(f"[*] Xóa dữ liệu cũ của bảng {table_ref} từ {start_date} đến {end_date}...")
    del_job = client.query(f"DELETE FROM `{table_ref}` WHERE date BETWEEN '{start_date}' AND '{end_date}'")
    del_job.result()
    
    logger.info(f"[*] Đang chèn {len(combined_data)} dòng tổng hợp mới vào BigQuery...")
    table = client.get_table(table_ref)
    job_config = bigquery.LoadJobConfig(
        write_disposition=bigquery.WriteDisposition.WRITE_APPEND,
        source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
        autodetect=False,
    )
    ndjson = "\n".join(json.dumps(row, default=str) for row in combined_data)
    
    import io
    load_job = client.load_table_from_file(
        io.BytesIO(ndjson.encode("utf-8")), 
        table, 
        job_config=job_config
    )
    load_job.result()
    
    if load_job.errors:
        logger.error(f"Lỗi khi load vào BigQuery: {load_job.errors}")
        raise RuntimeError(f"BigQuery load errors: {load_job.errors}")
        
    logger.info(f"🎉 HOÀN THÀNH CẬP NHẬT BẢNG EVALUATION VỚI PANCAKE! Đã chèn {load_job.output_rows} dòng.")

def main():
    parser = argparse.ArgumentParser(description="Update BigQuery ad_content_evaluation with Facebook and Pancake API.")
    parser.add_argument("--start-date", help="Ngày bắt đầu (YYYY-MM-DD)")
    parser.add_argument("--end-date", help="Ngày kết thúc (YYYY-MM-DD)")
    args = parser.parse_args()

    # Mặc định 7 ngày gần nhất nếu không truyền
    today = date.today()
    start_date = args.start_date or (today - timedelta(days=7)).strftime("%Y-%m-%d")
    end_date = args.end_date or today.strftime("%Y-%m-%d")

    run_sync(start_date, end_date)

if __name__ == "__main__":
    main()
