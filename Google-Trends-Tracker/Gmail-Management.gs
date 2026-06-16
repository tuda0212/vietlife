/**
 * Gmail Management Tool for Google Apps Script
 * Hỗ trợ kiểm tra và lọc thư rác (Spam) trong 7 ngày gần nhất.
 * 
 * Cách sử dụng:
 * 1. Mở dự án Google Apps Script của bạn (ví dụ liên kết với Sheets hoặc chạy độc lập).
 * 2. Copy đoạn mã này dán vào một file script mới (ví dụ Gmail-Management.gs).
 * 3. Chạy hàm checkSpamEmailsDryRun() để xem danh sách thư rác trong 7 ngày qua (Dry-Run an toàn).
 * 4. Nếu muốn xóa các thư rác này vào Thùng rác (Trash), hãy chạy hàm cleanSpamEmails() sau khi đã xác nhận danh sách.
 */

// Định nghĩa khoảng thời gian lọc (7 ngày gần nhất)
const SPAM_SEARCH_QUERY = 'in:spam newer_than:7d';

/**
 * 1. KIỂM TRA (Dry-Run) - Liệt kê thư rác trong 7 ngày qua mà không xóa
 */
function checkSpamEmailsDryRun() {
  Logger.log('=== BẮT ĐẦU KIỂM TRA THƯ RÁC (DRY-RUN) ===');
  Logger.log('Truy vấn: ' + SPAM_SEARCH_QUERY);
  
  try {
    var threads = GmailApp.search(SPAM_SEARCH_QUERY);
    Logger.log('Tìm thấy tổng cộng: ' + threads.length + ' luồng thư rác.');
    
    if (threads.length === 0) {
      Logger.log('Chúc mừng! Không có thư rác nào trong 7 ngày gần nhất.');
      return;
    }
    
    Logger.log('Dưới đây là danh sách 10 thư rác gần nhất để bạn kiểm tra (tránh xóa nhầm thư quan trọng):');
    Logger.log('--------------------------------------------------');
    
    var limit = Math.min(threads.length, 10);
    for (var i = 0; i < limit; i++) {
      var thread = threads[i];
      var messages = thread.getMessages();
      if (messages.length > 0) {
        var lastMsg = messages[messages.length - 1];
        Logger.log('Thư thứ ' + (i + 1) + ':');
        Logger.log('  - Người gửi: ' + lastMsg.getFrom());
        Logger.log('  - Tiêu đề  : ' + lastMsg.getSubject());
        Logger.log('  - Ngày nhận: ' + lastMsg.getDate());
        Logger.log('  - ID Luồng : ' + thread.getId());
        Logger.log('--------------------------------------------------');
      }
    }
    
    if (threads.length > 10) {
      Logger.log('... và ' + (threads.length - 10) + ' thư rác khác không được liệt kê.');
    }
    
    Logger.log('=== HOÀN TẤT KIỂM TRA ===');
    Logger.log('LƯU Ý: Đây là bản chạy thử (Dry-Run). Chưa có email nào bị xóa.');
    Logger.log('Nếu bạn muốn di chuyển toàn bộ ' + threads.length + ' thư rác này vào Thùng rác (Trash), hãy chạy hàm "cleanSpamEmails()".');
    
  } catch (e) {
    Logger.log('Đã xảy ra lỗi khi kiểm tra thư: ' + e.toString());
  }
}

/**
 * 2. LỌC VÀ XÓA (Clean) - Di chuyển thư rác 7 ngày qua vào Thùng rác (Trash)
 * Chỉ chạy hàm này sau khi bạn đã kiểm tra kỹ danh sách ở bước Dry-Run!
 */
function cleanSpamEmails() {
  Logger.log('=== BẮT ĐẦU DỌN DẸP THƯ RÁC ===');
  
  try {
    var threads = GmailApp.search(SPAM_SEARCH_QUERY);
    Logger.log('Tìm thấy ' + threads.length + ' luồng thư rác cần xử lý.');
    
    if (threads.length === 0) {
      Logger.log('Không có thư rác nào cần dọn dẹp.');
      return;
    }
    
    // Xử lý theo lô (batch) để tránh quá tải giới hạn của Apps Script
    var batchSize = 100;
    var processedCount = 0;
    
    for (var i = 0; i < threads.length; i += batchSize) {
      var batch = threads.slice(i, i + batchSize);
      
      // Di chuyển các luồng thư trong lô vào Thùng rác (Trash)
      GmailApp.moveThreadsToTrash(batch);
      processedCount += batch.length;
      
      Logger.log('Đã di chuyển ' + processedCount + '/' + threads.length + ' luồng thư vào Thùng rác.');
    }
    
    Logger.log('=== DỌN DẸP HOÀN TẤT ===');
    Logger.log('Đã di chuyển thành công ' + processedCount + ' thư rác vào Thùng rác (Trash).');
    Logger.log('Các thư này sẽ tự động bị Gmail xóa vĩnh viễn sau 30 ngày trong Thùng rác.');
    
  } catch (e) {
    Logger.log('Đã xảy ra lỗi khi dọn dẹp thư: ' + e.toString());
  }
}
