from google.cloud import bigquery

client = bigquery.Client(project="gen-lang-client-0738410622")

query = """
SELECT DISTINCT specialty_code, specialty_name 
FROM `gen-lang-client-0738410622.marketing_data.fb_ad_insights`
"""
print("Danh sach specialty trong fb_ad_insights:")
for r in client.query(query).result():
    print(f"Code: {r.specialty_code}, Name: {r.specialty_name}")

# Kiểm tra campaign name có brand
query_brand = """
SELECT campaign_name, COUNT(*) as cnt 
FROM `gen-lang-client-0738410622.marketing_data.fb_ad_insights`
WHERE LOWER(campaign_name) LIKE '%brand%' OR LOWER(specialty_name) LIKE '%brand%' OR LOWER(specialty_code) LIKE '%brand%'
GROUP BY campaign_name
LIMIT 10
"""
print("\nDanh sach campaign lien quan den Brand:")
for r in client.query(query_brand).result():
    print(f"Campaign: {r.campaign_name} (Số lượng: {r.cnt})")
