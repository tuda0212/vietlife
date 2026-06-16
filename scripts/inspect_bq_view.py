from google.cloud import bigquery

def main():
    project_id = "gen-lang-client-0738410622"
    dataset_id = "marketing_data"
    client = bigquery.Client(project=project_id)
    
    table = client.get_table(f"{project_id}.{dataset_id}.v_report")
    with open("v_report_definition.sql", "w", encoding="utf-8") as f:
        f.write(table.view_query)
    print("Saved view to v_report_definition.sql")

if __name__ == "__main__":
    main()
