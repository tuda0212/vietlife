import urllib.request
import urllib.error
import subprocess
import csv
import io
import socket
from collections import Counter

# Tăng timeout hệ thống lên 150 giây
socket.setdefaulttimeout(150)

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
    print(f"Downloading CSV from: {url} (with 120s timeout)")
    
    req = urllib.request.Request(url)
    req.add_header("Authorization", f"Bearer {token}")
    
    try:
        # Sử dụng timeout 120 giây
        with urllib.request.urlopen(req, timeout=120) as response:
            content = response.read().decode('utf-8')
            
        csv_reader = csv.reader(io.StringIO(content))
        rows = list(csv_reader)
        
        if not rows:
            print("Empty sheet.")
            return
            
        header = rows[0]
        print(f"\nHeader row (Total columns: {len(header)}):")
        for idx, col in enumerate(header):
            print(f"  Col {idx}: '{col}'")
            
        print(f"\nTotal rows loaded: {len(rows)}")
        
        # In ra 10 dòng đầu tiên để xem dữ liệu mẫu
        print("\nSample rows:")
        for i, row in enumerate(rows[1:11]):
            print(f"  Row {i+2}: {row[:15]}")
            
        # Thống kê giá trị trong từng cột tiềm năng (từ cột 8 trở đi)
        print("\nAnalyzing status columns...")
        for col_idx in range(8, min(len(header), 20)):
            col_values = [r[col_idx] for r in rows[1:] if len(r) > col_idx]
            counter = Counter(col_values)
            print(f"Col {col_idx} ({header[col_idx] if col_idx < len(header) else 'Unknown'}):")
            for val, count in counter.most_common(15):
                print(f"  - '{val}': {count}")
                
        # Thử tính toán Đặt lịch và Đến cửa dựa trên phán đoán các cột trạng thái
        # Chúng ta sẽ quét qua các cột xem có cột nào chứa Booking hay Arrival
        # Hoặc đếm theo các điều kiện cụ thể.
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
