import imaplib
import email
from email.header import decode_header
import datetime
import os
import getpass

def decode_mime_header(header_value):
    if not header_value:
        return "No Subject"
    decoded = decode_header(header_value)
    parts = []
    for text, codec in decoded:
        if isinstance(text, bytes):
            try:
                parts.append(text.decode(codec or 'utf-8', errors='replace'))
            except Exception:
                parts.append(text.decode('utf-8', errors='replace'))
        else:
            parts.append(str(text))
    return "".join(parts)

def select_spam_folder(mail):
    # Thử danh sách các tên thư mục Spam thông dụng trong Gmail (tùy thuộc vào ngôn ngữ của tài khoản)
    spam_folders = ['"[Gmail]/Spam"', '"[Gmail]/Thư rác"', 'Spam', 'Trash']
    for folder in spam_folders:
        try:
            status, data = mail.select(folder)
            if status == 'OK':
                return folder, status
        except Exception:
            continue
    return None, None

def select_trash_folder(mail):
    # Thử danh sách các tên thư mục Thùng rác thông dụng
    trash_folders = ['"[Gmail]/Trash"', '"[Gmail]/Thùng rác"', 'Trash']
    for folder in trash_folders:
        try:
            # Kiểm tra xem folder có tồn tại bằng cách thử select (sau đó nhớ select lại Spam)
            status, data = mail.select(folder)
            if status == 'OK':
                return folder
        except Exception:
            continue
    return None

def main():
    print("=== CÔNG CỤ LỌC THƯ RÁC GMAIL (IMAP) ===")
    print("Để sử dụng công cụ này, bạn cần bật xác minh 2 bước trên tài khoản Google và tạo 'Mật khẩu ứng dụng' (App Password).")
    print("Tạo mật khẩu ứng dụng tại: https://myaccount.google.com/apppasswords\n")
    
    # Đọc email và mật khẩu từ biến môi trường hoặc nhập thủ công
    username = os.environ.get("GMAIL_USER") or input("Nhập địa chỉ Gmail của bạn (ví dụ: user@gmail.com): ").strip()
    password = os.environ.get("GMAIL_APP_PASSWORD")
    
    if not password:
        password = getpass.getpass("Nhập Mật khẩu ứng dụng Gmail (16 ký tự viết liền): ").strip()
        
    if not username or not password:
        print("Lỗi: Địa chỉ email và mật khẩu không được để trống!")
        return

    # Kết nối IMAP Gmail
    try:
        print("\nĐang kết nối tới imap.gmail.com...")
        mail = imaplib.IMAP4_SSL("imap.gmail.com", 993)
        mail.login(username, password)
        print("Đăng nhập thành công!")
        
        # Chọn thư mục Spam
        spam_folder, status = select_spam_folder(mail)
        if not spam_folder:
            print("Lỗi: Không tìm thấy thư mục Spam/Thư rác trên tài khoản Gmail của bạn.")
            mail.logout()
            return
            
        print(f"Đã mở thư mục: {spam_folder}")
        
        # Tính toán ngày cách đây 7 ngày (định dạng IMAP: DD-Mon-YYYY)
        target_date = (datetime.datetime.now() - datetime.timedelta(days=7)).strftime("%d-%b-%Y")
        
        # Tìm kiếm email trong thư mục Spam từ target_date
        print(f"Đang tìm kiếm thư rác nhận được từ ngày {target_date}...")
        status, response_data = mail.search(None, f"SINCE {target_date}")
        
        if status != 'OK':
            print("Lỗi khi tìm kiếm email.")
            mail.logout()
            return
            
        mail_ids = response_data[0].split()
        total_spam = len(mail_ids)
        print(f"Tìm thấy {total_spam} thư rác trong 7 ngày gần nhất.")
        
        if total_spam == 0:
            mail.logout()
            return
            
        # Liệt kê thông tin 10 email gần nhất (dry-run)
        print("\nDanh sách 10 thư rác gần nhất:")
        print("-" * 80)
        
        # Duyệt từ thư mới nhất (cuối danh sách)
        limit = min(total_spam, 10)
        for i in range(1, limit + 1):
            msg_id = mail_ids[-i]
            status, msg_data = mail.fetch(msg_id, "(RFC822.SIZE BODY[HEADER.FIELDS (FROM SUBJECT DATE)])")
            if status != 'OK':
                continue
                
            header_text = msg_data[0][1].decode('utf-8', errors='replace')
            msg = email.message_from_string(header_text)
            
            sender = decode_mime_header(msg.get("From"))
            subject = decode_mime_header(msg.get("Subject"))
            date = msg.get("Date", "Unknown")
            
            print(f"[{i}] Người gửi: {sender}")
            print(f"    Tiêu đề  : {subject}")
            print(f"    Ngày nhận: {date}")
            print("-" * 80)
            
        if total_spam > 10:
            print(f"... và {total_spam - 10} thư rác khác.")
            
        # Hỏi ý kiến người dùng trước khi dọn dẹp
        confirm = input(f"\nBạn có muốn di chuyển toàn bộ {total_spam} thư rác này vào Thùng rác (Trash) không? (y/N): ").strip().lower()
        if confirm == 'y' or confirm == 'yes':
            # Tìm thư mục Trash
            trash_folder = select_trash_folder(mail)
            if not trash_folder:
                print("Không tìm thấy thư mục Thùng rác. Đang chuyển sang đánh dấu xóa trực tiếp...")
                # Nếu không tìm thấy folder Trash, ta sẽ đánh dấu xóa (\Deleted) trực tiếp
                for msg_id in mail_ids:
                    mail.store(msg_id, '+FLAGS', '\\Deleted')
                mail.expunge()
                print("Đã xóa vĩnh viễn các thư rác thành công!")
            else:
                # Đảm bảo đã select lại Spam trước khi copy
                mail.select(spam_folder)
                # Copy thư mục sang Trash và đánh dấu xóa ở Spam
                print(f"Đang di chuyển thư sang {trash_folder}...")
                for msg_id in mail_ids:
                    # Di chuyển bằng lệnh COPY sang Trash
                    copy_status, _ = mail.copy(msg_id, trash_folder)
                    if copy_status == 'OK':
                        # Đánh dấu xóa tại folder cũ
                        mail.store(msg_id, '+FLAGS', '\\Deleted')
                
                # Thực hiện xóa thực tế ở folder Spam các mail đã đánh dấu \Deleted
                mail.expunge()
                print("Đã di chuyển thành công toàn bộ thư rác vào Thùng rác!")
                
        else:
            print("Đã hủy thao tác. Không có thư nào bị di chuyển hoặc xóa.")
            
        # Đăng xuất
        mail.close()
        mail.logout()
        print("\nĐã đóng kết nối Gmail an toàn.")
        
    except imaplib.IMAP4.error as e:
        print(f"\nLỗi đăng nhập hoặc kết nối IMAP: {e}")
        print("Vui lòng kiểm tra lại địa chỉ email hoặc Mật khẩu ứng dụng của bạn.")
    except Exception as e:
        print(f"\nĐã xảy ra lỗi: {e}")

if __name__ == "__main__":
    main()
