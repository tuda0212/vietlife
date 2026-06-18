import logging
from google.cloud import bigquery

logging.basicConfig(level=logging.INFO)

def main():
    project_id = "gen-lang-client-0738410622"
    dataset_id = "marketing_data"
    client = bigquery.Client(project=project_id)
    
    # Tìm dòng của BS Phạm Duy ngày 2026-06-17
    query = f"""
    SELECT 
      lead_date,
      doctor_name,
      specialty_code,
      specialty_name,
      phone,
      ad_id,
      ad_name,
      page_id
    FROM `{project_id}.{dataset_id}.botcake_leads`
    WHERE lead_date = '2026-06-17'
      AND doctor_name = 'BS Phạm Duy'
    """
    
    query_job = client.query(query)
    results = list(query_job.result())
    
    print("Thông tin lead BS Phạm Duy ngày 17/6/2026:")
    for r in results:
        print(f"Date: {r.lead_date}, Doctor: {r.doctor_name}, Specialty: {r.specialty_code} ({r.specialty_name}), Phone: {r.phone}, Ad ID: {r.ad_id}, Ad Name: {r.ad_name}, Page ID: {r.page_id}")

if __name__ == "__main__":
    main()
