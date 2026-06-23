import logging
from google.cloud import bigquery

logging.basicConfig(level=logging.INFO)

def main():
    project_id = "gen-lang-client-0738410622"
    dataset_id = "marketing_data"
    client = bigquery.Client(project=project_id)
    
    query = f"""
        SELECT DISTINCT account_id, doctor_name, campaign_name, ad_name, post_link, thumbnail_url, content 
        FROM `{project_id}.{dataset_id}.fb_ad_insights`
        WHERE LOWER(doctor_name) LIKE '%tuyên%' 
           OR LOWER(campaign_name) LIKE '%tuyen%'
           OR LOWER(campaign_name) LIKE '%tuyên%'
           OR account_id = 'act_1433365117712667'
    """
    
    print("Running query...")
    query_job = client.query(query)
    results = list(query_job.result())
    print(f"Found {len(results)} rows.")
    for idx, row in enumerate(results[:10]):
        print(f"\nRow {idx+1}:")
        print(f"  account_id: {row.account_id}")
        print(f"  doctor_name: {row.doctor_name}")
        print(f"  campaign_name: {row.campaign_name}")
        print(f"  ad_name: {row.ad_name}")
        print(f"  post_link: {row.post_link}")
        print(f"  thumbnail_url: {row.thumbnail_url}")
        print(f"  content: {row.content[:100] if row.content else ''}")

if __name__ == "__main__":
    main()
