import logging
from google.cloud import bigquery

logging.basicConfig(level=logging.INFO)

def main():
    project_id = "gen-lang-client-0738410622"
    dataset_id = "marketing_data"
    client = bigquery.Client(project=project_id)
    
    # List tables and views in the dataset
    print("Listing tables in marketing_data:")
    dataset_ref = client.dataset(dataset_id)
    tables = list(client.list_tables(dataset_ref))
    for t in tables:
        print(f"- {t.table_id} ({t.table_type})")
        
    # Get schema and definition for tables/views
    for target in ["fb_ad_insights", "botcake_leads", "v_report"]:
        try:
            table = client.get_table(f"{project_id}.{dataset_id}.{target}")
            print(f"\n==================== {target} ====================")
            print(f"Table type: {table.table_type}")
            if table.table_type == "VIEW":
                print("View SQL:")
                print(table.view_query)
            else:
                print("Schema:")
                for field in table.schema:
                    print(f"  {field.name}: {field.field_type} ({field.mode})")
        except Exception as e:
            print(f"\nCould not fetch {target}: {e}")

if __name__ == "__main__":
    main()
