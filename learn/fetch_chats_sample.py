#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Pancake Chat Data Extractor Sample Script
Script này minh họa cách kết nối với Pancake Chat API để lấy các cuộc hội thoại
và lịch sử tin nhắn chi tiết của khách hàng, sau đó xuất ra file JSON phục vụ phân tích.
"""

import os
import sys
import time
import json
import requests
from datetime import datetime

# Cấu hình mã hóa UTF-8 cho console trên Windows
if sys.platform.startswith('win'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except AttributeError:
        pass # Python cũ hơn 3.7

# Cấu hình API Pancake
# Khuyến nghị: Lưu các thông tin này vào file .env
PANCAKE_API_BASE = "https://pages.fm/api/public_api/v1"
PAGE_ID = os.getenv("PANCAKE_PAGE_ID", "YOUR_PAGE_ID_HERE")
PAGE_ACCESS_TOKEN = os.getenv("PANCAKE_PAGE_ACCESS_TOKEN", "YOUR_PAGE_ACCESS_TOKEN_HERE")


def fetch_conversations(limit=20, page=1, type_filter="inbox", since=None, until=None):
    """
    Lấy danh sách các cuộc hội thoại từ Pancake API
    """
    now = int(time.time())
    if since is None:
        # Mặc định lấy các cuộc trò chuyện từ 30 ngày trước
        since = now - (30 * 24 * 60 * 60)
    if until is None:
        # Mặc định lấy đến thời điểm hiện tại
        until = now

    url = f"{PANCAKE_API_BASE}/pages/{PAGE_ID}/conversations"
    params = {
        "page_access_token": PAGE_ACCESS_TOKEN,
        "limit": limit,
        "page": page,
        "page_number": page,
        "type": type_filter,
        "since": since,
        "until": until
    }
    
    print(f"[*] Đang lấy danh sách hội thoại: Trang {page}, Giới hạn {limit}...")
    try:
        response = requests.get(url, params=params, timeout=15)
        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                return data.get("conversations", [])
            else:
                print(f"[!] API báo lỗi: {data.get('message', 'Không rõ nguyên nhân')}")
        elif response.status_code == 429:
            print("[!] Bị giới hạn tần suất gọi API (Rate Limit). Đang đợi 60s...")
            time.sleep(60)
            return fetch_conversations(limit, page, type_filter)
        else:
            print(f"[!] HTTP Error: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"[!] Đã xảy ra lỗi khi gọi API: {str(e)}")
    return []


def fetch_messages(conversation_id, limit=50):
    """
    Lấy lịch sử tin nhắn của một cuộc hội thoại cụ thể
    """
    url = f"{PANCAKE_API_BASE}/pages/{PAGE_ID}/conversations/{conversation_id}/messages"
    params = {
        "page_access_token": PAGE_ACCESS_TOKEN,
        "limit": limit
    }
    
    # print(f"[*] Đang lấy tin nhắn cho cuộc hội thoại {conversation_id}...")
    try:
        response = requests.get(url, params=params, timeout=15)
        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                return data.get("messages", [])
        elif response.status_code == 429:
            print("[!] Rate Limit khi lấy tin nhắn. Đang đợi 30s...")
            time.sleep(30)
            return fetch_messages(conversation_id, limit)
    except Exception as e:
        print(f"[!] Lỗi khi lấy tin nhắn của {conversation_id}: {str(e)}")
    return []


def main():
    # Kiểm tra cấu hình mẫu
    if PAGE_ID == "YOUR_PAGE_ID_HERE" or PAGE_ACCESS_TOKEN == "YOUR_PAGE_ACCESS_TOKEN_HERE":
        print("[!] Vui lòng thiết lập biến môi trường hoặc chỉnh sửa PAGE_ID và PAGE_ACCESS_TOKEN trong code.")
        # Ví dụ giả lập để người dùng thấy cấu trúc khi chạy test
        print("[*] Chạy chế độ giả lập xuất file cấu trúc mẫu...")
        save_dummy_data()
        return

    all_chat_data = []
    
    # Bước 1: Lấy danh sách hội thoại gần đây (Ví dụ: Trang 1, 10 cuộc hội thoại)
    conversations = fetch_conversations(limit=10, page=1)
    
    if not conversations:
        print("[!] Không tìm thấy cuộc hội thoại nào hoặc lỗi kết nối.")
        return

    print(f"[+] Đã tìm thấy {len(conversations)} cuộc hội thoại. Bắt đầu lấy lịch sử tin nhắn...")

    # Bước 2: Với mỗi cuộc hội thoại, lấy lịch sử tin nhắn chi tiết
    for index, conv in enumerate(conversations):
        conv_id = conv.get("id")
        customer_name = conv.get("customer", {}).get("name", "Ẩn danh")
        print(f"[{index+1}/{len(conversations)}] Lấy tin nhắn của khách hàng: {customer_name} (ID: {conv_id})")
        
        # Gọi API lấy tin nhắn
        messages = fetch_messages(conv_id, limit=50)
        
        # Chuẩn hóa dữ liệu hội thoại để lưu trữ
        chat_entry = {
            "conversation_id": conv_id,
            "customer_name": customer_name,
            "customer_id": conv.get("customer", {}).get("id") if conv.get("customer") else None,
            "tags": [t.get("name") for t in (conv.get("tags") or []) if t and isinstance(t, dict)],
            "updated_at": conv.get("updated_at"),
            "messages": []
        }
        
        # Đảo ngược danh sách tin nhắn để hiển thị theo trình tự thời gian từ cũ đến mới
        for msg in reversed(messages):
            chat_entry["messages"].append({
                "message_id": msg.get("id"),
                "sender": msg.get("from", {}).get("name", "Khách hàng"),
                "sender_id": msg.get("from", {}).get("id"),
                "content": msg.get("message"),
                "created_at": msg.get("created_at")
            })
            
        all_chat_data.append(chat_entry)
        
        # Sleep ngắn để tránh spam Rate Limit của API
        time.sleep(0.5)

    # Bước 3: Xuất dữ liệu ra file JSON
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_filename = f"pancake_chats_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    output_path = os.path.join(script_dir, output_filename)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(all_chat_data, f, ensure_ascii=False, indent=2)
        
    print(f"\n[+] Xuất dữ liệu thành công ra file: {output_path}")
    print(f"[*] Dữ liệu này đã sẵn sàng để gửi vào mô hình AI để phân tích chân dung & tối ưu kịch bản.")


def save_dummy_data():
    """Tạo file dữ liệu giả lập mẫu cấu trúc để làm ví dụ phân tích"""
    dummy_data = [
      {
        "conversation_id": "t.100063.98765",
        "customer_name": "Nguyễn Thị Mai",
        "customer_id": "98765",
        "tags": ["Khách Quan Tâm", "Cần Gọi Lại"],
        "updated_at": "2026-06-20T05:00:00Z",
        "messages": [
          {"sender": "Nguyễn Thị Mai", "content": "Dạ em chào anh/chị, em đang tìm hiểu về gói khám sức khỏe tổng quát cho mẹ em ạ.", "created_at": "2026-06-20T04:50:00Z"},
          {"sender": "Vietlife Clinic (Page)", "content": "Chào bạn Mai, Vietlife rất vui được tư vấn cho bạn. Mẹ bạn năm nay bao nhiêu tuổi và có đang gặp triệu chứng gì bất thường không ạ?", "created_at": "2026-06-20T04:52:00Z"},
          {"sender": "Nguyễn Thị Mai", "content": "Mẹ em năm nay 58 tuổi, dạo này hay kêu mệt, đau đầu với mất ngủ ạ. Không biết nên khám gói nào?", "created_at": "2026-06-20T04:53:00Z"},
          {"sender": "Vietlife Clinic (Page)", "content": "Dạ với độ tuổi của bác và các dấu hiệu đau đầu, mất ngủ, Vietlife có gói khám Sức Khỏe Toàn Diện kèm tầm soát Tai Biến - Đột Quỵ rất phù hợp ạ. Gói này đang ưu đãi giảm 15% còn 3.500.000đ.", "created_at": "2026-06-20T04:55:00Z"},
          {"sender": "Nguyễn Thị Mai", "content": "Giá 3.500.000đ là trọn gói chưa ạ? Có phát sinh thêm phí xét nghiệm gì không? Để em hỏi lại mẹ xem sao nhé.", "created_at": "2026-06-20T04:57:00Z"},
          {"sender": "Vietlife Clinic (Page)", "content": "Dạ giá trên đã bao gồm toàn bộ danh mục khám lâm sàng, siêu âm, chụp MRI não mạch máu và xét nghiệm máu cơ bản rồi ạ. Bạn cứ trao đổi với bác rồi báo lại bên mình xếp lịch khám nhé!", "created_at": "2026-06-20T04:59:00Z"}
        ]
      }
    ]
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_path = os.path.join(script_dir, "pancake_chats_dummy.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(dummy_data, f, ensure_ascii=False, indent=2)
    print(f"[+] Đã tạo file giả lập mẫu: {output_path}")


if __name__ == "__main__":
    main()
