"""
main.py — Entry point Flask cho Cloud Run.

Endpoints:
  GET  /health        Health check
  POST /run           Pipeline 1: Facebook Ads → BigQuery fb_ad_insights
  POST /run-crm       Pipeline 2: Google Sheets CRM → BigQuery botcake_leads
  POST /run-all       Chạy cả 2 pipeline tuần tự
"""

import logging
import os
from flask import Flask, jsonify, request

from pipeline import run as run_fb_pipeline
from crm_pipeline import run as run_crm_pipeline

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)

app = Flask(__name__)


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"}), 200


@app.route("/run", methods=["POST"])
def run():
    """
    Pipeline 1: Facebook Ads → BigQuery.
    Body JSON (optional):
      start_date  : "YYYY-MM-DD"
      end_date    : "YYYY-MM-DD"
      account_ids : ["act_xxx"]
    """
    body        = request.get_json(silent=True) or {}
    start_date  = body.get("start_date")
    end_date    = body.get("end_date")
    account_ids = body.get("account_ids")

    logger.info(f"[/run] {body}")
    try:
        result = run_fb_pipeline(
            start_date  = start_date,
            end_date    = end_date,
            account_ids = account_ids,
        )
        return jsonify(result), 200
    except Exception as exc:
        logger.exception(f"[/run] Lỗi: {exc}")
        return jsonify({"status": "error", "message": str(exc)}), 500


@app.route("/run-crm", methods=["POST"])
def run_crm():
    """
    Pipeline 2: Google Sheets CRM → BigQuery.
    Body JSON (optional):
      start_date : "YYYY-MM-DD"
      end_date   : "YYYY-MM-DD"
      doctors    : ["Định", "Tuyên"]  (mặc định: tất cả)
    """
    body       = request.get_json(silent=True) or {}
    start_date = body.get("start_date")
    end_date   = body.get("end_date")
    doctors    = body.get("doctors")

    logger.info(f"[/run-crm] {body}")
    try:
        result = run_crm_pipeline(
            start_date = start_date,
            end_date   = end_date,
            doctors    = doctors,
        )
        return jsonify(result), 200
    except Exception as exc:
        logger.exception(f"[/run-crm] Lỗi: {exc}")
        return jsonify({"status": "error", "message": str(exc)}), 500


@app.route("/run-all", methods=["POST"])
def run_all():
    """Chạy cả Pipeline 1 + Pipeline 2 tuần tự."""
    body       = request.get_json(silent=True) or {}
    start_date = body.get("start_date")
    end_date   = body.get("end_date")

    logger.info(f"[/run-all] {body}")
    try:
        fb_result  = run_fb_pipeline(start_date=start_date, end_date=end_date)
        crm_result = run_crm_pipeline(start_date=start_date, end_date=end_date)
        return jsonify({
            "status":     "ok",
            "fb_ads":     fb_result,
            "crm":        crm_result,
        }), 200
    except Exception as exc:
        logger.exception(f"[/run-all] Lỗi: {exc}")
        return jsonify({"status": "error", "message": str(exc)}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False)
