#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
scripts/sync_ad_content_evaluation.py
Dong bo du lieu danh gia noi dung quang cao tu dau nam den nay vao BigQuery.
Ghep noi du lieu Facebook Ads (tu BigQuery) va Pancake Chats (tu Pancake API) theo ad_id + date.
"""

import os
import sys
import json
import time
import argparse
import logging
import requests
from datetime import datetime, date, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
from google.cloud import bigquery
from google.cloud.exceptions import NotFound

# Thiet lap log khong dau de tranh loi encoding tren Windows console
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("sync_ad_content_evaluation")

# Cau hinh duong dan credentials GCP mac dinh tim thay tren may
ADC_PATH = r"C:\Users\Admin\AppData\Local\google-vscode-extension\auth\application_default_credentials.json"
if os.path.exists(ADC_PATH):
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = ADC_PATH
    logger.info(f"[GCP Auth] Da thiet lap GOOGLE_APPLICATION_CREDENTIALS tro toi: {ADC_PATH}")
else:
    logger.warning(f"[GCP Auth] Khong tim thay file credentials tai {ADC_PATH}. Se dung mac dinh he thong.")

# Cau hinh du an
PROJECT_ID = "gen-lang-client-0738410622"
DATASET_ID = "marketing_data"
TARGET_TABLE_ID = "ad_content_evaluation"
FB_INSIGHTS_TABLE = f"{PROJECT_ID}.{DATASET_ID}.fb_ad_insights"

# Pancake API Endpoint
PANCAKE_API_BASE = "https://pages.fm/api/public_api/v1"

def remove_accents(input_str):
    if not input_str:
        return ""
    s1 = "ÀÁÂÃÈÉÊÌÍÒÓÔÕÙÚÝàáâãèéêìíòóôõùúýĂăĐđĨĩŨũƠơƯưẠạẢảẤấẦầẨẩẪẫẬậẮắẰằẲẳẴẵẬậẸẹẺẻẼẽẾếỀềỂểỄễỆệỈỉỊịỌọỎỏỐốỒồỔổỖỗỘộỚớỜờỞởỠỡỢợỤụỦủỨứỪừỬửỮữỰựỲỳỶỷỸỹ"
    s2 = "AAAAEEEIIOOOOUUYaaaaeeeiiOOOOUUYaaDdIiUuOoUuAaAaAaAaAaAaAaAaAaAaAaAaEeEeEeEeEeEeEeEeIiIiOoOoOoOoOoOoOoOoOoOoOoOoUuUuUuUuUuUuUuYyYyYy"
    trans = str.maketrans(s1, s2)
    return input_str.translate(trans)

def parse_ad_name(ad_name):
    """
    Trich xuat Angle va Ad Post Name tu ad_name dua tren ky tu phan tach _
    """
    if not ad_name:
        return "Unknown", "Unknown"
    
    # Split va lam sach khoang trang
    parts = [p.strip() for p in ad_name.split("_") if p.strip()]
    
    if len(parts) >= 3:
        # Dang Angle_TenBai_ID
        angle = parts[0]
        post_name = parts[1]
        return angle, post_name
    elif len(parts) == 2:
        # Dang TenBai_ID hoac Angle_ID
        # Neu phan 2 la so (ID) thi phan 1 la ten bai
        if parts[1].isdigit() or len(parts[1]) > 10:
            return "Unknown", parts[0]
        else:
            return parts[0], parts[1]
    else:
        # Chi co 1 phan hoac khong theo chuan
        if parts and (parts[0].isdigit() or len(parts[0]) > 10):
            return "Unknown", "Unknown"
        return "Unknown", parts[0] if parts else "Unknown"

def get_bigquery_client():
    return bigquery.Client(project=PROJECT_ID)

def create_target_table_if_not_exists(client):
    table_ref = f"{PROJECT_ID}.{DATASET_ID}.{TARGET_TABLE_ID}"
    try:
        client.get_table(table_ref)
        logger.info(f"[BQ] Bang {table_ref} da ton tai.")
    except NotFound:
        logger.info(f"[BQ] Khong tim thay bang {table_ref}. Tien hanh tao moi...")
        schema = [
            bigquery.SchemaField("date", "DATE", mode="REQUIRED"),
            bigquery.SchemaField("specialty_name", "STRING", mode="NULLABLE"),
            bigquery.SchemaField("doctor_name", "STRING", mode="NULLABLE"),
            bigquery.SchemaField("ad_id", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("ad_name", "STRING", mode="NULLABLE"),
            bigquery.SchemaField("angle", "STRING", mode="NULLABLE"),
            bigquery.SchemaField("ad_post_name", "STRING", mode="NULLABLE"),
            bigquery.SchemaField("ad_format", "STRING", mode="NULLABLE"),
            bigquery.SchemaField("impressions", "INTEGER", mode="NULLABLE"),
            bigquery.SchemaField("clicks", "INTEGER", mode="NULLABLE"),
            bigquery.SchemaField("ctr", "FLOAT", mode="NULLABLE"),
            bigquery.SchemaField("fb_mess", "INTEGER", mode="NULLABLE"),
            bigquery.SchemaField("thruplay", "INTEGER", mode="NULLABLE"),
            bigquery.SchemaField("video_views", "INTEGER", mode="NULLABLE"),
            bigquery.SchemaField("thruplay_rate", "FLOAT", mode="NULLABLE"),
            bigquery.SchemaField("retention_rate", "FLOAT", mode="NULLABLE"),
            bigquery.SchemaField("spend", "FLOAT", mode="NULLABLE"),
            bigquery.SchemaField("pancake_chats", "INTEGER", mode="NULLABLE"),
            bigquery.SchemaField("qualified_chats", "INTEGER", mode="NULLABLE"),
            bigquery.SchemaField("reply_rate", "FLOAT", mode="NULLABLE"),
            bigquery.SchemaField("leads", "INTEGER", mode="NULLABLE"),
            bigquery.SchemaField("lead_rate", "FLOAT", mode="NULLABLE"),
            bigquery.SchemaField("inserted_at", "TIMESTAMP", mode="REQUIRED")
        ]
        table = bigquery.Table(table_ref, schema=schema)
        # Phan vung theo cot date
        table.time_partitioning = bigquery.TimePartitioning(
            type_=bigquery.TimePartitioningType.DAY,
            field="date"
        )
        client.create_table(table)
        logger.info(f"[BQ] Tao bang {table_ref} thanh cong.")

def get_facebook_ads_data(client, start_date, end_date):
    """
    Truy van du lieu Facebook Ads daily tu BigQuery
    """
    logger.info(f"[BQ] Dang truy van du lieu Facebook Ads tu {start_date} den {end_date}...")
    query = f"""
        SELECT 
          start_date as date,
          specialty_name,
          doctor_name,
          ad_id,
          ad_name,
          SUM(impressions) as impressions,
          SUM(clicks) as clicks,
          SUM(spend) as spend,
          SUM(mes) as fb_mess,
          SUM(thruplay) as thruplay,
          SUM(video_views) as video_views,
          SUM(video_100) as video_100
        FROM `{FB_INSIGHTS_TABLE}`
        WHERE start_date BETWEEN '{start_date}' AND '{end_date}'
        GROUP BY date, specialty_name, doctor_name, ad_id, ad_name
    """
    query_job = client.query(query)
    results = query_job.result()
    
    ads_data = {}
    for row in results:
        date_str = row.date.strftime("%Y-%m-%d")
        key = (row.ad_id, date_str)
        
        ads_data[key] = {
            "specialty_name": row.specialty_name,
            "doctor_name": row.doctor_name,
            "ad_name": row.ad_name,
            "impressions": row.impressions or 0,
            "clicks": row.clicks or 0,
            "spend": row.spend or 0.0,
            "fb_mess": row.fb_mess or 0,
            "thruplay": row.thruplay or 0,
            "video_views": row.video_views or 0,
            "video_100": row.video_100 or 0
        }
    logger.info(f"[BQ] Lay duoc {len(ads_data)} ban ghi Ads tu BigQuery.")
    return ads_data

def fetch_messages_count(page_id, conversation_id, token, customer_id):
    """
    Goi Pancake API de lay tin nhan va dem so tin nhan cua khach hang
    """
    url = f"{PANCAKE_API_BASE}/pages/{page_id}/conversations/{conversation_id}/messages"
    params = {
        "page_access_token": token,
        "limit": 50
    }
    try:
        response = requests.get(url, params=params, timeout=15)
        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                messages = data.get("messages", [])
                customer_msgs = sum(1 for m in messages if m.get("from", {}).get("id") == customer_id)
                return customer_msgs
        elif response.status_code == 429:
            logger.warning(f"[Pancake API] Rate Limit khi lay tin nhan cuoc chat {conversation_id}. Doi 10s...")
            time.sleep(10)
            return fetch_messages_count(page_id, conversation_id, token, customer_id)
    except Exception as e:
        logger.error(f"[Pancake API] Loi khi lay tin nhan cho cuoc chat {conversation_id}: {e}")
    return 0

def fetch_pancake_chats_for_page(page_id, token, doctor_name, since_ts, until_ts):
    """
    Tai toan bo hoi thoai tu Pancake trong khoang thoi gian cho 1 page (ho tro phan doan 30 ngay)
    """
    logger.info(f"[Pancake API] Bat dau tai hoi thoai cua trang: {remove_accents(doctor_name)} (ID: {page_id})...")
    
    # Chia thoi gian thanh cac khoang toi da 30 ngay vi Pancake API gioi han khoang date range < 1 thang
    chunks = []
    current_since = since_ts
    thirty_days_sec = 30 * 24 * 60 * 60
    
    while current_since < until_ts:
        current_until = min(current_since + thirty_days_sec, until_ts)
        chunks.append((current_since, current_until))
        current_since = current_until + 1
        
    all_ads_conversations = []
    
    for sub_since, sub_until in chunks:
        sub_since_str = datetime.fromtimestamp(sub_since).strftime("%Y-%m-%d")
        sub_until_str = datetime.fromtimestamp(sub_until).strftime("%Y-%m-%d")
        logger.info(f"[Pancake API] Tai du lieu segment: {sub_since_str} -> {sub_until_str}...")
        
        page = 1
        while True:
            url = f"{PANCAKE_API_BASE}/pages/{page_id}/conversations"
            params = {
                "page_access_token": token,
                "limit": 50,
                "type": "inbox",
                "since": sub_since,
                "until": sub_until,
                "page": page,
                "page_number": page
            }
            
            try:
                response = requests.get(url, params=params, timeout=15)
                if response.status_code == 200:
                    data = response.json()
                    if not data.get("success"):
                        logger.error(f"[Pancake API] Loi tu API: {data.get('message')}")
                        break
                    
                    convs = data.get("conversations", [])
                    if not convs:
                        break
                    
                    all_older = True
                    for conv in convs:
                        updated_at_str = conv.get("updated_at")
                        if updated_at_str:
                            updated_at_str = updated_at_str.replace("Z", "")
                            try:
                                dt = datetime.fromisoformat(updated_at_str)
                            except ValueError:
                                try:
                                    dt = datetime.strptime(updated_at_str, "%Y-%m-%d %H:%M:%S")
                                except ValueError:
                                    dt = datetime.now()
                            
                            if dt.timestamp() >= sub_since:
                                all_older = False
                                
                        if conv.get("ad_ids") or conv.get("ads"):
                            all_ads_conversations.append(conv)
                    
                    if all_older:
                        logger.info(f"[Pancake API] Trang {page} segment nay chua toan bo hoi thoai cu hon start. Dung phan trang segment.")
                        break
                    
                    logger.info(f"[Pancake API] Trang {page} segment: Tim thay {len(convs)} hoi thoai, giu {len([c for c in convs if c.get('ad_ids') or c.get('ads')])} tu Ads.")
                    page += 1
                    time.sleep(0.1)
                    
                elif response.status_code == 429:
                    logger.warning(f"[Pancake API] Gap Rate Limit. Dang cho 30 giay...")
                    time.sleep(30)
                    continue
                else:
                    logger.error(f"[Pancake API] HTTP Error: {response.status_code} - {response.text}")
                    break
            except Exception as e:
                logger.error(f"[Pancake API] Loi ket noi khi tai trang {page}: {e}")
                break
            
    logger.info(f"[Pancake API] Hoan thanh tai. Tong so hoi thoai tu Ads: {len(all_ads_conversations)}")
    
    chats_to_fetch = []
    for conv in all_ads_conversations:
        msg_count = conv.get("message_count", 0)
        if msg_count >= 2:
            chats_to_fetch.append(conv)
            
    logger.info(f"[Pancake API] Tien hanh kiem tra tin nhan chi tiet cho {len(chats_to_fetch)} cuoc hoi thoai co message_count >= 2...")
    
    conv_qualified_map = {}
    
    with ThreadPoolExecutor(max_workers=15) as executor:
        future_to_conv = {}
        for conv in chats_to_fetch:
            conv_id = conv["id"]
            customer_id = conv.get("from", {}).get("id")
            future = executor.submit(fetch_messages_count, page_id, conv_id, token, customer_id)
            future_to_conv[future] = conv_id
            
        for future in as_completed(future_to_conv):
            conv_id = future_to_conv[future]
            try:
                cust_msg_cnt = future.result()
                conv_qualified_map[conv_id] = (cust_msg_cnt >= 2)
            except Exception as exc:
                logger.error(f"[Pancake API] Loi lay messages cua {conv_id}: {exc}")
                conv_qualified_map[conv_id] = False
                
    pancake_grouped = {}
    
    for conv in all_ads_conversations:
        ad_ids = conv.get("ad_ids") or [a.get("ad_id") for a in (conv.get("ads") or []) if a.get("ad_id")]
        if not ad_ids:
            continue
            
        ad_id = ad_ids[0]
        
        inserted_at_str = conv.get("inserted_at")
        if not inserted_at_str:
            continue
        date_str = inserted_at_str.split("T")[0]
        
        try:
            conv_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            continue
            
        key = (ad_id, date_str)
        if key not in pancake_grouped:
            pancake_grouped[key] = {
                "pancake_chats": 0,
                "qualified_chats": 0,
                "leads": 0
            }
            
        stats = pancake_grouped[key]
        stats["pancake_chats"] += 1
        
        conv_id = conv["id"]
        is_qualified = conv_qualified_map.get(conv_id, False)
        if is_qualified:
            stats["qualified_chats"] += 1
            
        has_phone = conv.get("has_phone", False) or len(conv.get("recent_phone_numbers") or []) > 0
        if has_phone:
            stats["leads"] += 1
            
    logger.info(f"[Pancake API] Gom nhom thanh cong {len(pancake_grouped)} cap (ad_id, date) Pancake chat.")
    return pancake_grouped

def main():
    parser = argparse.ArgumentParser(description="Dong bo du lieu danh gia noi dung quang cao vao BigQuery.")
    parser.add_argument("--start-date", help="Ngay bat dau (YYYY-MM-DD), mac dinh: 2026-01-01")
    parser.add_argument("--end-date", help="Ngay ket thu (YYYY-MM-DD), mac dinh: hom nay")
    args = parser.parse_args()
    
    today_str = date.today().strftime("%Y-%m-%d")
    start_date_str = args.start_date or "2026-01-01"
    end_date_str = args.end_date or today_str
    
    start_dt = datetime.strptime(start_date_str, "%Y-%m-%d")
    end_dt = datetime.strptime(end_date_str, "%Y-%m-%d")
    
    since_ts = int(start_dt.timestamp())
    until_ts = int((end_dt + timedelta(days=1)).timestamp()) - 1
    
    logger.info(f"[Pipeline] BAT DAU DONG BO: {start_date_str} -> {end_date_str}")
    
    config_path = r"e:\vietlife\.agents\skills\ad-insight-alignment\scripts\pages_config.json"
    if not os.path.exists(config_path):
        logger.error(f"Khong tim thay tep cau hinh bac si tai: {config_path}")
        sys.exit(1)
        
    with open(config_path, "r", encoding="utf-8") as f:
        pages_config = json.load(f)
        
    logger.info(f"[Config] Doc thanh cong cau hinh cua {len(pages_config)} bac si.")
    
    bq_client = get_bigquery_client()
    create_target_table_if_not_exists(bq_client)
    
    ads_data = get_facebook_ads_data(bq_client, start_date_str, end_date_str)
    
    all_pancake_data = {}
    for doc_key, config in pages_config.items():
        page_id = config.get("page_id")
        pancake_token = config.get("pancake_token")
        doctor_name = config.get("doctor_name")
        
        if not page_id or not pancake_token:
            logger.warning(f"Bac si {remove_accents(doctor_name)} thieu page_id hoac pancake_token. Bo qua.")
            continue
            
        page_pancake_data = fetch_pancake_chats_for_page(page_id, pancake_token, doctor_name, since_ts, until_ts)
        
        for key, stats in page_pancake_data.items():
            if key not in all_pancake_data:
                all_pancake_data[key] = {
                    "pancake_chats": 0,
                    "qualified_chats": 0,
                    "leads": 0
                }
            all_pancake_data[key]["pancake_chats"] += stats["pancake_chats"]
            all_pancake_data[key]["qualified_chats"] += stats["qualified_chats"]
            all_pancake_data[key]["leads"] += stats["leads"]
            
    logger.info("[Pipeline] Dang tien hanh ghep noi du lieu Ads va Pancake...")
    
    all_keys = set(ads_data.keys()).union(all_pancake_data.keys())
    logger.info(f"[Pipeline] Tong cong co {len(all_keys)} cap (ad_id, date) can xu ly.")
    
    final_rows = []
    now_iso = datetime.utcnow().isoformat() + "Z"
    
    for key in all_keys:
        ad_id, date_str = key
        
        ad_stats = ads_data.get(key, {})
        pan_stats = all_pancake_data.get(key, {})
        
        specialty_name = ad_stats.get("specialty_name", "")
        doctor_name = ad_stats.get("doctor_name", "")
        ad_name = ad_stats.get("ad_name", "")
        
        if not ad_name:
            for k_other, stats_other in ads_data.items():
                if k_other[0] == ad_id:
                    specialty_name = stats_other.get("specialty_name", "")
                    doctor_name = stats_other.get("doctor_name", "")
                    ad_name = stats_other.get("ad_name", "")
                    break
                    
        if not ad_name:
            ad_name = ad_id
            
        angle, ad_post_name = parse_ad_name(ad_name)
        
        impressions = ad_stats.get("impressions", 0)
        clicks = ad_stats.get("clicks", 0)
        spend = ad_stats.get("spend", 0.0)
        fb_mess = ad_stats.get("fb_mess", 0)
        thruplay = ad_stats.get("thruplay", 0)
        video_views = ad_stats.get("video_views", 0)
        
        pancake_chats = pan_stats.get("pancake_chats", 0)
        qualified_chats = pan_stats.get("qualified_chats", 0)
        leads = pan_stats.get("leads", 0)
        
        ctr = (clicks / impressions) if impressions > 0 else 0.0
        thruplay_rate = (thruplay / impressions) if impressions > 0 else 0.0
        retention_rate = (thruplay / video_views) if video_views > 0 else 0.0
        reply_rate = (qualified_chats / pancake_chats) if pancake_chats > 0 else 0.0
        lead_rate = (leads / qualified_chats) if qualified_chats > 0 else 0.0
        
        ad_format = "Video" if (thruplay > 0 or video_views > 0) else "Image"
        
        if spend == 0 and impressions == 0 and pancake_chats == 0:
            continue
            
        row = {
            "date": date_str,
            "specialty_name": specialty_name,
            "doctor_name": doctor_name,
            "ad_id": ad_id,
            "ad_name": ad_name,
            "angle": angle,
            "ad_post_name": ad_post_name,
            "ad_format": ad_format,
            "impressions": int(impressions),
            "clicks": int(clicks),
            "ctr": float(ctr),
            "fb_mess": int(fb_mess),
            "thruplay": int(thruplay),
            "video_views": int(video_views),
            "thruplay_rate": float(thruplay_rate),
            "retention_rate": float(retention_rate),
            "spend": float(spend),
            "pancake_chats": int(pancake_chats),
            "qualified_chats": int(qualified_chats),
            "reply_rate": float(reply_rate),
            "leads": int(leads),
            "lead_rate": float(lead_rate),
            "inserted_at": now_iso
        }
        final_rows.append(row)
        
    logger.info(f"[Pipeline] Gom duoc {len(final_rows)} dong du lieu tong hop sach.")
    
    if not final_rows:
        logger.warning("[Pipeline] Khong co dong nao de luu. Ket thuc.")
        return
        
    table_ref = f"{PROJECT_ID}.{DATASET_ID}.{TARGET_TABLE_ID}"
    
    logger.info(f"[BQ] Xoa du lieu cu trong bang {TARGET_TABLE_ID} tu {start_date_str} to {end_date_str}...")
    delete_sql = f"""
        DELETE FROM `{table_ref}`
        WHERE date BETWEEN '{start_date_str}' AND '{end_date_str}'
    """
    bq_client.query(delete_sql).result()
    logger.info("[BQ] Xoa du lieu cu thanh cong.")
    
    logger.info(f"[BQ] Dang ghi {len(final_rows)} dong vao bang {TARGET_TABLE_ID}...")
    table = bq_client.get_table(table_ref)
    job_config = bigquery.LoadJobConfig(
        write_disposition=bigquery.WriteDisposition.WRITE_APPEND,
        source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
        autodetect=False,
    )
    ndjson_data = "\n".join(json.dumps(row) for row in final_rows)
    import io
    buffer = io.BytesIO(ndjson_data.encode("utf-8"))
    load_job = bq_client.load_table_from_file(buffer, table, job_config=job_config)
    load_job.result()
    
    if load_job.errors:
        logger.error(f"[BQ] Loi chen du lieu: {load_job.errors}")
        sys.exit(1)
        
    logger.info(f"[Pipeline] DONG BO THANH CONG! Da nap {load_job.output_rows} dong vao BigQuery.")

if __name__ == "__main__":
    main()
