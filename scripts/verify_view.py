from google.cloud import bigquery

def verify_view(client, project_id, dataset_id, view_name):
    print(f"\n--- Xác thực View: {view_name} ---")
    try:
        # 1. Đếm tổng số dòng
        row_count_query = f"SELECT count(*) as total_rows FROM `{project_id}.{dataset_id}.{view_name}`"
        res = list(client.query(row_count_query).result())
        print(f"Tổng số dòng trong {view_name}: {res[0].total_rows}")
        
        # 2. Lấy mẫu dữ liệu
        sample_query = f"SELECT * FROM `{project_id}.{dataset_id}.{view_name}` LIMIT 3"
        rows = list(client.query(sample_query).result())
        print(f"Lấy mẫu {len(rows)} dòng:")
        for idx, row in enumerate(rows):
            print(f"  Dòng {idx+1}: {dict(row)}")
    except Exception as e:
        print(f"Lỗi khi xác thực {view_name}: {e}")

def verify():
    project_id = "gen-lang-client-0738410622"
    dataset_id = "marketing_data"
    client = bigquery.Client(project=project_id)
    
    for view_name in ["v_report", "v_report_y_te", "v_report_y_te_detail", "v_report_duoc"]:
        verify_view(client, project_id, dataset_id, view_name)

if __name__ == "__main__":
    verify()
