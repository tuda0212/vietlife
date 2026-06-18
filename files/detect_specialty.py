import os
import requests
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config import FB_ACCESS_TOKEN, FB_API_BASE

def detect_account_specialty(account_id):
    print(f"\nDetecting specialty for account: {account_id}")
    url = f"{FB_API_BASE}/{account_id}/campaigns"
    params = {
        "fields": "name",
        "limit": 20,
        "access_token": FB_ACCESS_TOKEN
    }
    try:
        resp = requests.get(url, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        campaigns = data.get("data", [])
        if not campaigns:
            print("No campaigns found for this account.")
            return None
            
        print(f"Found {len(campaigns)} campaigns:")
        specialty_votes = {}
        for c in campaigns:
            name = c.get("name", "")
            print(f" - Campaign Name: {name}")
            parts = [p.strip() for p in name.split("_") if p.strip()]
            if parts:
                code = parts[0].upper()
                specialty_votes[code] = specialty_votes.get(code, 0) + 1
                
        if specialty_votes:
            # Lấy mã chuyên khoa xuất hiện nhiều nhất
            best_code = max(specialty_votes, key=specialty_votes.get)
            print(f"Detected specialty code: {best_code} (Votes: {specialty_votes})")
            return best_code
        return None
    except Exception as e:
        print(f"Error fetching campaigns for {account_id}: {e}")
        return None

def main():
    accounts = ["act_2031624244397226", "act_1433365117712667"]
    for acc in accounts:
        detect_account_specialty(acc)

if __name__ == "__main__":
    main()
