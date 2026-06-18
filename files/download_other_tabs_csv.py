import urllib.request
import urllib.error
import subprocess
import csv
import io

def get_access_token():
    try:
        token = subprocess.check_output(
            ["gcloud", "auth", "print-access-token"],
            text=True,
            stderr=subprocess.DEVNULL
        ).strip()
        return token
    except Exception as e:
        print(f"Error getting gcloud token: {e}")
        return None

def test_download_tab(sheet_id, gid, tab_name, token):
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"
    print(f"\n--- Testing download for tab '{tab_name}' (GID: {gid}) ---")
    req = urllib.request.Request(url)
    req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=20) as response:
            content = response.read().decode('utf-8')
        print(f"Success downloading '{tab_name}'!")
        csv_reader = csv.reader(io.StringIO(content))
        rows = list(csv_reader)
        print(f"Total rows: {len(rows)}")
        if rows:
            print(f"Header: {rows[0][:15]}")
            # In ra 5 dòng dữ liệu đầu
            for i, r in enumerate(rows[1:6]):
                print(f"  Row {i+2}: {r[:10]}")
        return rows
    except Exception as e:
        print(f"Error downloading '{tab_name}': {e}")
        return None

def main():
    sheet_id = "1guUru-qTB6Pug4Oc43fqoEw3UUVmFXs2R7MAUr3AIGY"
    token = get_access_token()
    if not token:
        return
        
    # Test 3 tab tiềm năng chứa dữ liệu thô
    test_download_tab(sheet_id, "452462375", "Data CRM Clean", token)
    test_download_tab(sheet_id, "77557067", "DATA KHÁCH", token)
    test_download_tab(sheet_id, "1202314784", "Khách Đến Cửa", token)

if __name__ == "__main__":
    main()
