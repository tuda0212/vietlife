"""
bq_loader.py — Ghi dữ liệu vào BigQuery.
Upsert: xóa dữ liệu cũ cùng start_date + end_date + account_id trước khi insert.
"""

import logging
import io
import json

from google.cloud import bigquery

from config import (
    BQ_DATASET,
    BQ_TABLE,
    BQ_TABLE_DEMOGRAPHICS,
    GCP_PROJECT_ID,
    UPSERT_DELETE_BEFORE_INSERT,
)

logger = logging.getLogger(__name__)

_client = None


def _get_client() -> bigquery.Client:
    global _client
    if _client is None:
        _client = bigquery.Client(project=GCP_PROJECT_ID)
    return _client


def upsert_rows(
    rows: list[dict],
    start_date: str,
    end_date: str,
    account_ids: list[str],
) -> int:
    """
    Xóa dữ liệu cũ cùng khoảng ngày + account → insert mới.
    Trả về số dòng đã insert.
    """
    if not rows:
        logger.warning("[BQ] Không có dòng nào để insert.")
        return 0

    client = _get_client()
    table_ref = f"{GCP_PROJECT_ID}.{BQ_DATASET}.{BQ_TABLE}"

    # --- Xóa dữ liệu cũ ---
    if UPSERT_DELETE_BEFORE_INSERT and account_ids:
        ids_str = ", ".join(f"'{a}'" for a in account_ids)
        delete_sql = f"""
            DELETE FROM `{table_ref}`
            WHERE start_date BETWEEN '{start_date}' AND '{end_date}'
              AND account_id  IN ({ids_str})
        """
        logger.info(
            f"[BQ] Xóa dữ liệu cũ: {start_date} → {end_date}, accounts: {account_ids}")
        client.query(delete_sql).result()

    # --- Insert mới ---
    table = client.get_table(table_ref)
    job_config = bigquery.LoadJobConfig(
        write_disposition=bigquery.WriteDisposition.WRITE_APPEND,
        source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
        autodetect=False,
    )
    ndjson = "\n".join(json.dumps(row, default=str) for row in rows)
    buffer = io.BytesIO(ndjson.encode("utf-8"))

    load_job = client.load_table_from_file(
        buffer, table, job_config=job_config)
    load_job.result()

    if load_job.errors:
        logger.error(f"[BQ] Lỗi insert: {load_job.errors}")
        raise RuntimeError(f"BigQuery load errors: {load_job.errors}")

    logger.info(f"[BQ] Đã insert {load_job.output_rows} dòng vào {table_ref}")
    return load_job.output_rows


def query_report(
    start_date: str,
    end_date: str,
    specialty_code: str = None,
) -> list[dict]:
    """
    Query v_report để kiểm tra kết quả sau khi pipeline chạy.
    """
    client = _get_client()
    view = f"{GCP_PROJECT_ID}.{BQ_DATASET}.v_report"

    where = f"WHERE start_date = '{start_date}' AND end_date = '{end_date}'"
    if specialty_code:
        where += f" AND specialty_code = '{specialty_code}'"

    sql = f"SELECT * FROM `{view}` {where} ORDER BY doctor_name, spend DESC"
    result = client.query(sql).result()
    return [dict(row) for row in result]


def _create_demographics_table_if_not_exists(client, table_ref: str):
    from google.cloud import bigquery
    from google.cloud.exceptions import NotFound
    try:
        client.get_table(table_ref)
    except NotFound:
        logger.info(f"[BQ] Khởi tạo bảng demographics mới: {table_ref}")
        schema = [
            bigquery.SchemaField("inserted_at", "TIMESTAMP", mode="REQUIRED"),
            bigquery.SchemaField("run_date", "DATE", mode="REQUIRED"),
            bigquery.SchemaField("start_date", "DATE", mode="REQUIRED"),
            bigquery.SchemaField("end_date", "DATE", mode="REQUIRED"),
            bigquery.SchemaField("account_id", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("ad_id", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("ad_name", "STRING", mode="NULLABLE"),
            bigquery.SchemaField("campaign_name", "STRING", mode="NULLABLE"),
            bigquery.SchemaField("specialty_code", "STRING", mode="NULLABLE"),
            bigquery.SchemaField("specialty_name", "STRING", mode="NULLABLE"),
            bigquery.SchemaField("doctor_name", "STRING", mode="NULLABLE"),
            bigquery.SchemaField("spend", "FLOAT", mode="REQUIRED"),
            bigquery.SchemaField("clicks", "INTEGER", mode="REQUIRED"),
            bigquery.SchemaField("impressions", "INTEGER", mode="REQUIRED"),
            bigquery.SchemaField("reach", "INTEGER", mode="REQUIRED"),
            bigquery.SchemaField("mes", "INTEGER", mode="REQUIRED"),
            bigquery.SchemaField("breakdown_type", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("age", "STRING", mode="NULLABLE"),
            bigquery.SchemaField("gender", "STRING", mode="NULLABLE"),
            bigquery.SchemaField("region", "STRING", mode="NULLABLE"),
        ]
        table = bigquery.Table(table_ref, schema=schema)
        # Phân vùng theo start_date giúp tối ưu hóa chi phí
        table.time_partitioning = bigquery.TimePartitioning(
            type_=bigquery.TimePartitioningType.DAY,
            field="start_date"
        )
        client.create_table(table)
        logger.info("[BQ] Tạo bảng demographics thành công.")


def upsert_demographics_rows(
    rows: list[dict],
    start_date: str,
    end_date: str,
    account_ids: list[str],
) -> int:
    if not rows:
        return 0

    client = _get_client()
    table_ref = f"{GCP_PROJECT_ID}.{BQ_DATASET}.{BQ_TABLE_DEMOGRAPHICS}"

    _create_demographics_table_if_not_exists(client, table_ref)

    if UPSERT_DELETE_BEFORE_INSERT and account_ids:
        ids_str = ", ".join(f"'{a}'" for a in account_ids)
        delete_sql = f"""
            DELETE FROM `{table_ref}`
            WHERE start_date BETWEEN '{start_date}' AND '{end_date}'
              AND account_id  IN ({ids_str})
        """
        logger.info(
            f"[BQ Demographics] Xóa dữ liệu cũ: {start_date} → {end_date}")
        client.query(delete_sql).result()

    table = client.get_table(table_ref)
    job_config = bigquery.LoadJobConfig(
        write_disposition=bigquery.WriteDisposition.WRITE_APPEND,
        source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
        autodetect=False,
    )
    ndjson = "\n".join(json.dumps(row, default=str) for row in rows)
    buffer = io.BytesIO(ndjson.encode("utf-8"))

    load_job = client.load_table_from_file(
        buffer, table, job_config=job_config)
    load_job.result()

    logger.info(f"[BQ Demographics] Đã insert {load_job.output_rows} dòng.")
    return load_job.output_rows
