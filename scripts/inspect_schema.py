from google.cloud import bigquery

client = bigquery.Client(project="gen-lang-client-0738410622")

for table_id in ["fb_ad_insights", "botcake_leads"]:
    table = client.get_table(f"gen-lang-client-0738410622.marketing_data.{table_id}")
    print(f"Schema of {table_id}:")
    for field in table.schema:
        print(f"  {field.name}: {field.field_type}")
