"""
pipeline.py — Điều phối toàn bộ luồng:
  1. Lấy insights từ tất cả Facebook Accounts
  2. Lấy chi tiết creative/status (song song)
  3. Transform → rows BigQuery
  4. Upsert vào bảng fb_ad_insights
"""

import logging
from datetime import date, timedelta

from config import AD_ACCOUNTS, DEFAULT_LOOKBACK_DAYS
from fb_api import fetch_all_accounts, fetch_ad_details, normalize_ad_id
from transform import transform
from bq_loader import upsert_rows

logger = logging.getLogger(__name__)


def run(
    start_date: str = None,
    end_date: str   = None,
    account_ids: list[str] = None,
) -> dict:
    """
    Chạy toàn bộ pipeline.
    - Nếu không truyền start/end_date: lấy DEFAULT_LOOKBACK_DAYS ngày gần nhất.
    - Nếu không truyền account_ids: chạy tất cả account trong config.
    Trả về dict tổng kết kết quả.
    """

    # --- Ngày mặc định ---
    today    = date.today()
    end_str  = end_date   or today.strftime("%Y-%m-%d")
    start_str = start_date or (today - timedelta(days=DEFAULT_LOOKBACK_DAYS)).strftime("%Y-%m-%d")
    run_str  = today.strftime("%Y-%m-%d")

    # --- Account mặc định ---
    if account_ids:
        active_accounts = {a: AD_ACCOUNTS.get(a, "") for a in account_ids if a in AD_ACCOUNTS}
    else:
        active_accounts = dict(AD_ACCOUNTS)

    logger.info("=" * 60)
    logger.info(f"[Pipeline] BẮT ĐẦU: {start_str} → {end_str}")
    logger.info(f"[Pipeline] Accounts: {list(active_accounts.keys())}")
    logger.info("=" * 60)

    # --- B1: Lấy insights từ Facebook ---
    logger.info("[B1] Lấy Facebook Insights...")
    all_insights = fetch_all_accounts(
        list(active_accounts.keys()), start_str, end_str
    )
    logger.info(f"[B1] Tổng insights có spend > 0: {len(all_insights)}")

    if not all_insights:
        logger.warning("[Pipeline] Không có dữ liệu. Kết thúc sớm.")
        return {
            "status":        "ok",
            "start_date":    start_str,
            "end_date":      end_str,
            "insights_count": 0,
            "inserted_rows":  0,
        }

    # --- B2: Lấy chi tiết creative/status (song song) ---
    logger.info("[B2] Lấy chi tiết Ad (creative, status)...")
    unique_ad_ids = list({
        normalize_ad_id(row.get("ad_id"))
        for row in all_insights
        if normalize_ad_id(row.get("ad_id"))
    })
    ad_details = fetch_ad_details(unique_ad_ids)
    logger.info(f"[B2] Lấy được chi tiết {len(ad_details)} ad")

    # --- B3: Transform ---
    logger.info("[B3] Transform dữ liệu...")
    rows = transform(
        insights           = all_insights,
        ad_details         = ad_details,
        account_specialty_map = active_accounts,
        start_date         = start_str,
        end_date           = end_str,
        run_date           = run_str,
    )
    logger.info(f"[B3] {len(rows)} dòng sẵn sàng insert")

    # --- B4: Upsert vào BigQuery ---
    logger.info("[B4] Upsert vào BigQuery...")
    inserted = upsert_rows(
        rows        = rows,
        start_date  = start_str,
        end_date    = end_str,
        account_ids = list(active_accounts.keys()),
    )

    logger.info(f"[Pipeline] HOÀN TẤT — đã insert {inserted} dòng.")
    logger.info("=" * 60)

    return {
        "status":         "ok",
        "start_date":     start_str,
        "end_date":       end_str,
        "accounts":       list(active_accounts.keys()),
        "insights_count": len(all_insights),
        "ads_fetched":    len(ad_details),
        "inserted_rows":  inserted,
    }
