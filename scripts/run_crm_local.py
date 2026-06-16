import sys
import os
import logging

# Tự động tìm đường dẫn tới thư mục 'files' trong workspace
workspace_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
files_dir = os.path.join(workspace_dir, "files")
sys.path.append(files_dir)

import crm_pipeline

logging.basicConfig(level=logging.INFO)

try:
    print("Starting CRM pipeline sync for 'Dược Nano'...")
    res = crm_pipeline.run(
        start_date="2020-01-01",
        end_date="2026-06-15",
        doctors=["Dược Nano"]
    )
    print("Success! Result:")
    print(res)
except Exception as e:
    print(f"Failed to run CRM pipeline: {e}")
