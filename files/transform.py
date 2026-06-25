"""
transform.py — Biến đổi raw Facebook insights → rows sạch cho BigQuery.
Port logic từ groupInsightsByPost_() và buildDetailRow_() trong Apps Script.
"""

import logging
from datetime import datetime, timezone

from config import SPECIALTY_NAMES
from fb_api import (
    get_action_value,
    get_creative_text,
    get_post_id,
    get_thumbnail_url,
    get_video_metric,
    normalize_ad_id,
    parse_campaign_name,
)

logger = logging.getLogger(__name__)


def transform(
    insights: list[dict],
    ad_details: dict,
    account_specialty_map: dict,  # { "act_xxx": "CXK" }
    start_date: str,
    end_date: str,
    run_date: str,
    gcs_thumbnail_map: dict = None,
) -> list[dict]:
    """
    Biến đổi raw insights + ad_details → list[dict] sẵn sàng insert BigQuery.
    Mỗi dict = 1 dòng trong bảng fb_ad_insights (1 ad, không gom theo post —
    việc gom để view v_report xử lý bằng SQL).
    """
    now_utc = datetime.now(timezone.utc).isoformat()
    rows = []

    for item in insights:
        ad_id = normalize_ad_id(item.get("ad_id"))
        if not ad_id:
            continue

        spend = float(item.get("spend") or 0)
        if spend <= 0:
            continue

        campaign_name = item.get("campaign_name") or ""
        parsed        = parse_campaign_name(campaign_name)

        # Ưu tiên mã CK từ campaign name, fallback sang account map
        account_id     = item.get("_account_id", "")
        specialty_code = parsed["specialty_code"] or account_specialty_map.get(account_id, "")
        specialty_name = SPECIALTY_NAMES.get(specialty_code, specialty_code)
        doctor_name    = parsed["doctor_name"]

        # Creative / Status
        details        = ad_details.get(ad_id) or {}
        creative       = details.get("creative") or {}
        status         = details.get("status") or ""
        eff_status     = details.get("effective_status") or ""
        is_active      = (status == "ACTIVE" and eff_status == "ACTIVE")

        post_id        = get_post_id(creative, item.get("ad_name") or "")
        post_link      = f"https://facebook.com/{post_id}" if post_id else ""
        
        # Ưu tiên lấy URL đã được lưu trên GCS, fallback về get_thumbnail_url gốc
        if gcs_thumbnail_map and ad_id in gcs_thumbnail_map:
            thumbnail_url = gcs_thumbnail_map[ad_id]
        else:
            thumbnail_url = get_thumbnail_url(creative)
            
        content        = get_creative_text(creative)

        # Actions
        actions = item.get("actions") or []
        mes = get_action_value(actions, [
            "messaging_first_reply",
            "onsite_conversion.messaging_first_reply",
        ])
        cmt = get_action_value(actions, ["comment"])

        rows.append({
            "inserted_at":      now_utc,
            "run_date":         run_date,
            "start_date":       item.get("date_start") or start_date,
            "end_date":         item.get("date_stop") or end_date,
            "account_id":       account_id,
            "ad_id":            ad_id,
            "ad_name":          item.get("ad_name") or "",
            "campaign_name":    campaign_name,
            "specialty_code":   specialty_code,
            "specialty_name":   specialty_name,
            "doctor_name":      doctor_name,
            "post_id":          post_id,
            "post_link":        post_link,
            "thumbnail_url":    thumbnail_url,
            "content":          content,
            "status":           status,
            "effective_status": eff_status,
            "is_active":        is_active,
            "spend":            spend,
            "mes":              mes,
            "cmt":              cmt,
            "clicks":           int(item.get("clicks") or 0),
            "impressions":      int(item.get("impressions") or 0),
            "reach":            int(item.get("reach") or 0),
            "video_views":      get_action_value(actions, ["video_view"]),
            "video_25":         get_video_metric(item.get("video_p25_watched_actions")),
            "video_50":         get_video_metric(item.get("video_p50_watched_actions")),
            "video_75":         get_video_metric(item.get("video_p75_watched_actions")),
            "video_95":         get_video_metric(item.get("video_p95_watched_actions")),
            "video_100":        get_video_metric(item.get("video_p100_watched_actions")),
            "thruplay":         get_video_metric(item.get("video_thruplay_watched_actions")),
        })

    logger.info(f"[Transform] {len(insights)} insights → {len(rows)} dòng hợp lệ")
    return rows


def transform_demographics(
    insights: list[dict],
    account_specialty_map: dict,  # { "act_xxx": "CXK" }
    breakdown_type: str,          # "age_gender" hoặc "region"
    run_date: str,
) -> list[dict]:
    """
    Biến đổi raw insights có breakdowns -> rows sạch cho bảng demographics.
    """
    now_utc = datetime.now(timezone.utc).isoformat()
    rows = []

    for item in insights:
        ad_id = normalize_ad_id(item.get("ad_id"))
        if not ad_id:
            continue

        spend = float(item.get("spend") or 0)
        if spend <= 0:
            continue

        campaign_name = item.get("campaign_name") or ""
        parsed        = parse_campaign_name(campaign_name)

        account_id     = item.get("_account_id", "")
        specialty_code = parsed["specialty_code"] or account_specialty_map.get(account_id, "")
        specialty_name = SPECIALTY_NAMES.get(specialty_code, specialty_code)
        doctor_name    = parsed["doctor_name"]

        # Actions (Tin nhắn)
        actions = item.get("actions") or []
        mes = get_action_value(actions, [
            "messaging_first_reply",
            "onsite_conversion.messaging_first_reply",
        ])

        # Đọc thông tin phân rã nhân khẩu
        age = item.get("age") if breakdown_type == "age_gender" else None
        gender = item.get("gender") if breakdown_type == "age_gender" else None
        region = item.get("region") if breakdown_type == "region" else None

        rows.append({
            "inserted_at":      now_utc,
            "run_date":         run_date,
            "start_date":       item.get("date_start"),
            "end_date":         item.get("date_stop"),
            "account_id":       account_id,
            "ad_id":            ad_id,
            "ad_name":          item.get("ad_name") or "",
            "campaign_name":    campaign_name,
            "specialty_code":   specialty_code,
            "specialty_name":   specialty_name,
            "doctor_name":      doctor_name,
            "spend":            spend,
            "clicks":           int(item.get("clicks") or 0),
            "impressions":      int(item.get("impressions") or 0),
            "reach":            int(item.get("reach") or 0),
            "mes":              mes,
            "breakdown_type":   breakdown_type,
            "age":              age,
            "gender":           gender,
            "region":           region,
        })

    return rows
