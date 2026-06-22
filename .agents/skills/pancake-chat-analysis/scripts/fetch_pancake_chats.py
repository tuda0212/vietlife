#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script kết nối Pancake Chat API để tải hội thoại và lịch sử tin nhắn.
Hỗ trợ chạy qua tham số CLI hoặc biến môi trường.
"""

import os
import sys
import time
import json
import argparse
import requests
from datetime import datetime

PANCAKE_API_BASE = "https://pages.fm/api/public_api/v1"

def fetch_conversations(page_id, token, limit=20, page=1, since=None, until=None):
    now = int(time.time())
    if since is None:
        # Mặc định lấy các cuộc trò chuyện từ 30 ngày trước
        since = now - (30 * 24 * 60 * 60)
    if until is None:
        # Mặc định lấy đến thời điểm hiện tại
        until = now

    url = f"{PANCAKE_API_BASE}/pages/{page_id}/conversations"
    params = {
        "page_access_token": token,
        "limit": limit,
        "page": page,
        "page_number": page,
        "type": "inbox",
        "since": since,
        "until": until
    }

    print(f"[*] Đang tải danh sách hội thoại từ Pancake: Trang {page}, Giới hạn {limit}...")
    try:
        response = requests.get(url, params=params, timeout=15)
        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                return data.get("conversations", [])
            else:
                print(f"[!] API trả về lỗi: {data.get('message', 'Không rõ nguyên nhân')}")
        elif response.status_code == 429:
            print("[!] Rate Limit. Đang đợi 60 giây...")
            time.sleep(60)
            return fetch_conversations(page_id, token, limit, page, since, until)
        else:
            print(f"[!] HTTP Error: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"[!] Lỗi kết nối API: {str(e)}")
    return []

def fetch_messages(page_id, conversation_id, token, limit=50):
    url = f"{PANCAKE_API_BASE}/pages/{page_id}/conversations/{conversation_id}/messages"
    params = {
        "page_access_token": token,
        "limit": limit
    }
    try:
        response = requests.get(url, params=params, timeout=15)
        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                return data.get("messages", [])
        elif response.status_code == 429:
            print("[!] Rate Limit khi lấy tin nhắn. Đợi 30s...")
            time.sleep(30)
            return fetch_messages(page_id, conversation_id, token, limit)
    except Exception as e:
        print(f"[!] Lỗi khi lấy tin nhắn: {str(e)}")
    return []

def save_dummy_data(output_path):
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
      },
      {
        "conversation_id": "t.100063.11223",
        "customer_name": "Trần Minh Hoàng",
        "customer_id": "11223",
        "tags": ["Khách Than Đắt", "Chưa Chốt"],
        "updated_at": "2026-06-21T09:15:00Z",
        "messages": [
          {"sender": "Trần Minh Hoàng", "content": "Tư vấn cho mình gói chụp cộng hưởng từ MRI cột sống cổ.", "created_at": "2026-06-21T09:00:00Z"},
          {"sender": "Vietlife Clinic (Page)", "content": "Chào anh Hoàng, chụp cộng hưởng từ MRI cột sống cổ tại Vietlife sử dụng công nghệ từ trường cao 1.5T không tiếng ồn. Giá chụp là 2.200.000đ ạ.", "created_at": "2026-06-21T09:02:00Z"},
          {"sender": "Trần Minh Hoàng", "content": "Sao đắt thế em? Bên phòng khám khác anh hỏi có 1.800.000đ thôi.", "created_at": "2026-06-21T09:05:00Z"},
          {"sender": "Vietlife Clinic (Page)", "content": "Dạ vâng ạ.", "created_at": "2026-06-21T09:10:00Z"}
        ]
      }
    ]
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(dummy_data, f, ensure_ascii=False, indent=2)
    print(f"[+] Đã ghi dữ liệu giả lập vào tệp: {output_path}")

def main():
    parser = argparse.ArgumentParser(description="Tải dữ liệu hội thoại từ Pancake Chat API.")
    parser.add_argument("--page-id", help="Pancake Page ID")
    parser.add_argument("--token", help="Pancake Page Access Token")
    parser.add_argument("--limit", type=int, default=10, help="Số lượng hội thoại cần lấy")
    parser.add_argument("--output", help="Đường dẫn lưu file JSON kết quả")
    parser.add_argument("--dummy", action="store_true", help="Chạy chế độ tạo dữ liệu mẫu giả lập")

    args = parser.parse_args()

    page_id = args.page_id or os.getenv("PANCAKE_PAGE_ID")
    token = args.token or os.getenv("PANCAKE_PAGE_ACCESS_TOKEN") or os.getenv("FB_ACCESS_TOKEN")
    
    # Định nghĩa file output
    output_path = args.output
    if not output_path:
        output_path = f"pancake_chats_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

    # Nếu chọn chế độ giả lập hoặc thiếu thông tin thật
    if args.dummy or not page_id or not token or "YOUR_PAGE_ID" in page_id:
        print("[!] Không tìm thấy cấu hình Pancake Page ID hoặc Token thật. Chuyển sang sinh dữ liệu giả lập để thử nghiệm...")
        save_dummy_data(output_path)
        return

    # Tiến hành tải dữ liệu thật
    conversations = fetch_conversations(page_id, token, limit=args.limit)
    if not conversations:
        print("[!] Không lấy được cuộc trò chuyện nào từ API. Chuyển sang sinh dữ liệu giả lập để dự phòng...")
        save_dummy_data(output_path)
        return

    all_chat_data = []
    print(f"[+] Tìm thấy {len(conversations)} cuộc hội thoại. Đang tải lịch sử tin nhắn...")

    for index, conv in enumerate(conversations):
        conv_id = conv.get("id")
        customer_name = conv.get("customer", {}).get("name", "Ẩn danh")
        print(f"[{index+1}/{len(conversations)}] Đang lấy tin nhắn của: {customer_name} (ID: {conv_id})")
        
        messages = fetch_messages(page_id, conv_id, token, limit=50)
        
        chat_entry = {
            "conversation_id": conv_id,
            "customer_name": customer_name,
            "customer_id": conv.get("customer", {}).get("id") if conv.get("customer") else None,
            "tags": [t.get("name") for t in (conv.get("tags") or []) if t and isinstance(t, dict)],
            "updated_at": conv.get("updated_at"),
            "messages": []
        }
        
        for msg in reversed(messages):
            chat_entry["messages"].append({
                "sender": msg.get("from", {}).get("name", "Khách hàng"),
                "content": msg.get("message"),
                "created_at": msg.get("created_at")
            })
            
        all_chat_data.append(chat_entry)
        time.sleep(0.5)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(all_chat_data, f, ensure_ascii=False, indent=2)

    print(f"\n[+] Xuất dữ liệu thành công ra file: {output_path}")

if __name__ == "__main__":
    main()
