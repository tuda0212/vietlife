#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script chạy đồng bộ dữ liệu lịch sử (backfill) năm 2026.
Đồng bộ Facebook Ads (6 tài khoản) và CRM Leads (tất cả bác sĩ) theo từng tháng.
"""

import sys
import os
import logging
from pathlib import Path
from datetime import date

# 1. Load biến môi trường từ file .env thật
workspace_root = Path(__file__).resolve().parent.parent
env_file = workspace_root / ".env"
# Nếu không thấy .env ở worktree, thử lấy ở master workspace
if not env_file.exists():
    env_file = Path("/Users/daudau/VL/.env")

if env_file.exists():
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                os.environ.setdefault(key.strip(), value.strip())

# Thêm thư mục 'files' vào sys.path để import các pipeline
files_dir = workspace_root / "files"
sys.path.append(str(files_dir))

import pipeline
import crm_pipeline
from config_crm import DOCTOR_SHEETS

# Cấu hình logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s"
)
logger = logging.getLogger("backfill_2026")

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Chạy backfill dữ liệu năm 2026 theo từng tháng.")
    parser.add_argument("--test", action="store_true", help="Chạy chế độ kiểm thử 1 tuần đầu năm 2026")
    args = parser.parse_args()

    # Định nghĩa các khoảng thời gian theo từng tháng trong năm 2026
    if args.test:
        months = [
            ("2026-01-01", "2026-01-07")
        ]
        logger.info("[*] Chạy chế độ kiểm thử (1 tuần đầu năm 2026)...")
    else:
        # Ngày hiện tại của hệ thống là 2026-06-26
        today_str = date.today().strftime("%Y-%m-%d")
        months = [
            ("2026-01-01", "2026-01-31"),
            ("2026-02-01", "2026-02-28"),
            ("2026-03-01", "2026-03-31"),
            ("2026-04-01", "2026-04-30"),
            ("2026-05-01", "2026-05-31"),
            ("2026-06-01", today_str)
        ]
        logger.info(f"[*] Bắt đầu chạy backfill toàn bộ năm 2026 đến ngày {today_str}...")

    # Lấy toàn bộ danh sách bác sĩ từ cấu hình CRM
    all_doctors = list(DOCTOR_SHEETS.keys())
    logger.info(f"[*] Số lượng bác sĩ CRM cần đồng bộ: {len(all_doctors)} ({', '.join(all_doctors)})")
    logger.info(f"[*] Sẽ đồng bộ cả 6 tài khoản Facebook Ads trong cấu hình.")

    total_fb_inserted = 0
    total_crm_inserted = 0

    for start_date, end_date in months:
        logger.info("\n" + "="*80)
        logger.info(f"⏳ ĐANG ĐỒNG BỘ KHOẢNG THỜI GIAN: {start_date} ➔ {end_date}")
        logger.info("="*80)

        # 1. Chạy Facebook Ads pipeline (tự động lấy cả 6 tài khoản Ads trong config)
        try:
            logger.info(f"[FB Ads] Bắt đầu đồng bộ chi tiêu và insights...")
            fb_res = pipeline.run(
                start_date=start_date,
                end_date=end_date,
                account_ids=None # Lấy tất cả tài khoản trong config
            )
            inserted_fb = fb_res.get("inserted_rows", 0)
            total_fb_inserted += inserted_fb
            logger.info(f"[FB Ads] Hoàn thành. Số dòng đã nạp: {inserted_fb}")
        except Exception as fb_err:
            logger.error(f"[FB Ads] Lỗi đồng bộ khoảng {start_date} -> {end_date}: {fb_err}", exc_info=True)

        # 2. Chạy CRM pipeline (đồng bộ tất cả các bác sĩ)
        try:
            logger.info(f"[CRM] Bắt đầu đồng bộ leads từ Google Sheets...")
            crm_res = crm_pipeline.run(
                start_date=start_date,
                end_date=end_date,
                doctors=all_doctors,
                versions=[2026] # Giới hạn phiên bản năm 2026
            )
            inserted_crm = crm_res.get("total_inserted", 0)
            total_crm_inserted += inserted_crm
            logger.info(f"[CRM] Hoàn thành. Tổng số dòng đã nạp: {inserted_crm}")
            for detail in crm_res.get("details", []):
                logger.info(f"   - {detail.get('doctor')}: đã nạp {detail.get('inserted')} dòng (trạng thái: {detail.get('status')})")
        except Exception as crm_err:
            logger.error(f"[CRM] Lỗi đồng bộ khoảng {start_date} -> {end_date}: {crm_err}", exc_info=True)

        # 3. Cập nhật bảng ad_content_evaluation
        try:
            logger.info(f"[Evaluation] Bắt đầu tổng hợp và cập nhật bảng ad_content_evaluation kết hợp Pancake Chats cho khoảng {start_date} ➔ {end_date}...")
            import sync_evaluation_pancake
            sync_evaluation_pancake.run_sync(start_date, end_date)
            logger.info(f"[Evaluation] Hoàn thành cập nhật bảng ad_content_evaluation.")
        except Exception as eval_err:
            logger.error(f"[Evaluation] Lỗi cập nhật bảng ad_content_evaluation cho khoảng {start_date} ➔ {end_date}: {eval_err}", exc_info=True)

    logger.info("\n" + "="*80)
    logger.info("🎉 HOÀN THÀNH TOÀN BỘ QUÁ TRÌNH DỒNG BỘ BACKFILL!")
    logger.info(f"➔ Tổng số dòng Ads đã nạp: {total_fb_inserted}")
    logger.info(f"➔ Tổng số dòng CRM đã nạp: {total_crm_inserted}")
    logger.info("="*80)

if __name__ == "__main__":
    main()
