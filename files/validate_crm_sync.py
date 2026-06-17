import sys
import os
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s — %(message)s")
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from crm_pipeline import run as run_crm_pipeline

def validate():
    print("=== STARTING PIPELINE VALIDATION ===")
    
    # We run the pipeline for the period 2026-06-01 to 2026-06-15
    start_date = "2026-06-01"
    end_date = "2026-06-15"
    
    # Run the CRM pipeline
    result = run_crm_pipeline(start_date=start_date, end_date=end_date)
    
    print("\n=== VALIDATION RESULT ===")
    print(f"Status: {result.get('status')}")
    print(f"Total inserted: {result.get('total_inserted')}")
    for detail in result.get("details", []):
        print(f" - Config: {detail.get('doctor')}, Read: {detail.get('rows_read')}, Inserted: {detail.get('inserted')}, Status: {detail.get('status')}")
        if detail.get("status") == "error":
            print(f"   Error Message: {detail.get('message')}")

if __name__ == "__main__":
    validate()
