#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script tổng hợp dữ liệu Facebook Ads (từ Facebook Marketing API) và Pancake Chats (gọi trực tiếp Pancake API)
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
import unicodedata
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

# Thêm thư mục 'files' vào sys.path để import pipeline components
workspace_root = Path(__file__).resolve().parent.parent
files_dir = os.path.join(workspace_root, "files")
if files_dir not in sys.path:
    sys.path.append(files_dir)

# 1. Load biến môi trường từ file .env
# Tìm file .env ở thư mục workspace_root, nếu không có thử tìm ở sync-facebook-ad-demographics hoặc path khác
env_file = workspace_root / ".env"
if not env_file.exists():
    # Thử tìm ở thư mục sync-facebook-ad-demographics (nơi ta tìm thấy .env thật)
    env_file = workspace_root.parent / "sync-facebook-ad-demographics" / ".env"
if not env_file.exists():
    env_file = Path("/Users/daudau/VL/.env")

if env_file.exists():
    logger.info(f"[*] Loading environment from: {env_file}")
    with open(env_file, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                os.environ.setdefault(key.strip(), value.strip())

# Sau khi load env, ta set GOOGLE_APPLICATION_CREDENTIALS nếu chưa có
cred_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
if not cred_path or not os.path.exists(cred_path):
    # Thử check file creds tìm thấy
    potential_creds = [
        workspace_root.parent / "refactor-hospital-reconciliation-logic" / "google-credentials.json",
        workspace_root / "google-credentials.json"
    ]
    for p in potential_creds:
        if p.exists():
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(p)
            logger.info(f"[*] Set GOOGLE_APPLICATION_CREDENTIALS to: {p}")
            break

# Import Facebook Ads API helpers từ files
from fb_api import fetch_all_accounts, fetch_ad_details, normalize_ad_id
from transform import transform as transform_fb_ads
from config import AD_ACCOUNTS

def normalize_doctor_name(name):
    if not name:
        return "Unknown"
    
    # Chuẩn hóa chuỗi bằng cách bỏ dấu tiếng Việt và chuyển sang viết thường
    def remove_accents(s):
        s = unicodedata.normalize("NFD", s)
        s = "".join(c for c in s if unicodedata.category(c) != "Mn")
        return s.replace("đ", "d").replace("Đ", "d").lower().strip()
        
    normalized_name = remove_accents(name)
    
    mapping = {
        "dinh": "BS Định",
        "tuyen": "BS Tuyên",
        "duy": "BS Phạm Duy",
        "chung": "BS Kim Chung",
        "hung": "BS Kiều Đình Hùng",
        "vu anh": "BS Vũ Anh",
        "khanh": "BS Khánh"
    }
    
    for key, val in mapping.items():
        if key in normalized_name:
            return val
            
    return name

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
    Trả về: pancake_stats
    """
    pancake_stats = {}
    
    # Chia khoảng thời gian thành các khoảng nhỏ dưới 15 ngày để tránh giới hạn API
    date_ranges = split_date_range(start_date, end_date, max_days=15)
    logger.info(f"[*] Khoảng thời gian {start_date} ➔ {end_date} được chia thành các khoảng nhỏ để gọi Pancake API: {date_ranges}")

    # Chuẩn bị token dùng chung làm fallback
    env_token = os.getenv("PANCAKE_PAGE_ACCESS_TOKEN") or os.getenv("FB_ACCESS_TOKEN")

    for doc_key, cfg in pages_config.items():
        page_id = cfg.get("page_id")
        token = cfg.get("pancake_token")
        doctor_name_raw = cfg.get("doctor_name")
        doctor_name = normalize_doctor_name(doctor_name_raw)
        
        # Đoán chuyên khoa dựa trên tên bác sĩ hoặc gán mặc định
        specialty_name = "Cột Sống" if "Tuyên" in doctor_name or "Định" in doctor_name else "Thần Kinh"
        
        # Nếu token là placeholder hoặc rỗng, dùng token dùng chung
        if not token or "YOUR" in token:
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
            logger.warning(f"[-] Bỏ qua kết quả Pancake của {doctor_name} do API bị lỗi.")
            continue
            
        logger.info(f"   - Lấy thành công {len(all_convs)} cuộc hội thoại cho {doctor_name} từ {start_date} đến {end_date}.")
        
        # Phân tích từng cuộc hội thoại (lấy trực tiếp thông tin từ metadata của cuộc hội thoại, không gọi fetch_messages)
        for conv in all_convs:
            ads_list = conv.get("ads") or []
            
            # Nếu cuộc hội thoại không gắn với Ads, ta xem là "organic" (nhưng Pancake stats vẫn đếm)
            # Tuy nhiên, nếu ads_list rỗng, ta gán ad_id là 'organic'
            if not ads_list:
                ads_list = [{"ad_id": "organic"}]
                
            conv_type = conv.get("type", "inbox")
            
            # Lấy ngày hội thoại (UTC -> convert sang YYYY-MM-DD)
            inserted_at_str = conv.get("inserted_at")
            if not inserted_at_str:
                continue
            
            # Parse UTC sang múi giờ Việt Nam (+7) trước khi lấy ngày để so khớp chính xác với Ads
            try:
                # Pancake timestamp format: "2026-06-22T07:54:35.330000Z" or without Z
                ts_str = inserted_at_str.replace("Z", "")
                dt_utc = datetime.fromisoformat(ts_str)
                # Cộng thêm 7 tiếng cho múi giờ VN
                dt_vn = dt_utc + timedelta(hours=7)
                chat_date = dt_vn.strftime("%Y-%m-%d")
            except Exception as e:
                # Fallback if parse error
                chat_date = inserted_at_str.split("T")[0]
            
            # 1. Đếm số điện thoại
            has_phone = conv.get("has_phone", False)
            if not has_phone and conv.get("recent_phone_numbers"):
                phones = conv.get("recent_phone_numbers")
                if isinstance(phones, list):
                    for p in phones:
                        if p and REGEX_PHONE.match(str(p).strip()):
                            has_phone = True
                            break
                elif isinstance(phones, str):
                    if REGEX_PHONE.match(phones.strip()):
                        has_phone = True
            
            # 2. Kiểm tra phản hồi của page
            last_sent = conv.get("last_sent_by")
            has_reply = False
            if last_sent:
                if last_sent.get("id") == page_id or last_sent.get("admin_name"):
                    has_reply = True
            
            # 3. Kiểm tra khtn (inbox và messages_count >= 3)
            messages_count = conv.get("messages_count", 0)
            has_khtn = (conv_type == "inbox") and (messages_count >= 3)
            
            # 4. Kiểm tra đặt lịch (bookings hoặc tags đặt hẹn)
            has_booking = False
            bookings = conv.get("bookings") or []
            for b in bookings:
                if b and isinstance(b, dict):
                    status = b.get("status", "").lower()
                    if status not in ["cancelled", "cancel", "hủy", "huy"]:
                        has_booking = True
                        break
            
            if not has_booking:
                tags = conv.get("tags") or []
                booking_keywords = ["đặt lịch", "chốt lịch", "booking", "lên lịch", "hen kham", "hẹn khám", "chốt hẹn", "đã hẹn"]
                for tag in tags:
                    tag_name = ""
                    if isinstance(tag, dict):
                        tag_name = tag.get("name", "")
                    elif isinstance(tag, str):
                        tag_name = tag
                    tag_name_lower = tag_name.lower().strip()
                    if any(kw in tag_name_lower for kw in booking_keywords):
                        has_booking = True
                        break

            # Cập nhật thống kê theo từng ad_id và date
            for ad in ads_list:
                ad_id = ad.get("ad_id") or "organic"
                
                key = (chat_date, ad_id, doctor_name)
                if key not in pancake_stats:
                    pancake_stats[key] = {
                        "pancake_chat": 0,
                        "pancake_comment": 0,
                        "pancake_phone": 0,
                        "dat_lich": 0,
                        "reply_count": 0,
                        "khtn": 0,
                        "doctor_name": doctor_name,
                        "specialty_name": specialty_name
                    }
                    
                stats = pancake_stats[key]
                if conv_type != "comment":
                    stats["pancake_chat"] += 1
                else:
                    stats["pancake_comment"] += 1
                    
                if has_phone:
                    stats["pancake_phone"] += 1
                    
                if has_reply:
                    stats["reply_count"] += 1

                if has_khtn:
                    stats["khtn"] += 1
                    
                if has_booking:
                    stats["dat_lich"] += 1

    return pancake_stats

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
    try:
        pancake_stats = analyze_pancake_data(start_date, end_date, pages_config)
    except Exception as e:
        logger.error(f"[Pancake API] Thất bại khi phân tích dữ liệu Pancake: {e}", exc_info=True)

    # 3. Lấy dữ liệu Facebook Ads trực tiếp từ API (Không dùng BQ fb_ad_insights)
    logger.info(f"[*] Đang lấy dữ liệu Facebook Ads trực tiếp từ Facebook API: {start_date} ➔ {end_date}...")
    fb_rows = []
    try:
        account_ids = list(AD_ACCOUNTS.keys())
        raw_insights = fetch_all_accounts(account_ids, start_date, end_date)
        
        unique_ad_ids = list({
            normalize_ad_id(row.get("ad_id"))
            for row in raw_insights
            if normalize_ad_id(row.get("ad_id"))
        })
        ad_details = fetch_ad_details(unique_ad_ids)
        
        run_date = date.today().strftime("%Y-%m-%d")
        transformed_rows = transform_fb_ads(
            insights=raw_insights,
            ad_details=ad_details,
            account_specialty_map=AD_ACCOUNTS,
            start_date=start_date,
            end_date=end_date,
            run_date=run_date
        )
        
        # Nhóm transformed_rows theo (date, ad_id) giống câu query BQ trước đây
        fb_groups = {}
        for r in transformed_rows:
            d_str = r.get("start_date")
            d = datetime.strptime(d_str, "%Y-%m-%d").date()
            ad_id = r.get("ad_id")
            
            # Chuẩn hóa tên bác sĩ từ campaign name
            doc_name_raw = r.get("doctor_name")
            doc_name = normalize_doctor_name(doc_name_raw)
            
            key = (d, ad_id, doc_name)
            if key not in fb_groups:
                fb_groups[key] = {
                    "date": d,
                    "ad_id": ad_id,
                    "ad_name": r.get("ad_name"),
                    "specialty_name": r.get("specialty_name"),
                    "doctor_name": doc_name,
                    "spend": 0.0,
                    "clicks": 0,
                    "impressions": 0,
                    "mes": 0,
                    "cmt": 0,
                    "video_views": 0,
                    "thruplay": 0,
                    "video_100": 0
                }
            g = fb_groups[key]
            g["spend"] += float(r.get("spend") or 0.0)
            g["clicks"] += int(r.get("clicks") or 0)
            g["impressions"] += int(r.get("impressions") or 0)
            g["mes"] += int(r.get("mes") or 0)
            g["cmt"] += int(r.get("cmt") or 0)
            g["video_views"] += int(r.get("video_views") or 0)
            g["thruplay"] += int(r.get("thruplay") or 0)
            g["video_100"] += int(r.get("video_100") or 0)
            
            if r.get("ad_name"):
                g["ad_name"] = r.get("ad_name")
            if r.get("specialty_name"):
                g["specialty_name"] = r.get("specialty_name")
                
        fb_rows = list(fb_groups.values())
        logger.info(f"   - Lấy thành công {len(fb_rows)} dòng quảng cáo từ Facebook Ads API.")
    except Exception as e:
        logger.error(f"[-] Lỗi khi gọi Facebook API: {e}", exc_info=True)

    # 4. Gộp dữ liệu Facebook Ads và Pancake
    combined_data = []
    
    # Gom tất cả các key (date_str, ad_id, doctor_name) duy nhất
    all_keys = set()
    for r in fb_rows:
        date_str = r["date"].strftime("%Y-%m-%d")
        all_keys.add((date_str, r["ad_id"], r["doctor_name"]))
        
    for (chat_date, ad_id, doc_name) in pancake_stats.keys():
        all_keys.add((chat_date, ad_id, doc_name))
        
    # Map để tra cứu fb_rows nhanh
    fb_map = {(r["date"].strftime("%Y-%m-%d"), r["ad_id"], r["doctor_name"]): r for r in fb_rows}
    
    now_iso = datetime.utcnow().isoformat() + "Z"

    for chat_date, ad_id, doc_name in all_keys:
        fb_info = fb_map.get((chat_date, ad_id, doc_name)) or {}
        p_info = pancake_stats.get((chat_date, ad_id, doc_name))
        
        # Xác định các thuộc tính văn bản
        # Ưu tiên lấy specialty từ Pancake (nếu có p_info) hoặc Facebook Ads
        spec_name = fb_info.get("specialty_name")
        if not spec_name and p_info:
            spec_name = p_info["specialty_name"]
        if not spec_name:
            spec_name = "Cột Sống" if "Tuyên" in doc_name or "Định" in doc_name else "Thần Kinh"
            
        ad_name = fb_info.get("ad_name")
        if not ad_name:
            ad_name = "Organic" if ad_id == "organic" else f"Unknown_Ad_{ad_id}"
            
        # Parsing angles, format theo cú pháp mới: Angle_tên bài_id post fb
        parts = ad_name.split("_")
        
        if ad_name == "Organic":
            angle = "Organic"
            ad_post_name = "Organic"
        elif len(parts) >= 2:
            angle = parts[0].strip()
            ad_post_name = parts[1].strip()
        else:
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
                
        ad_format = "Video" if "video" in ad_name.lower() else "Image"
        
        # Các chỉ số Ads
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

        # Chỉ số hội thoại & chuyển đổi từ Pancake API
        if p_info:
            pancake_chat = p_info["pancake_chat"]
            pancake_comment = p_info["pancake_comment"]
            pancake_lead = pancake_chat + pancake_comment
            pancake_phone = p_info["pancake_phone"]
            dat_lich = p_info["dat_lich"]
            khtn = p_info["khtn"]
        else:
            # Fallback nếu không có dữ liệu Pancake (ví dụ Ads chạy nhưng không kéo được Pancake)
            # Theo yêu cầu, không dùng botcake_leads nữa. Ta chỉ dùng dữ liệu fb_mess/fb_comment làm chỉ số chat cơ bản, phone và dat_lich gán = 0
            pancake_chat = fb_mess
            pancake_comment = fb_comment
            pancake_lead = pancake_chat + pancake_comment
            pancake_phone = 0
            dat_lich = 0
            khtn = 0
            
        pancake_phone_rate = pancake_phone / pancake_lead if pancake_lead > 0 else 0.0
        dat_lich_rate = dat_lich / pancake_lead if pancake_lead > 0 else 0.0
        
        cost_per_lead = spend / pancake_lead if pancake_lead > 0 else 0.0
        cost_per_phone = spend / dat_lich if dat_lich > 0 else 0.0

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
            "retention_rate": 0.0, # Sẽ được cập nhật sau bằng script update_retention_rate
            "spend": spend,
            "pancake_chat": pancake_chat,
            "pancake_comment": pancake_comment,
            "pancake_lead": pancake_lead,
            "pancake_phone": pancake_phone,
            "pancake_phone_rate": pancake_phone_rate,
            "dat_lich": dat_lich,
            "dat_lich_rate": dat_lich_rate,
            "khtn": khtn,
            "inserted_at": now_iso,
            "fb_comment": fb_comment,
            "fb_lead": fb_lead,
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
