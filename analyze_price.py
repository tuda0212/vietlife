import json
import re

with open('/Users/daudau/VL/pancake_chats_real_2.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

total_convs = len(data)
ask_price_early_count = 0
left_phone_count = 0
dropped_off_count = 0

phone_pattern = re.compile(r'0[35789]\d{8}')
price_keywords = ['giá', 'nhiêu', 'tiền', 'bao nhieu', 'bnhieu', 'bnhiu', '1 hộp']

for conv in data:
    messages = conv.get('messages', [])
    # messages are usually in chronological or reverse chronological?
    # fetch_pancake_chats.py says:
    # for msg in reversed(messages): chat_entry["messages"].append(...)
    # So the messages array is in chronological order (oldest first).
    
    # Filter customer messages
    customer_msgs = [m for m in messages if 'Bình An' not in m.get('sender', '') and 'Page' not in m.get('sender', '')]
    
    if not customer_msgs:
        continue
        
    # Check if first or second customer message asks for price
    early_msgs = customer_msgs[:2]
    asked_price = False
    for m in early_msgs:
        content = m.get('content', '').lower()
        if any(kw in content for kw in price_keywords):
            asked_price = True
            break
            
    if asked_price:
        ask_price_early_count += 1
        
        # Check if they left a phone number anywhere in their messages
        left_phone = False
        for m in customer_msgs:
            if phone_pattern.search(m.get('content', '')):
                left_phone = True
                break
                
        if left_phone:
            left_phone_count += 1
        else:
            # Check if dropped off (last message is from page)
            if len(messages) > 0 and ('Bình An' in messages[-1].get('sender', '') or 'Page' in messages[-1].get('sender', '')):
                dropped_off_count += 1

print(f"Tổng số hội thoại: {total_convs}")
print(f"Số người hỏi luôn về giá: {ask_price_early_count}")
print(f"Trong đó, số người để lại SĐT (tỉ lệ mua ngay): {left_phone_count}")
print(f"Số người dừng không tương tác (rớt đài): {dropped_off_count}")
