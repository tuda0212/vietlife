import logging
from google.cloud import bigquery

logging.basicConfig(level=logging.INFO)

def main():
    project_id = "gen-lang-client-0738410622"
    dataset_id = "marketing_data"
    client = bigquery.Client(project=project_id)
    
    query = f"""
    SELECT 
      date,
      specialty_name,
      doctor_name,
      spend,
      revenue,
      mes_cmt,
      sdts,
      dat_lich,
      den_cua
    FROM `{project_id}.{dataset_id}.v_report_y_te`
    WHERE date BETWEEN '2026-06-01' AND '2026-06-17'
      AND specialty_code = 'CXK'
    ORDER BY date DESC, spend DESC
    """
    
    query_job = client.query(query)
    results = list(query_job.result())
    
    print("DATE|SPECIALTY|DOCTOR|SPEND|REVENUE|MES_CMT|SDTS|DAT_LICH|DEN_CUA")
    for r in results:
        print(f"{r.date}|{r.specialty_name}|{r.doctor_name}|{r.spend}|{r.revenue}|{r.mes_cmt}|{r.sdts}|{r.dat_lich}|{r.den_cua}")

if __name__ == "__main__":
    main()
