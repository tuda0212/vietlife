import sys
import os
import logging

logging.basicConfig(level=logging.INFO)
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sheets_reader import _get_sheets_service

SPREADSHEETS = {
    "TTCS_2026": "1r4OsKbVzleV_eYGYEoAZxD1SEIezM6X289xP4ru1TK0",
    "TTCS_2025": "1DnsGIOTl23R3oRBbi1SuE-Sxh5cChxGKCR-kWLrBFVo",
    "TTTK_2025": "1JTwnQx1NzB2QJJ-njI3GY8gksPoYX4kFOGsadsEvVww",
    "TTTK_2026": "1byrhdkbpzxhg8dRKM1of7FurdogMdvQ-F5FpISUSM9E",
    "TTCXK_2025": "1iGs3bBIDdvf3TUiOxrkWNddwZuR63391hfnF8-OC20s",
    "TTCXK_2026": "1670sIuSotKrIH0sEb_sabGR3SlhwCm8QdK2f_mNPUwU"
}

def inspect():
    service = _get_sheets_service()
    sheet_api = service.spreadsheets()
    
    for name, sheet_id in SPREADSHEETS.items():
        print(f"\n==================================================")
        print(f"Inspecting {name} ({sheet_id})")
        try:
            meta = sheet_api.get(spreadsheetId=sheet_id).execute()
            print(f"Spreadsheet Title: {meta['properties']['title']}")
            for s in meta['sheets']:
                title = s['properties']['title']
                grid = s['properties']['gridProperties']
                print(f"  - Tab: '{title}' (rows={grid.get('rowCount')}, cols={grid.get('columnCount')})")
                
                # Fetch first row (headers)
                try:
                    result = sheet_api.values().get(
                        spreadsheetId=sheet_id,
                        range=f"'{title}'!A1:Z2",
                        valueRenderOption="FORMATTED_VALUE"
                    ).execute()
                    vals = result.get("values", [])
                    if vals:
                        print(f"    Header: {vals[0]}")
                        if len(vals) > 1:
                            print(f"    Sample Row: {vals[1]}")
                except Exception as e_sheet:
                    print(f"    Error reading headers: {e_sheet}")
        except Exception as e:
            print(f"Error inspecting {name}: {e}")

if __name__ == "__main__":
    inspect()
