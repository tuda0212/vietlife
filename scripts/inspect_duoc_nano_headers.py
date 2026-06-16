import subprocess
import urllib.request
import json

def get_token():
    res = subprocess.run(["gcloud", "auth", "print-access-token"], capture_output=True, text=True)
    return res.stdout.strip()

def inspect_headers():
    token = get_token()
    spreadsheet_id = "1Y99VmZqvXEsBY8zII3bcY-qIYDNPuATpXWC01hwrzVI"
    
    # First get spreadsheet info to find the first sheet name
    url_meta = f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}"
    req_meta = urllib.request.Request(url_meta, headers={"Authorization": f"Bearer {token}"})
    try:
        with urllib.request.urlopen(req_meta) as response:
            meta = json.loads(response.read().decode())
    except Exception as e:
        print(f"Error getting metadata: {e}")
        return
        
    first_sheet = meta["sheets"][0]["properties"]["title"]
    print(f"Tab name: {first_sheet}")
    
    # Get values A1:AH2
    range_notation = urllib.parse.quote(f"'{first_sheet}'!A1:AH2")
    url_values = f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}/values/{range_notation}?valueRenderOption=UNFORMATTED_VALUE"
    req_values = urllib.request.Request(url_values, headers={"Authorization": f"Bearer {token}"})
    try:
        with urllib.request.urlopen(req_values) as response:
            values_data = json.loads(response.read().decode())
            values = values_data.get("values", [])
            if len(values) >= 1:
                headers = values[0]
                for idx, h in enumerate(headers):
                    print(f"Col {idx} (Letter {chr(65+idx) if idx < 26 else 'A' + chr(65+idx-26)}): {h}")
            else:
                print("No values found")
    except Exception as e:
        print(f"Error getting values: {e}")

if __name__ == "__main__":
    inspect_headers()
