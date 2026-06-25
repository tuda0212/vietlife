import os
from google.cloud import bigquery
from config_crm import GCP_PROJECT_ID

def main():
    client = bigquery.Client(project=GCP_PROJECT_ID)
    
    sql = """
        SELECT DISTINCT 
            doctor_name, 
            specialty_name 
        FROM `gen-lang-client-0738410622.marketing_data.botcake_leads`
        WHERE report_group = 'Y tế'
        ORDER BY specialty_name, doctor_name;
    """
    
    print("Danh sách bác sĩ thực tế ghi nhận trong BigQuery (botcake_leads):")
    try:
        query_job = client.query(sql)
        rows = list(query_job.result())
        for r in rows:
            print(f" - {r.doctor_name} ({r.specialty_name})")
    except Exception as e:
        print("Error query:", e)

if __name__ == "__main__":
    main()
