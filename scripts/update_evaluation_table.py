#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script tổng hợp dữ liệu - Đã được chuyển hướng sang gọi trực tiếp sync_evaluation_pancake.py
để tuân thủ quy tắc lấy dữ liệu trực tiếp từ Facebook API và Pancake API.
"""

import sys
import argparse
from pathlib import Path

# Thêm thư mục scripts vào path để import
script_dir = Path(__file__).resolve().parent
if str(script_dir) not in sys.path:
    sys.path.append(str(script_dir))

from sync_evaluation_pancake import run_sync

def main():
    parser = argparse.ArgumentParser(description="Chuyển hướng đồng bộ qua API.")
    parser.add_argument("--start-date", help="Ngày bắt đầu (YYYY-MM-DD)")
    parser.add_argument("--end-date", help="Ngày kết thúc (YYYY-MM-DD)")
    args = parser.parse_args()
    
    from datetime import date, timedelta
    today = date.today()
    start_date = args.start_date or (today - timedelta(days=7)).strftime("%Y-%m-%d")
    end_date = args.end_date or today.strftime("%Y-%m-%d")
    
    print(f"[Redirect] Đang chuyển hướng đồng bộ dữ liệu sang API trực tiếp từ {start_date} đến {end_date}...")
    run_sync(start_date, end_date)

if __name__ == "__main__":
    main()
