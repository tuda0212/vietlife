"""
crm_pipeline.py — Pipeline 2: Google Sheets CRM → BigQuery botcake_leads.
Đọc từng sheet bác sĩ và trung tâm → transform → upsert vào BigQuery.
"""

import io
import json
import logging
import unicodedata
from datetime import date, timedelta, timezone, datetime
from collections import defaultdict

from google.cloud import bigquery

from config_crm import (
    GCP_PROJECT_ID,
    BQ_DATASET,
    BQ_TABLE_LEADS,
    DOCTOR_SHEETS,
    CENTER_CRM_SHEETS,
    DOCTOR_METADATA,
    UPSERT_DELETE_BEFORE_INSERT,
)
from sheets_reader import read_crm_sheet, read_center_crm_sheet

logger = logging.getLogger(__name__)

_bq_client = None


def _get_bq_client():
    global _bq_client
    if _bq_client is None:
        _bq_client = bigquery.Client(project=GCP_PROJECT_ID)
    return _bq_client


def _map_channel_to_doctor_meta(channel: str, specialty_code: str) -> dict:
    if not channel:
        return None
    clean = channel.strip().lower()
    
    for doc_key, meta in DOCTOR_METADATA.items():
        # Match doctor name (e.g. BS Định -> "định" or "dinh")
        key_clean = doc_key.replace("BS ", "").strip().lower()
        
        def remove_accents(s):
            s = unicodedata.normalize("NFD", s)
            s = "".join(c for c in s if unicodedata.category(c) != "Mn")
            return s.replace("đ", "d").replace("D", "d")
        
        if remove_accents(key_clean) in remove_accents(clean):
            return meta
    return None


def run(
    start_date: str = None,
    end_date: str   = None,
    doctors: list[str] = None,
    versions: list[int] = None,
) -> dict:
    """
    Chạy pipeline CRM.
    - start_date / end_date: khoảng ngày cần đồng bộ (mặc định 7 ngày gần nhất)
    - doctors: danh sách các cấu hình cần chạy (mặc định: tất cả)
    """
    today     = date.today()
    end_str   = end_date   or today.strftime("%Y-%m-%d")
    start_str = start_date or (today - timedelta(days=7)).strftime("%Y-%m-%d")

    start_date_obj = datetime.strptime(start_str, "%Y-%m-%d").date()
    end_date_obj = datetime.strptime(end_str, "%Y-%m-%d").date()

    if versions is None:
        versions = list(range(start_date_obj.year, end_date_obj.year + 1))

    logger.info("=" * 60)
    logger.info(f"[CRM Pipeline] BẮT ĐẦU: {start_str} → {end_str} (versions: {versions})")
    logger.info("=" * 60)

    results = []
    total_inserted = 0

    # 1) Xử lý nhóm Dược Nano (nếu được yêu cầu hoặc mặc định chạy hết)
    if not doctors or "Dược Nano" in doctors:
        cfg = DOCTOR_SHEETS.get("Dược Nano")
        if cfg:
            logger.info(f"[CRM] Đang đồng bộ Dược Nano ({cfg['spreadsheet_id']})")
            try:
                raw_rows = read_crm_sheet(
                    cfg["spreadsheet_id"],
                    start_str,
                    end_str,
                    sheet_type=cfg.get("sheet_type", "doctor"),
                    sheet_title=cfg.get("sheet_title"),
                )
                
                now_utc = datetime.now(timezone.utc).isoformat()
                bq_rows = []
                for r in raw_rows:
                    bq_rows.append({
                        "inserted_at":      now_utc,
                        "lead_date":        r["lead_date"],
                        "page_id":          cfg["spreadsheet_id"],
                        "doctor_name":      cfg["doctor_name"],
                        "specialty_code":   r.get("specialty_code", cfg["specialty_code"]),
                        "specialty_name":   r.get("specialty_name", cfg["specialty_name"]),
                        "report_group":     cfg["report_group"],
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
                
                inserted = _upsert_to_bq(bq_rows, start_str, end_str, cfg["spreadsheet_id"])
                total_inserted += inserted
                results.append({
                    "doctor":    "Dược Nano",
                    "rows_read": len(raw_rows),
                    "inserted":  inserted,
                    "status":    "ok",
                })
            except Exception as exc:
                logger.error(f"[CRM] Lỗi đồng bộ Dược Nano: {exc}", exc_info=True)
                results.append({
                    "doctor":  "Dược Nano",
                    "status":  "error",
                    "message": str(exc),
                })

    # 2) Xử lý nhóm Y tế (kết nối Center CRM sheets và Doctor sheets)
    # Nếu bộ lọc doctors chỉ chứa Dược Nano, bỏ qua phần Y tế.
    if not doctors or any(d != "Dược Nano" for d in doctors):
        logger.info(f"[CRM] Đang đồng bộ nhóm Y tế (Tổng hợp từ Trung tâm CRM và Bác sĩ)...")
        
        try:
            # B2.1: Xây dựng bản đồ phone -> (ad_id, subscriber_id, spreadsheet_id) từ tất cả các sheet Bác sĩ
            # Đọc khoảng ngày rộng hơn (90 ngày trước start_date) để bắt được ad_id
            start_date_obj = datetime.strptime(start_str, "%Y-%m-%d").date()
            start_lookback_obj = start_date_obj - timedelta(days=90)
            start_lookback_str = start_lookback_obj.strftime("%Y-%m-%d")
            
            logger.info(f"[CRM] Đang xây dựng bản đồ ad_id từ các sheet Bác sĩ từ ngày {start_lookback_str}...")
            phone_to_ad_id = {}
            
            for doc_key, cfg in DOCTOR_SHEETS.items():
                if cfg["report_group"] != "Y tế":
                    continue
                try:
                    raw_doc_rows = read_crm_sheet(
                        cfg["spreadsheet_id"],
                        start_lookback_str,
                        end_str,
                        sheet_type="doctor"
                    )
                    for r in raw_doc_rows:
                        phone = r["phone"]
                        if phone and r["ad_id"]:
                            phone_to_ad_id[phone] = {
                                "ad_id": r["ad_id"],
                                "subscriber_id": r.get("subscriber_id", ""),
                                "spreadsheet_id": cfg["spreadsheet_id"]
                            }
                except Exception as e:
                    logger.warning(f"[CRM] Bỏ qua lỗi đọc sheet Bác sĩ {doc_key}: {e}")
            
            logger.info(f"[CRM] Bản đồ ad_id đã thu thập được {len(phone_to_ad_id)} SĐT từ các sheet Bác sĩ")

            # B2.2: Đọc dữ liệu từ các sheet Trung tâm CRM và thực hiện ghép nối
            y_te_bq_rows = []
            
            for center_key, cfg in CENTER_CRM_SHEETS.items():
                if versions and cfg.get("version") not in versions:
                    continue
                # Cho phép filter theo bác sĩ nếu người dùng truyền danh sách doctors
                if doctors:
                    # Kiểm tra xem specialty_code có khớp với các bác sĩ trong filter không
                    doc_specs = [DOCTOR_SHEETS[d]["specialty_code"] for d in doctors if d in DOCTOR_SHEETS]
                    if cfg["specialty_code"] not in doc_specs:
                        continue
                
                spreadsheet_id = cfg["spreadsheet_id"]
                specialty_code = cfg["specialty_code"]
                specialty_name = cfg["specialty_name"]
                main_tab       = cfg["main_tab"]
                arrival_tab    = cfg["arrival_tab"]
                version        = cfg["version"]
                
                logger.info(f"[CRM] Đọc trung tâm: {center_key} ({spreadsheet_id})")
                
                try:
                    center_rows = read_center_crm_sheet(
                        spreadsheet_id=spreadsheet_id,
                        main_tab=main_tab,
                        arrival_tab=arrival_tab,
                        start_date=start_str,
                        end_date=end_str,
                        specialty_code=specialty_code,
                        version=version
                    )
                    logger.info(f"[CRM] {center_key}: {len(center_rows)} dòng hợp lệ")
                    
                    now_utc = datetime.now(timezone.utc).isoformat()
                    
                    for r in center_rows:
                        phone = r["phone"]
                        channel = r["channel"]
                        
                        # A) Ghép nối lấy ad_id từ sheet Bác sĩ
                        ad_info = phone_to_ad_id.get(phone)
                        ad_id = ad_info["ad_id"] if ad_info else ""
                        subscriber_id = ad_info["subscriber_id"] if ad_info else ""
                        
                        # B) Xác định thông tin bác sĩ để gán page_id và doctor_name
                        meta_doc = _map_channel_to_doctor_meta(channel, specialty_code)
                        
                        # Khởi tạo chuyên khoa mặc định từ cấu hình Trung tâm
                        lead_specialty_code = specialty_code
                        lead_specialty_name = specialty_name
                        
                        if ad_info:
                            # Nếu khớp SĐT quảng cáo, lấy page_id (spreadsheet_id) của bác sĩ đó
                            page_id = ad_info["spreadsheet_id"]
                            doctor_name = "TỰ NHIÊN / KHÁC"
                            for k, v in DOCTOR_SHEETS.items():
                                if v["spreadsheet_id"] == page_id:
                                    doctor_name = v["doctor_name"]
                                    lead_specialty_code = v["specialty_code"]
                                    lead_specialty_name = v["specialty_name"]
                                    break
                        elif meta_doc:
                            # Nếu không khớp SĐT quảng cáo nhưng khớp tên bác sĩ qua cột Kênh
                            page_id = meta_doc["page_id"]
                            doctor_name = meta_doc["doctor_name"]
                            lead_specialty_code = meta_doc["specialty_code"]
                            lead_specialty_name = meta_doc["specialty_name"]
                        else:
                            # Mặc định
                            page_id = spreadsheet_id  # Dùng spreadsheet_id của Trung tâm làm page_id tạm
                            doctor_name = f"BS Trung tâm {specialty_name}"
                            
                        y_te_bq_rows.append({
                            "inserted_at":      now_utc,
                            "lead_date":        r["lead_date"],
                            "page_id":          page_id,
                            "doctor_name":      doctor_name,
                            "specialty_code":   lead_specialty_code,
                            "specialty_name":   lead_specialty_name,
                            "report_group":     "Y tế",
                            "subscriber_id":    subscriber_id,
                            "phone":            phone,
                            "ad_id":            ad_id,
                            "ad_name":          "",
                            "conversation_id":  "",
                            "booking_status":   r["booking_status"],
                            "arrival_status":   r["arrival_status"],
                            "is_booking":       r["is_booking"],
                            "is_arrival":       r["is_arrival"],
                            "note":             "",
                            "revenue":          r["revenue"],
                        })
                except Exception as e_center:
                    logger.error(f"[CRM] Lỗi đọc trung tâm {center_key}: {e_center}", exc_info=True)
                    results.append({
                        "doctor":  center_key,
                        "status":  "error",
                        "message": str(e_center),
                    })

            # B2.3: Nhóm các dòng theo page_id và thực hiện upsert
            grouped = defaultdict(list)
            for row in y_te_bq_rows:
                grouped[row["page_id"]].append(row)
                
            for p_id, rows_for_page in grouped.items():
                inserted = _upsert_to_bq(rows_for_page, start_str, end_str, p_id)
                total_inserted += inserted
                
                # Tìm tên bác sĩ / trung tâm tương ứng với page_id để lưu log
                name_log = p_id
                for k, v in DOCTOR_SHEETS.items():
                    if v["spreadsheet_id"] == p_id:
                        name_log = v["doctor_name"]
                        break
                for k, v in CENTER_CRM_SHEETS.items():
                    if v["spreadsheet_id"] == p_id:
                        name_log = k
                        break
                        
                results.append({
                    "doctor":    name_log,
                    "rows_read": len(rows_for_page),
                    "inserted":  inserted,
                    "status":    "ok",
                })
                
        except Exception as exc:
            logger.error(f"[CRM] Lỗi đồng bộ nhóm Y tế: {exc}", exc_info=True)
            results.append({
                "doctor":  "Y tế",
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
