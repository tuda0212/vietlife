"""
crm_pipeline.py — Pipeline 2: Google Sheets CRM → BigQuery botcake_leads.
Đọc từng sheet bác sĩ → transform → upsert vào BigQuery.
"""

import io
import json
import logging
from datetime import date, timedelta, timezone, datetime

from google.cloud import bigquery

from config_crm import (
    GCP_PROJECT_ID,
    BQ_DATASET,
    BQ_TABLE_LEADS,
    DOCTOR_SHEETS,
    UPSERT_DELETE_BEFORE_INSERT,
)
from sheets_reader import read_crm_sheet

logger = logging.getLogger(__name__)

_bq_client = None


def _get_bq_client():
    global _bq_client
    if _bq_client is None:
        _bq_client = bigquery.Client(project=GCP_PROJECT_ID)
    return _bq_client


def run(
    start_date: str = None,
    end_date: str   = None,
    doctors: list[str] = None,
) -> dict:
    """
    Chạy pipeline CRM.
    - start_date / end_date: khoảng ngày cần đồng bộ (mặc định 7 ngày gần nhất)
    - doctors: danh sách tên bác sĩ cần chạy (mặc định tất cả)
    """
    today     = date.today()
    end_str   = end_date   or today.strftime("%Y-%m-%d")
    start_str = start_date or (today - timedelta(days=7)).strftime("%Y-%m-%d")

    active_doctors = {
        k: v for k, v in DOCTOR_SHEETS.items()
        if not doctors or k in doctors
    }

    logger.info("=" * 60)
    logger.info(f"[CRM Pipeline] BẮT ĐẦU: {start_str} → {end_str}")
    logger.info(f"[CRM Pipeline] Bác sĩ: {list(active_doctors.keys())}")
    logger.info("=" * 60)

    total_inserted = 0
    results = []

    for doctor_key, cfg in active_doctors.items():
        spreadsheet_id = cfg["spreadsheet_id"]
        doctor_name    = cfg["doctor_name"]
        specialty_code = cfg["specialty_code"]
        specialty_name = cfg["specialty_name"]
        report_group   = cfg["report_group"]

        logger.info(f"[CRM] Đang đọc: {doctor_name} ({spreadsheet_id})")

        try:
            # B1: Đọc Sheet
            sheet_type = cfg.get("sheet_type", "doctor")
            sheet_title = cfg.get("sheet_title")
            raw_rows = read_crm_sheet(
                spreadsheet_id,
                start_str,
                end_str,
                sheet_type=sheet_type,
                sheet_title=sheet_title,
            )
            logger.info(f"[CRM] {doctor_name}: {len(raw_rows)} dòng hợp lệ")

            # B2: Transform → BQ rows
            now_utc = datetime.now(timezone.utc).isoformat()
            bq_rows = []
            for r in raw_rows:
                bq_rows.append({
                    "inserted_at":      now_utc,
                    "lead_date":        r["lead_date"],
                    "page_id":          spreadsheet_id,   # dùng spreadsheet_id làm page_id tạm
                    "doctor_name":      doctor_name,
                    "specialty_code":   r.get("specialty_code", specialty_code),
                    "specialty_name":   r.get("specialty_name", specialty_name),
                    "report_group":     report_group,
                    "subscriber_id":    r.get("subscriber_id", ""),
                    "phone":            r["phone"],
                    "ad_id":            r["ad_id"],
                    "ad_name":          "",
                    "conversation_id":  "",
                    "booking_status":   r["booking_status"],
                    "arrival_status":   r["arrival_status"],
                    "is_booking":       r["is_booking"],
                    "is_arrival":       r["is_arrival"],
                    "note":             "",
                    "revenue":          r.get("revenue", 0.0),
                })

            # B3: Upsert vào BigQuery
            inserted = _upsert_to_bq(bq_rows, start_str, end_str, spreadsheet_id)
            total_inserted += inserted

            results.append({
                "doctor":    doctor_name,
                "rows_read": len(raw_rows),
                "inserted":  inserted,
                "status":    "ok",
            })

        except Exception as exc:
            logger.error(f"[CRM] Lỗi {doctor_name}: {exc}", exc_info=True)
            results.append({
                "doctor":  doctor_name,
                "status":  "error",
                "message": str(exc),
            })

    logger.info(f"[CRM Pipeline] HOÀN TẤT — tổng {total_inserted} dòng.")
    logger.info("=" * 60)

    return {
        "status":         "ok",
        "start_date":     start_str,
        "end_date":       end_str,
        "total_inserted": total_inserted,
        "details":        results,
    }


def _upsert_to_bq(rows: list[dict], start_date: str, end_date: str, page_id: str) -> int:
    if not rows:
        return 0

    client    = _get_bq_client()
    table_ref = f"{GCP_PROJECT_ID}.{BQ_DATASET}.{BQ_TABLE_LEADS}"

    # Xóa data cũ cùng khoảng ngày + page_id
    if UPSERT_DELETE_BEFORE_INSERT:
        delete_sql = f"""
            DELETE FROM `{table_ref}`
            WHERE lead_date BETWEEN '{start_date}' AND '{end_date}'
              AND page_id = '{page_id}'
        """
        try:
            client.query(delete_sql).result()
            logger.info(f"[BQ] Đã xóa data cũ: {page_id} / {start_date}→{end_date}")
        except Exception as e:
            logger.warning(f"[BQ] Bỏ qua xóa (streaming buffer?): {e}")

    # Load batch job
    table      = client.get_table(table_ref)
    job_config = bigquery.LoadJobConfig(
        write_disposition=bigquery.WriteDisposition.WRITE_APPEND,
        source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
        autodetect=False,
    )
    ndjson  = "\n".join(json.dumps(row, default=str) for row in rows)
    buffer  = io.BytesIO(ndjson.encode("utf-8"))

    load_job = client.load_table_from_file(buffer, table, job_config=job_config)
    load_job.result()

    if load_job.errors:
        raise RuntimeError(f"BQ load errors: {load_job.errors}")

    logger.info(f"[BQ] Insert {load_job.output_rows} dòng cho {page_id}")
    return load_job.output_rows
