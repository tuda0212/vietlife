import os
import sys
import logging
from pathlib import Path
from google.cloud import bigquery

# Load env variables
workspace_root = Path(__file__).resolve().parent.parent
env_file = workspace_root / ".env"
if env_file.exists():
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                os.environ.setdefault(key.strip(), value.strip())

# Add files to path
workspace_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
files_dir = os.path.join(workspace_dir, "files")
sys.path.append(files_dir)

from sheets_reader import _get_sheets_service

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s"
)
logger = logging.getLogger("update_chung_ads_sheet")

def main():
    project_id = "gen-lang-client-0738410622"
    dataset_id = "marketing_data"
    spreadsheet_id = "10sWUCv1uYk5X2CKfcwOqbd5K3JXjPmty00yb9IJkK0c"
    target_gid = 667764405
    
    # 1. Truy vấn BigQuery lấy các ad của bác sĩ Chung
    logger.info("Đang truy vấn BigQuery để lấy danh sách bài quảng cáo của BS Chung...")
    bq_client = bigquery.Client(project=project_id)
    
    # Query gom nhóm theo post_link để loại bỏ trùng lặp
    query = f"""
        SELECT 
          post_link,
          ANY_VALUE(thumbnail_url) as thumbnail_url,
          ANY_VALUE(content) as content,
          MAX(spend) as max_spend
        FROM `{project_id}.{dataset_id}.fb_ad_insights`
        WHERE (
          LOWER(doctor_name) LIKE '%chung%' 
          OR LOWER(campaign_name) LIKE '%chung%'
        )
        AND post_link IS NOT NULL 
        AND post_link != ''
        GROUP BY post_link
        ORDER BY max_spend DESC
    """
    
    query_job = bq_client.query(query)
    results = list(query_job.result())
    logger.info(f"Tìm thấy {len(results)} bài quảng cáo độc nhất.")
    
    if not results:
        logger.warning("Không tìm thấy bài quảng cáo nào. Kết thúc.")
        return
        
    # 2. Kết nối tới Google Sheets
    logger.info("Đang kết nối tới Google Sheets API...")
    service = _get_sheets_service()
    sheet_api = service.spreadsheets()
    
    # Lấy tiêu đề của sheet theo GID
    meta = sheet_api.get(spreadsheetId=spreadsheet_id).execute()
    sheet_title = None
    for sheet in meta.get("sheets", []):
        props = sheet.get("properties", {})
        if props.get("sheetId") == target_gid:
            sheet_title = props.get("title")
            break
            
    if not sheet_title:
        logger.error(f"Không tìm thấy sheet với GID: {target_gid}")
        return
    logger.info(f"Cập nhật vào tab: '{sheet_title}' (GID: {target_gid})")
    
    # 3. Chuẩn bị dữ liệu ghi vào sheet
    rows_to_write = []
    # Header row
    rows_to_write.append(["Thumbnail", "Content", "Link bài viết"])
    
    for row in results:
        thumb_formula = f'=IMAGE("{row.thumbnail_url}")' if row.thumbnail_url else ""
        content = row.content or ""
        rows_to_write.append([thumb_formula, content, row.post_link])
        
    total_rows = len(rows_to_write)
    logger.info(f"Chuẩn bị ghi {total_rows} hàng dữ liệu (bao gồm cả header)...")
    
    # Xoá dữ liệu cũ trước khi ghi mới
    logger.info("Xoá dữ liệu cũ trên sheet...")
    sheet_api.values().clear(
        spreadsheetId=spreadsheet_id,
        range=f"'{sheet_title}'!A1:Z1000"
    ).execute()
    
    # Ghi dữ liệu mới
    body = {
        'values': rows_to_write
    }
    logger.info("Ghi dữ liệu mới vào sheet...")
    sheet_api.values().update(
        spreadsheetId=spreadsheet_id,
        range=f"'{sheet_title}'!A1",
        valueInputOption='USER_ENTERED',
        body=body
    ).execute()
    logger.info("Ghi dữ liệu thành công!")
    
    # 4. Định dạng thẩm mỹ cho sheet
    logger.info("Bắt đầu định dạng thẩm mỹ cho Google Sheet...")
    
    requests = [
        # 1. Đặt chiều rộng cột A (Thumbnail) là 120 pixels
        {
            "updateDimensionProperties": {
                "range": {
                    "sheetId": target_gid,
                    "dimension": "COLUMNS",
                    "startIndex": 0,
                    "endIndex": 1
                },
                "properties": {
                    "pixelSize": 120
                },
                "fields": "pixelSize"
            }
        },
        # 2. Đặt chiều cao hàng cho tất cả các hàng dữ liệu (từ hàng 2 trở đi, index 1 đến N) là 90 pixels
        {
            "updateDimensionProperties": {
                "range": {
                    "sheetId": target_gid,
                    "dimension": "ROWS",
                    "startIndex": 1,
                    "endIndex": total_rows
                },
                "properties": {
                    "pixelSize": 90
                },
                "fields": "pixelSize"
            }
        },
        # 3. Căn giữa theo chiều dọc (vertical alignment) cho tất cả các ô trong bảng
        {
            "repeatCell": {
                "range": {
                    "sheetId": target_gid,
                    "startRowIndex": 0,
                    "endRowIndex": total_rows,
                    "startColumnIndex": 0,
                    "endColumnIndex": 3
                },
                "cell": {
                    "userEnteredFormat": {
                        "verticalAlignment": "MIDDLE",
                    }
                },
                "fields": "userEnteredFormat.verticalAlignment"
            }
        },
        # 4. Định dạng wrap text (xuống dòng) cho cột Content (cột B, index 1)
        {
            "repeatCell": {
                "range": {
                    "sheetId": target_gid,
                    "startRowIndex": 1,
                    "endRowIndex": total_rows,
                    "startColumnIndex": 1,
                    "endColumnIndex": 2
                },
                "cell": {
                    "userEnteredFormat": {
                        "wrapStrategy": "WRAP"
                    }
                },
                "fields": "userEnteredFormat.wrapStrategy"
            }
        },
        # 5. Căn giữa theo chiều ngang (horizontal alignment = CENTER) cho cột Thumbnail và Link bài viết
        {
            "repeatCell": {
                "range": {
                    "sheetId": target_gid,
                    "startRowIndex": 0,
                    "endRowIndex": total_rows,
                    "startColumnIndex": 0,
                    "endColumnIndex": 1
                },
                "cell": {
                    "userEnteredFormat": {
                        "horizontalAlignment": "CENTER"
                    }
                },
                "fields": "userEnteredFormat.horizontalAlignment"
            }
        },
        {
            "repeatCell": {
                "range": {
                    "sheetId": target_gid,
                    "startRowIndex": 0,
                    "endRowIndex": total_rows,
                    "startColumnIndex": 2,
                    "endColumnIndex": 3
                },
                "cell": {
                    "userEnteredFormat": {
                        "horizontalAlignment": "CENTER"
                    }
                },
                "fields": "userEnteredFormat.horizontalAlignment"
            }
        },
        # 6. Định dạng in đậm (bold) và nền xanh nhạt cho Header row
        {
            "repeatCell": {
                "range": {
                    "sheetId": target_gid,
                    "startRowIndex": 0,
                    "endRowIndex": 1,
                    "startColumnIndex": 0,
                    "endColumnIndex": 3
                },
                "cell": {
                    "userEnteredFormat": {
                        "textFormat": {
                            "bold": True,
                            "fontSize": 11
                        },
                        "backgroundColor": {
                            "red": 0.85,
                            "green": 0.92,
                            "blue": 1.0
                        }
                    }
                },
                "fields": "userEnteredFormat.textFormat,userEnteredFormat.backgroundColor"
            }
        }
    ]
    
    sheet_api.batchUpdate(
        spreadsheetId=spreadsheet_id,
        body={'requests': requests}
    ).execute()
    logger.info("Định dạng sheet hoàn tất thành công!")

if __name__ == "__main__":
    main()
