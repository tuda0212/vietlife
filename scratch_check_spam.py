import datetime
from google.auth import default as google_auth_default
from googleapiclient.discovery import build

def main():
    try:
        print("Đang xác thực bằng Application Default Credentials (ADC)...")
        # Sử dụng scope modify để có thể chỉnh sửa nhãn nếu cần, hoặc readonly
        scopes = [
            "https://www.googleapis.com/auth/gmail.readonly",
            "https://www.googleapis.com/auth/gmail.modify"
        ]
        credentials, project = google_auth_default(scopes=scopes)
        
        print("Đang kết nối tới Gmail API...")
        service = build("gmail", "v1", credentials=credentials, cache_discovery=False)
        
        # Truy vấn tìm thư rác (in:spam hoặc is:spam hoặc label:SPAM) trong 7 ngày qua
        # Google Trends Tracker chạy local time là 2026-06-16
        # Newer than 7 days
        query = "in:spam newer_than:7d"
        print(f"Đang tìm kiếm thư rác với truy vấn: '{query}'...")
        
        result = service.users().messages().list(userId="me", q=query).execute()
        messages = result.get("messages", [])
        
        print(f"Tìm thấy {len(messages)} thư rác trong 7 ngày gần nhất.")
        
        if not messages:
            print("Không có thư rác nào trong 7 ngày qua.")
            return
            
        # Liệt kê thông tin chi tiết một vài thư rác (tối đa 10 thư)
        print("\nDanh sách thư rác:")
        print("-" * 80)
        for msg in messages[:10]:
            msg_id = msg["id"]
            detail = service.users().messages().get(userId="me", id=msg_id, format="metadata", metadataHeaders=["From", "Subject", "Date"]).execute()
            
            headers = detail.get("payload", {}).get("headers", [])
            sender = "Unknown"
            subject = "No Subject"
            date = "Unknown"
            
            for h in headers:
                if h["name"] == "From":
                    sender = h["value"]
                elif h["name"] == "Subject":
                    subject = h["value"]
                elif h["name"] == "Date":
                    date = h["value"]
            
            print(f"ID: {msg_id}")
            print(f"Người gửi: {sender}")
            print(f"Tiêu đề: {subject}")
            print(f"Ngày: {date}")
            print("-" * 80)
            
    except Exception as e:
        print(f"Lỗi: {e}")

if __name__ == "__main__":
    main()
