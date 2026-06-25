"""
fb_api.py — Gọi Facebook Marketing API
Port trực tiếp từ Apps Script: fetchAdInsights_, fetchAdDetailsMap_,
parseCampaignName_, getPostIdFromCreative_, v.v.
"""

import logging
import re
import unicodedata
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta

import requests

from config import (
    FB_ACCESS_TOKEN,
    FB_API_BASE,
    FB_BATCH_SIZE,
    INSIGHTS_FIELDS,
    CREATIVE_FIELDS,
)

logger = logging.getLogger(__name__)


def _split_date_range(start_str: str, end_str: str, chunk_days: int = 30) -> list[tuple[str, str]]:
    try:
        start = datetime.strptime(start_str, "%Y-%m-%d")
        end   = datetime.strptime(end_str, "%Y-%m-%d")
    except Exception:
        return [(start_str, end_str)]
    
    chunks = []
    curr = start
    while curr <= end:
        chunk_end = min(curr + timedelta(days=chunk_days - 1), end)
        chunks.append((curr.strftime("%Y-%m-%d"), chunk_end.strftime("%Y-%m-%d")))
        curr += timedelta(days=chunk_days)
    return chunks


# =================================================================
# INSIGHTS API
# =================================================================

def fetch_insights(account_id: str, start_date: str, end_date: str) -> list[dict]:
    """
    Lấy toàn bộ insights theo account + khoảng ngày (chia nhỏ 30 ngày/chunk).
    Tự phân trang. Chỉ trả về dòng có spend > 0.
    Tương đương fetchAdInsights_() trong Apps Script.
    """
    fields = ",".join(INSIGHTS_FIELDS)
    all_rows = []
    
    # Chia khoảng ngày lớn thành các chunk 30 ngày để tránh lỗi Facebook API Code 1 Subcode 99
    chunks = _split_date_range(start_date, end_date, chunk_days=30)
    logger.info(f"[FB Insights] {account_id}: Chia {start_date} -> {end_date} thành {len(chunks)} chunks để query.")

    for sub_start, sub_end in chunks:
        time_range = f'{{"since":"{sub_start}","until":"{sub_end}"}}'
        url = (
            f"{FB_API_BASE}/{account_id}/insights"
            f"?level=ad"
            f"&time_range={requests.utils.quote(time_range)}"
            f"&time_increment=1"
            f"&fields={fields}"
            f"&limit=500"
            f"&access_token={FB_ACCESS_TOKEN}"
        )

        chunk_rows_count = 0
        while url:
            resp = requests.get(url, timeout=60)
            resp.raise_for_status()
            data = resp.json()

            if "error" in data:
                raise RuntimeError(f"[FB Insights] {account_id} ({sub_start}->{sub_end}): {data['error']['message']}")

            for row in data.get("data", []):
                row["_account_id"] = account_id
                if float(row.get("spend") or 0) > 0:
                    all_rows.append(row)
                    chunk_rows_count += 1

            url = data.get("paging", {}).get("next")
            
        logger.info(f"[FB Insights] {account_id} ({sub_start} -> {sub_end}): Lấy được {chunk_rows_count} dòng (spend > 0)")

    logger.info(f"[FB Insights] {account_id} TỔNG CỘNG: {len(all_rows)} dòng (spend > 0)")
    return all_rows



def fetch_all_accounts(
    account_ids: list[str], start_date: str, end_date: str
) -> list[dict]:
    """Lấy insights từ nhiều account, gộp lại."""
    all_insights = []
    for account_id in account_ids:
        try:
            rows = fetch_insights(account_id, start_date, end_date)
            all_insights.extend(rows)
        except Exception as exc:
            logger.error(f"[FB Insights] Lỗi account {account_id}: {exc}")
    logger.info(f"[FB Insights] Tổng: {len(all_insights)} dòng từ {len(account_ids)} account")
    return all_insights


# =================================================================
# AD DETAILS (CREATIVE + STATUS) — SONG SONG
# Tương đương fetchAdDetailsMap_() trong Apps Script
# =================================================================

def _fetch_batch(ad_ids_batch: list[str]) -> dict:
    """Gọi 1 batch tối đa FB_BATCH_SIZE ad."""
    ids_str = ",".join(ad_ids_batch)
    url = (
        f"{FB_API_BASE}/"
        f"?ids={ids_str}"
        f"&fields={requests.utils.quote(CREATIVE_FIELDS)}"
        f"&access_token={FB_ACCESS_TOKEN}"
    )
    resp = requests.get(url, timeout=60)
    resp.raise_for_status()
    data = resp.json()

    if "error" in data:
        logger.error(f"[FB Details] Lỗi batch: {data['error']['message']}")
        return {}

    return {ad_id: info for ad_id, info in data.items()}


def fetch_ad_details(ad_ids: list[str], max_workers: int = 10) -> dict:
    """
    Lấy creative + status theo lô, gọi SONG SONG.
    Tương đương fetchAdDetailsMap_() trong Apps Script.
    """
    if not ad_ids:
        return {}

    batches = [ad_ids[i:i + FB_BATCH_SIZE] for i in range(0, len(ad_ids), FB_BATCH_SIZE)]
    logger.info(f"[FB Details] {len(ad_ids)} ad → {len(batches)} batch (song song {max_workers} luồng)")

    result = {}
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(_fetch_batch, batch): batch for batch in batches}
        for future in as_completed(futures):
            try:
                result.update(future.result())
            except Exception as exc:
                logger.error(f"[FB Details] Lỗi batch: {exc}")

    logger.info(f"[FB Details] Lấy được chi tiết {len(result)} ad")
    return result


# =================================================================
# CAMPAIGN NAME PARSING
# Tương đương parseCampaignName_(), filterInsightsBySpecialty_()
# =================================================================

def parse_campaign_name(campaign_name: str) -> dict:
    """
    Tách campaign name theo format: MÃ_CK_TÊN BS_NGÀY
    Ví dụ: CXK_BS Định_2026-06-06
    Trả về: { specialty_code, doctor_name, campaign_date }
    """
    if not campaign_name:
        return {"specialty_code": "", "doctor_name": "", "campaign_date": ""}

    parts = [p.strip() for p in str(campaign_name).split("_") if p.strip()]

    return {
        "specialty_code": parts[0] if len(parts) > 0 else "",
        "doctor_name":    parts[1] if len(parts) > 1 else "",
        "campaign_date":  parts[2] if len(parts) > 2 else "",
    }


def filter_by_specialty(insights: list[dict], specialty_code: str) -> list[dict]:
    """Lọc insights theo mã chuyên khoa ở đầu campaign name."""
    code = specialty_code.strip().lower()
    return [
        row for row in insights
        if parse_campaign_name(row.get("campaign_name", ""))["specialty_code"].lower() == code
    ]


# =================================================================
# CREATIVE HELPERS
# Tương đương getPostIdFromCreative_, getCreativeText_, getCreativeThumbnailUrl_()
# =================================================================

def get_post_id(creative: dict, ad_name: str = "") -> str:
    """Lấy post_id từ effective_object_story_id hoặc parse từ ad_name."""
    story_id = creative.get("effective_object_story_id", "")
    if story_id:
        if "_" in story_id:
            return story_id.split("_")[1]
        return story_id
    return _extract_core_id(ad_name)


def _extract_core_id(text: str) -> str:
    if not text:
        return ""
    clean = str(text).strip()
    if re.match(r"^\d+$", clean):
        return clean
    nums = re.findall(r"\d{6,}", clean)
    if nums:
        return max(nums, key=len)
    return clean


def get_creative_text(creative: dict) -> str:
    """Lấy body hoặc title, cắt tối đa 100 ký tự."""
    text = creative.get("body") or creative.get("title") or ""
    text = str(text).strip()
    return text[:100] + "..." if len(text) > 100 else text


def get_thumbnail_url(creative: dict) -> str:
    """Ưu tiên thumbnail_url → image_url → object_story_spec."""
    if creative.get("thumbnail_url"):
        return creative["thumbnail_url"]
    if creative.get("image_url"):
        return creative["image_url"]
    spec = creative.get("object_story_spec") or {}
    for path in [
        ("link_data",     "picture"),
        ("photo_data",    "url"),
        ("video_data",    "image_url"),
        ("template_data", "picture"),
    ]:
        val = spec.get(path[0], {}).get(path[1])
        if val:
            return val
    return ""


# =================================================================
# ACTION / VIDEO HELPERS
# Tương đương getActionValue_(), getVideoMetricValue_()
# =================================================================

def get_action_value(actions: list, action_types: list[str]) -> int:
    """Tổng value của các action_type cần lấy."""
    if not actions:
        return 0
    return sum(
        int(float(a.get("value") or 0))
        for a in actions
        if a.get("action_type") in action_types
    )


def get_video_metric(metric_actions) -> int:
    """Tổng value của video metric (list or None)."""
    if not metric_actions:
        return 0
    return sum(int(float(a.get("value") or 0)) for a in metric_actions)


# =================================================================
# NORMALIZE
# =================================================================

def normalize_ad_id(value) -> str:
    """Trích số dài nhất từ ad_id string."""
    if not value:
        return ""
    text = str(value).strip().lstrip("'")
    nums = re.findall(r"\d{6,}", text)
    return nums[0] if nums else text


def remove_vietnamese_tone(text: str) -> str:
    """Bỏ dấu tiếng Việt, lowercase."""
    text = unicodedata.normalize("NFD", str(text or ""))
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    return text.replace("đ", "d").replace("Đ", "D").lower()


def fetch_demographics_insights(account_id: str, start_date: str, end_date: str, breakdowns: str) -> list[dict]:
    """
    Lấy insights theo breakdowns (vd: 'age,gender' hoặc 'region').
    Chỉ lấy các trường cơ bản liên quan nhân khẩu học để tối ưu tải và tránh timeout.
    """
    fields = "ad_id,ad_name,campaign_name,date_start,date_stop,spend,impressions,clicks,reach,actions"
    all_rows = []
    
    chunks = _split_date_range(start_date, end_date, chunk_days=30)
    logger.info(f"[FB Demographics] {account_id} ({breakdowns}): Chia {start_date} -> {end_date} thành {len(chunks)} chunks.")

    for sub_start, sub_end in chunks:
        time_range = f'{{"since":"{sub_start}","until":"{sub_end}"}}'
        url = (
            f"{FB_API_BASE}/{account_id}/insights"
            f"?level=ad"
            f"&time_range={requests.utils.quote(time_range)}"
            f"&time_increment=1"
            f"&fields={fields}"
            f"&breakdowns={breakdowns}"
            f"&limit=500"
            f"&access_token={FB_ACCESS_TOKEN}"
        )

        chunk_rows_count = 0
        while url:
            resp = requests.get(url, timeout=60)
            resp.raise_for_status()
            data = resp.json()

            if "error" in data:
                raise RuntimeError(f"[FB Demographics] {account_id} ({breakdowns}) ({sub_start}->{sub_end}): {data['error']['message']}")

            for row in data.get("data", []):
                row["_account_id"] = account_id
                if float(row.get("spend") or 0) > 0:
                    all_rows.append(row)
                    chunk_rows_count += 1

            url = data.get("paging", {}).get("next")
            
    logger.info(f"[FB Demographics] {account_id} ({breakdowns}) TỔNG CỘNG: {len(all_rows)} dòng (spend > 0)")
    return all_rows
