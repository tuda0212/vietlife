#!/usr/bin/env python3
"""
fb_creation_helper.py
Helper script hỗ trợ tạo Campaign, Ad Set, Ad Creative và Ad trên Facebook Marketing API.
Sử dụng thư viện 'requests' để tránh các dependency phức tạp.
"""

import os
import logging
import json
import requests
from pathlib import Path

# Cấu hình logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s"
)
logger = logging.getLogger("fb_creation_helper")

# Tự động load file .env từ thư mục gốc của repo
def load_env():
    # Tìm gốc repo (cha của cha của cha của thư mục chứa script này: .agents/skills/facebook-ads-campaign/scripts/)
    script_dir = Path(__file__).resolve().parent
    workspace_root = script_dir.parent.parent.parent.parent
    env_file = workspace_root / ".env"
    
    if env_file.exists():
        logger.info(f"Đang tải biến môi trường từ {env_file}...")
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, _, value = line.partition("=")
                    os.environ.setdefault(key.strip(), value.strip())
    else:
        logger.warning(f"Không tìm thấy file .env tại {workspace_root}. Sử dụng biến môi trường hiện tại.")

# Tải biến môi trường
load_env()

FB_ACCESS_TOKEN = os.environ.get("FB_ACCESS_TOKEN")
FB_API_VERSION = "v20.0"
FB_API_BASE = f"https://graph.facebook.com/{FB_API_VERSION}"

def _get_headers():
    return {
        "Authorization": f"Bearer {FB_ACCESS_TOKEN}"
    }

def check_auth():
    """Kiểm tra token Facebook Ads."""
    if not FB_ACCESS_TOKEN or FB_ACCESS_TOKEN.startswith("your_"):
        raise EnvironmentError(
            "❌ Thiếu FB_ACCESS_TOKEN hợp lệ trong biến môi trường hoặc file .env!"
        )

# =============================================================================
# 1. TẠO CAMPAIGN
# =============================================================================
def create_campaign(ad_account_id: str, name: str, objective: str = "OUTCOME_LEADS", status: str = "PAUSED") -> str:
    """
    Tạo một chiến dịch quảng cáo Facebook (Campaign).
    Mục tiêu mặc định: OUTCOME_LEADS (Có thể thay đổi thành OUTCOME_TRAFFIC, OUTCOME_ENGAGEMENT, v.v.)
    """
    check_auth()
    
    # Chuẩn hóa ad_account_id (phải bắt đầu bằng act_)
    account_id = ad_account_id.strip()
    if not account_id.startswith("act_"):
        account_id = f"act_{account_id}"
        
    url = f"{FB_API_BASE}/{account_id}/campaigns"
    
    payload = {
        "name": name,
        "objective": objective,
        "status": status,
        "special_ad_categories": "[]" # Mặc định trống cho quảng cáo thông thường
    }
    
    logger.info(f"Đang tạo Campaign '{name}' với mục tiêu {objective}...")
    resp = requests.post(url, headers=_get_headers(), data=payload, timeout=30)
    
    try:
        data = resp.json()
    except Exception:
        raise RuntimeError(f"Lỗi phản hồi từ Facebook: {resp.text}")
        
    if "error" in data:
        raise RuntimeError(f"Lỗi Facebook API khi tạo Campaign: {data['error']['message']} (Code: {data['error'].get('code')})")
        
    campaign_id = data["id"]
    logger.info(f"Tạo Campaign thành công! ID: {campaign_id}")
    return campaign_id


# =============================================================================
# 2. TẠO AD SET
# =============================================================================
def create_ad_set(
    ad_account_id: str, 
    campaign_id: str, 
    name: str, 
    daily_budget: int = 100000, 
    targeting: dict = None,
    billing_event: str = "IMPRESSIONS",
    optimization_goal: str = "LEADS",
    status: str = "PAUSED"
) -> str:
    """
    Tạo một nhóm quảng cáo (Ad Set).
    daily_budget: Ngân sách hàng ngày (được tính bằng đơn vị tiền tệ nhỏ nhất, ví dụ VND thì 100k là 100000)
    targeting: Dictionary chứa thông tin nhắm đối tượng. Mặc định nhắm mục tiêu Việt Nam.
    """
    check_auth()
    
    account_id = ad_account_id.strip()
    if not account_id.startswith("act_"):
        account_id = f"act_{account_id}"
        
    url = f"{FB_API_BASE}/{account_id}/adsets"
    
    # Mặc định nhắm mục tiêu toàn Việt Nam nếu không truyền targeting cụ thể
    if not targeting:
        targeting = {
            "geo_locations": {
                "countries": ["VN"]
            }
        }
        
    payload = {
        "name": name,
        "campaign_id": campaign_id,
        "daily_budget": daily_budget,
        "billing_event": billing_event,
        "optimization_goal": optimization_goal,
        "bid_strategy": "LOWEST_COST_WITHOUT_CAP",
        "targeting": json.dumps(targeting),
        "status": status
    }
    
    logger.info(f"Đang tạo Ad Set '{name}' cho Campaign ID {campaign_id}...")
    resp = requests.post(url, headers=_get_headers(), data=payload, timeout=30)
    
    try:
        data = resp.json()
    except Exception:
        raise RuntimeError(f"Lỗi phản hồi từ Facebook: {resp.text}")
        
    if "error" in data:
        raise RuntimeError(f"Lỗi Facebook API khi tạo Ad Set: {data['error']['message']} (Code: {data['error'].get('code')})")
        
    adset_id = data["id"]
    logger.info(f"Tạo Ad Set thành công! ID: {adset_id}")
    return adset_id


# =============================================================================
# 3. TẠO AD CREATIVE (MẪU QUẢNG CÁO)
# =============================================================================
def create_ad_creative_post(ad_account_id: str, name: str, page_id: str, post_id: str) -> str:
    """
    Tạo một Ad Creative dựa trên bài viết có sẵn trên Page (Page Post).
    """
    check_auth()
    
    account_id = ad_account_id.strip()
    if not account_id.startswith("act_"):
        account_id = f"act_{account_id}"
        
    url = f"{FB_API_BASE}/{account_id}/adcreatives"
    
    payload = {
        "name": name,
        "object_story_id": f"{page_id}_{post_id}"
    }
    
    logger.info(f"Đang tạo Ad Creative '{name}' từ bài viết {page_id}_{post_id}...")
    resp = requests.post(url, headers=_get_headers(), data=payload, timeout=30)
    
    try:
        data = resp.json()
    except Exception:
        raise RuntimeError(f"Lỗi phản hồi từ Facebook: {resp.text}")
        
    if "error" in data:
        raise RuntimeError(f"Lỗi Facebook API khi tạo Ad Creative: {data['error']['message']} (Code: {data['error'].get('code')})")
        
    creative_id = data["id"]
    logger.info(f"Tạo Ad Creative thành công! ID: {creative_id}")
    return creative_id


def create_ad_creative_link(
    ad_account_id: str, 
    name: str, 
    page_id: str, 
    message: str, 
    link: str, 
    image_hash: str = None,
    call_to_action_type: str = "LEARN_MORE"
) -> str:
    """
    Tạo một Ad Creative mới (Link ad) sử dụng ảnh (image_hash) và thông điệp tùy chỉnh.
    """
    check_auth()
    
    account_id = ad_account_id.strip()
    if not account_id.startswith("act_"):
        account_id = f"act_{account_id}"
        
    url = f"{FB_API_BASE}/{account_id}/adcreatives"
    
    link_data = {
        "link": link,
        "message": message,
        "call_to_action": {
            "type": call_to_action_type,
            "value": {
                "link": link
            }
        }
    }
    
    if image_hash:
        link_data["image_hash"] = image_hash
        
    object_story_spec = {
        "page_id": page_id,
        "link_data": link_data
    }
    
    payload = {
        "name": name,
        "object_story_spec": json.dumps(object_story_spec)
    }
    
    logger.info(f"Đang tạo Ad Creative mới '{name}' với liên kết {link}...")
    resp = requests.post(url, headers=_get_headers(), data=payload, timeout=30)
    
    try:
        data = resp.json()
    except Exception:
        raise RuntimeError(f"Lỗi phản hồi từ Facebook: {resp.text}")
        
    if "error" in data:
        raise RuntimeError(f"Lỗi Facebook API khi tạo Ad Creative: {data['error']['message']} (Code: {data['error'].get('code')})")
        
    creative_id = data["id"]
    logger.info(f"Tạo Ad Creative thành công! ID: {creative_id}")
    return creative_id


# =============================================================================
# 4. TẠO AD (QUẢNG CÁO CHI TIẾT)
# =============================================================================
def create_ad(ad_account_id: str, adset_id: str, creative_id: str, name: str, status: str = "PAUSED") -> str:
    """
    Tạo quảng cáo thực tế (Ad) liên kết Ad Set với Ad Creative.
    """
    check_auth()
    
    account_id = ad_account_id.strip()
    if not account_id.startswith("act_"):
        account_id = f"act_{account_id}"
        
    url = f"{FB_API_BASE}/{account_id}/ads"
    
    payload = {
        "name": name,
        "adset_id": adset_id,
        "creative": json.dumps({"creative_id": creative_id}),
        "status": status
    }
    
    logger.info(f"Đang tạo Ad '{name}' bằng AdSet {adset_id} và Creative {creative_id}...")
    resp = requests.post(url, headers=_get_headers(), data=payload, timeout=30)
    
    try:
        data = resp.json()
    except Exception:
        raise RuntimeError(f"Lỗi phản hồi từ Facebook: {resp.text}")
        
    if "error" in data:
        raise RuntimeError(f"Lỗi Facebook API khi tạo Ad: {data['error']['message']} (Code: {data['error'].get('code')})")
        
    ad_id = data["id"]
    logger.info(f"Tạo Ad thành công! ID: {ad_id}")
    return ad_id


# =============================================================================
# PIPELINE: CHẠY TOÀN BỘ QUY TRÌNH
# =============================================================================
def launch_full_campaign(
    ad_account_id: str,
    page_id: str,
    campaign_name: str,
    adset_name: str,
    creative_name: str,
    ad_name: str,
    daily_budget: int = 100000,
    post_id: str = None, # Nếu dùng bài viết sẵn
    # Nếu tạo mẫu ad mới:
    ad_message: str = None,
    ad_link: str = None,
    ad_image_hash: str = None
) -> dict:
    """
    Chạy tự động cả 4 bước để lên một chiến dịch quảng cáo hoàn chỉnh.
    """
    check_auth()
    logger.info("⚡⚡ BẮT ĐẦU QUY TRÌNH LÊN QUẢNG CÁO FACEBOOK TỰ ĐỘNG ⚡⚡")
    
    results = {}
    
    try:
        # Bước 1: Campaign
        campaign_id = create_campaign(ad_account_id, campaign_name)
        results["campaign_id"] = campaign_id
        
        # Bước 2: Ad Set
        adset_id = create_ad_set(ad_account_id, campaign_id, adset_name, daily_budget=daily_budget)
        results["adset_id"] = adset_id
        
        # Bước 3: Ad Creative
        if post_id:
            creative_id = create_ad_creative_post(ad_account_id, creative_name, page_id, post_id)
        else:
            if not ad_message or not ad_link:
                raise ValueError("Cần cung cấp ad_message và ad_link nếu không sử dụng post_id!")
            creative_id = create_ad_creative_link(
                ad_account_id, creative_name, page_id, ad_message, ad_link, image_hash=ad_image_hash
            )
        results["creative_id"] = creative_id
        
        # Bước 4: Ad
        ad_id = create_ad(ad_account_id, adset_id, creative_id, ad_name)
        results["ad_id"] = ad_id
        
        logger.info("🎉🎉 QUY TRÌNH TẠO QUẢNG CÁO HOÀN TẤT THÀNH CÔNG! 🎉🎉")
        logger.info(f"Kết quả ID: {results}")
        return results
        
    except Exception as e:
        logger.error(f"❌ Quy trình lên quảng cáo thất bại tại bước trước đó: {e}")
        raise
