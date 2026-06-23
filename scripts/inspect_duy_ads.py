import logging
from google.cloud import bigquery

logging.basicConfig(level=logging.INFO)

def main():
    project_id = "gen-lang-client-0738410622"
    dataset_id = "marketing_data"
    client = bigquery.Client(project=project_id)
    
    # Tìm kiếm bác sĩ Hùng
    query_hung = f"""
        SELECT account_id, COUNT(*) as cnt
        FROM `{project_id}.{dataset_id}.fb_ad_insights`
        WHERE LOWER(doctor_name) LIKE '%hùng%' 
           OR LOWER(campaign_name) LIKE '%hung%'
        GROUP BY account_id
    """
    
    # Tìm kiếm bác sĩ Vũ Anh
    query_vuanh = f"""
        SELECT account_id, COUNT(*) as cnt
        FROM `{project_id}.{dataset_id}.fb_ad_insights`
        WHERE LOWER(doctor_name) LIKE '%vũ anh%' 
           OR LOWER(doctor_name) LIKE '%vu anh%'
           OR LOWER(doctor_name) LIKE '%vũ ảnh%'
           OR LOWER(campaign_name) LIKE '%vũ anh%'
           OR LOWER(campaign_name) LIKE '%vu anh%'
           OR LOWER(campaign_name) LIKE '%vũ ảnh%'
        GROUP BY account_id
    """
    
    print("Running query for Dr Hung...")
    query_job = client.query(query_hung)
    results = list(query_job.result())
    print(f"Found {len(results)} accounts for Dr Hung.")
    for idx, row in enumerate(results):
        print(f"  account_id: {row.account_id}, count: {row.cnt}")
        
    print("\nRunning query for Dr Vu Anh...")
    query_job = client.query(query_vuanh)
    results = list(query_job.result())
    print(f"Found {len(results)} accounts for Dr Vu Anh.")
    for idx, row in enumerate(results):
        print(f"  account_id: {row.account_id}, count: {row.cnt}")

if __name__ == "__main__":
    main()
