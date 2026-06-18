import os
from google.cloud import bigquery
from config_crm import GCP_PROJECT_ID

def main():
    client = bigquery.Client(project=GCP_PROJECT_ID)
    table_id = "gen-lang-client-0738410622.marketing_data.v_report_y_te_detail"
    try:
        table = client.get_table(table_id)
        print(f"Schema for {table_id}:")
        for field in table.schema:
            print(f" - {field.name}: {field.field_type}")
    except Exception as e:
        print("Error:", e)

if __name__ == "__main__":
    main()
