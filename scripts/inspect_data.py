from google.cloud import bigquery

def main():
    project_id = "gen-lang-client-0738410622"
    dataset_id = "marketing_data"
    client = bigquery.Client(project=project_id)
    
    print("--- FB Ad Insights Distinct Values ---")
    query_fb = f"""
    SELECT doctor_name, specialty_code, count(*) as count
    FROM `{project_id}.{dataset_id}.fb_ad_insights`
    GROUP BY doctor_name, specialty_code
    """
    for row in client.query(query_fb).result():
        print(f"doctor_name: {row.doctor_name}, specialty_code: {row.specialty_code}, count: {row.count}")
        
    print("\n--- Botcake Leads Distinct Values ---")
    query_leads = f"""
    SELECT doctor_name, specialty_code, report_group, count(*) as count
    FROM `{project_id}.{dataset_id}.botcake_leads`
    GROUP BY doctor_name, specialty_code, report_group
    """
    for row in client.query(query_leads).result():
        print(f"doctor_name: {row.doctor_name}, specialty_code: {row.specialty_code}, report_group: {row.report_group}, count: {row.count}")

if __name__ == "__main__":
    main()
