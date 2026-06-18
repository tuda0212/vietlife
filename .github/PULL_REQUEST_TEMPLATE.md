## 📋 Mô tả thay đổi
<!-- Giải thích ngắn gọn: bạn đã làm gì và tại sao? -->


## 🔗 Liên quan đến
<!-- Issue / task nào? Ví dụ: Closes #12, Fixes #5 -->
- 

## ✅ Checklist trước khi merge

### Bảo mật (BẮT BUỘC)
- [ ] Không có token/key/password nào bị hardcode trong code
- [ ] Không commit file `.env`, `*.json` credentials
- [ ] Đã kiểm tra `.gitignore` bao gồm các file nhạy cảm

### Code Quality
- [ ] Code đã chạy thử trên máy cục bộ thành công
- [ ] Không break các pipeline đang chạy trên Cloud Run
- [ ] Commit message theo đúng convention (`feat:`, `fix:`, `sql:`, `config:`, `docs:`, `chore:`)

### Tài liệu
- [ ] Cập nhật README.md nếu thêm tính năng mới
- [ ] Thêm comment giải thích nếu logic phức tạp

## 🧪 Cách test thay đổi này
<!-- Hướng dẫn người review kiểm tra cụ thể -->

```bash
# Ví dụ:
python3 scripts/verify_view.py
# hoặc
python3 scripts/inspect_bq.py
```

## 📊 Kết quả test (nếu có)
<!-- Paste output hoặc screenshot -->

## ⚠️ Lưu ý khi deploy
<!-- Có cần chạy migration? Cần cập nhật biến môi trường trên Cloud Run? -->
