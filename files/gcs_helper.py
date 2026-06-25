import logging
import requests
import io
from concurrent.futures import ThreadPoolExecutor, as_completed
from google.cloud import storage

logger = logging.getLogger(__name__)

def upload_single_thumbnail(storage_client, bucket_name, ad_id, fb_url) -> str:
    """
    Xử lý tải và upload một hình ảnh lên GCS.
    Nếu file đã tồn tại trên GCS, trả về luôn link GCS.
    Nếu tải lỗi hoặc upload lỗi, trả về link gốc fb_url làm fallback.
    """
    if not fb_url:
        return ""
        
    destination_blob_name = f"thumbnails/{ad_id}.jpg"
    gcs_url = f"https://storage.googleapis.com/{bucket_name}/{destination_blob_name}"
    
    try:
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(destination_blob_name)
        
        # Kiểm tra xem ảnh đã tồn tại chưa để tiết kiệm băng thông
        try:
            if blob.exists():
                return gcs_url
        except Exception as exists_err:
            logger.warning(f"Không thể kiểm tra tồn tại của blob {destination_blob_name} (chưa cấu hình permissions hoặc chưa có bucket?): {exists_err}")
            
        # Tải ảnh từ Facebook CDN
        resp = requests.get(fb_url, timeout=15)
        if resp.status_code != 200:
            logger.warning(f"Không thể tải ảnh từ Facebook cho ad {ad_id}: {resp.status_code}")
            return fb_url
            
        # Upload lên GCS
        # Thiết lập content_type là image/jpeg để hiển thị trực tiếp thay vì tải về
        blob.upload_from_string(
            resp.content,
            content_type="image/jpeg"
        )
        
        # Cấp quyền đọc công khai (nếu bucket không cấu hình allUsers mặc định)
        try:
            blob.make_public()
        except Exception:
            pass # Bỏ qua nếu bucket đã được thiết lập IAM allUsers tập trung
            
        logger.info(f"Đã upload thành công thumbnail cho ad {ad_id} lên GCS.")
        return gcs_url
        
    except Exception as e:
        logger.error(f"Lỗi khi xử lý thumbnail cho ad {ad_id}: {e}")
        return fb_url # Fallback về link gốc nếu gặp bất kỳ lỗi gì

def upload_thumbnails_to_gcs_batch(ad_details: dict, bucket_name: str, max_workers: int = 10) -> dict:
    """
    Đầu vào: ad_details là dictionary dạng { ad_id: { "creative": { "thumbnail_url": ... }, "status": ... } }
    Đầu ra: Trả về một dict map { ad_id: gcs_url_hoac_fb_url }
    """
    if not ad_details or not bucket_name:
        return {}
        
    try:
        storage_client = storage.Client()
    except Exception as init_err:
        logger.error(f"Không khởi tạo được GCS Client: {init_err}")
        return {}
        
    ad_gcs_urls = {}
    
    # Chuẩn bị danh sách các ad cần upload
    tasks = []
    for ad_id, details in ad_details.items():
        creative = details.get("creative") or {}
        # Lấy link thumbnail gốc của Facebook
        fb_url = creative.get("thumbnail_url") or creative.get("image_url") or ""
        if fb_url:
            tasks.append((ad_id, fb_url))
            
    if not tasks:
        return {}
        
    logger.info(f"[GCS Helper] Bắt đầu xử lý {len(tasks)} thumbnails song song (luồng: {max_workers})")
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_ad = {
            executor.submit(upload_single_thumbnail, storage_client, bucket_name, ad_id, fb_url): ad_id
            for ad_id, fb_url in tasks
        }
        
        for future in as_completed(future_to_ad):
            ad_id = future_to_ad[future]
            try:
                gcs_url = future.result()
                if gcs_url:
                    ad_gcs_urls[ad_id] = gcs_url
            except Exception as e:
                logger.error(f"Lỗi thread xử lý ảnh ad {ad_id}: {e}")
                
    return ad_gcs_urls
