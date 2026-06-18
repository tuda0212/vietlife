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

def main():
    sheet_id = "1guUru-qTB6Pug4Oc43fqoEw3UUVmFXs2R7MAUr3AIGY"
    gid = "1357441053"  # GID của tab 'Hiệu quả bài (T3)'
    token = get_access_token()
    if not token:
        print("Could not retrieve access token.")
        return
        
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"
    print(f"Downloading CSV from export link with auth token: {url}")
    
    req = urllib.request.Request(url)
    req.add_header("Authorization", f"Bearer {token}")
    
    try:
        # Sử dụng timeout 30 giây để tránh treo vô hạn
        with urllib.request.urlopen(req, timeout=30) as response:
            content = response.read().decode('utf-8')
            
        print("Successfully downloaded CSV!")
        
        # Đọc dữ liệu CSV
        csv_reader = csv.reader(io.StringIO(content))
        rows = list(csv_reader)
        print(f"Read {len(rows)} rows from CSV:")
        
        # In ra 50 dòng đầu
        for i, row in enumerate(rows[:50]):
            clean_row = [str(cell) if cell is not None else "" for cell in row]
            if any(clean_row):
                print(f"Row {i+1}: {clean_row[:15]}")
                
    except urllib.error.HTTPError as e:
        print(f"HTTP Error: {e.code} - {e.reason}")
        try:
            print("Details:", e.read().decode('utf-8')[:200])
        except Exception:
            pass
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
