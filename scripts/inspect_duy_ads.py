import logging
from google.cloud import bigquery

logging.basicConfig(level=logging.INFO)

def main():
    project_id = "gen-lang-client-0738410622"
    dataset_id = "marketing_data"
    client = bigquery.Client(project=project_id)
    
    query = f"""
        SELECT account_id, COUNT(*) as cnt
        FROM `{project_id}.{dataset_id}.fb_ad_insights`
        WHERE LOWER(doctor_name) LIKE '%phạm duy%' 
           OR LOWER(campaign_name) LIKE '%phạm duy%'
           OR LOWER(campaign_name) LIKE '%pham duy%'
        GROUP BY account_id
    """
    
    print("Running query...")
    query_job = client.query(query)
    results = list(query_job.result())
    print(f"Found {len(results)} accounts.")
    for idx, row in enumerate(results):
        print(f"  account_id: {row.account_id}, count: {row.cnt}")

if __name__ == "__main__":
    main()
