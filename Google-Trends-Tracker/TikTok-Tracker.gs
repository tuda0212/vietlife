/**
 * ============================================================
 *  VIETLIFE — TIKTOK TRENDS TRACKER (Module bổ sung)
 *  Lấy hashtag / âm thanh / creator đang trending tại Việt Nam
 *  từ TikTok Creative Center, ghi vào CÙNG Google Sheet với
 *  module Google Trends và phân loại content cho marketing.
 *
 *  CÁCH CÀI: tạo file mới trong cùng dự án Apps Script
 *  (biểu tượng + cạnh "Tệp" > Tập lệnh), đặt tên TikTokTracker,
 *  dán toàn bộ code này vào, Lưu, rồi chạy setupTikTokTrigger() MỘT LẦN.
 *
 *  LƯU Ý: đây là endpoint dữ liệu nội bộ của TikTok Creative Center
 *  (không phải API công khai chính thức). TikTok có thể thay đổi
 *  bất kỳ lúc nào — khi đó tab NhatKy sẽ báo lỗi để xử lý kịp thời.
 * ============================================================
 */

// ----------------- CẤU HÌNH TIKTOK -----------------
var TT_CONFIG = {
  COUNTRY: 'VN',
  PERIOD_DAYS: 7,        // cửa sổ xếp hạng trend: 7 ngày (có thể đổi 1, 30, 120)
  LIMIT: 30,             // số dòng lấy mỗi loại
  UPDATE_EVERY_HOURS: 6, // Creative Center cập nhật theo NGÀY -> 6h/lần là đủ
  SHEET_HASHTAG: 'TT_Hashtag',
  SHEET_SOUND: 'TT_AmThanh',
  SHEET_CREATOR: 'TT_Creator',
  SHEET_DASH: 'TT_Dashboard',
  SHEET_LOG: 'NhatKy',
  // Ngưỡng vòng đời xu hướng TikTok tính theo NGÀY trên bảng trending
  NGAN_HAN_NGAY: 3,
  TRUNG_HAN_NGAY: 14
};

var TT_BASE = 'https://ads.tiktok.com/creative_radar_api/v1/popular_trend/';
var TT_ENDPOINTS = {
  hashtag: [
    TT_BASE + 'hashtag/list?page=1&limit={L}&period={P}&country_code={C}&sort_by=popular',
    TT_BASE + 'hashtag/list?page=1&limit={L}&period={P}&country_code={C}'
  ],
  sound: [
    TT_BASE + 'sound/rank_list?page=1&limit={L}&period={P}&country_code={C}&rank_type=popular',
    TT_BASE + 'sound/rank_list?page=1&limit={L}&period={P}&country_code={C}'
  ],
  creator: [
    TT_BASE + 'creator/list?page=1&limit={L}&period=30&country_code={C}&sort_by=follower',
    TT_BASE + 'creator/list?page=1&limit={L}&period=30&country_code={C}&sort_by=engagement'
  ]
};

// ================== HÀM CHÍNH (trigger gọi định kỳ) ==================
function updateTikTokTrends() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var okCount = 0;
  okCount += updateTTHashtags_(ss) ? 1 : 0;
  okCount += updateTTSounds_(ss) ? 1 : 0;
  okCount += updateTTCreators_(ss) ? 1 : 0;
  if (okCount > 0) buildTTDashboard_(ss);
  ttLog_(ss, okCount === 3 ? 'OK' : (okCount > 0 ? 'MOT_PHAN' : 'LOI'),
    'Cập nhật xong ' + okCount + '/3 nguồn (hashtag, âm thanh, creator).');
}

// ================== 1. HASHTAG TRENDING ==================
function updateTTHashtags_(ss) {
  var data = ttFetch_('hashtag');
  var list = data && data.list ? data.list : [];
  if (!list.length) { ttLog_(ss, 'LOI', 'Hashtag: không lấy được dữ liệu — TikTok có thể đã đổi endpoint.'); return false; }

  var sheet = getOrCreateSheet_(ss, TT_CONFIG.SHEET_HASHTAG, [
    'Thời điểm ghi', 'Năm', 'Tháng', 'Ngày', 'Hashtag', 'Hạng', 'Biến động hạng',
    'Lượt xem video', 'Số video đăng', 'Chủ đề content', 'Tính chất',
    'Lần đầu xuất hiện', 'Số ngày trên trending', 'Loại xu hướng', 'Trạng thái'
  ]);

  var now = new Date();
  var firstSeen = ttFirstSeenMap_(sheet, 5, 12);   // cột E (hashtag), cột L (lần đầu)
  var prevRank = ttPrevRankMap_(sheet, 5, 6);      // hạng của lần ghi gần nhất
  var rows = list.map(function (h) {
    var name = '#' + (h.hashtag_name || '');
    var key = normalize_(name);
    var first = firstSeen[key] || now;
    var daysAlive = Math.max(1, Math.round((now - first) / 86400000) + 1);
    var category = classifyHashtag_(h.hashtag_name || '');
    var rank = h.rank || '';
    var status;
    if (!(key in prevRank)) status = 'Mới vào bảng';
    else if (rank && prevRank[key] && rank < prevRank[key]) status = 'Đang tăng';
    else if (rank && prevRank[key] && rank > prevRank[key]) status = 'Đang giảm';
    else status = 'Ổn định';
    return [
      Utilities.formatDate(now, CONFIG.TIMEZONE, 'yyyy-MM-dd HH:mm'),
      Number(Utilities.formatDate(now, CONFIG.TIMEZONE, 'yyyy')),
      Number(Utilities.formatDate(now, CONFIG.TIMEZONE, 'MM')),
      Number(Utilities.formatDate(now, CONFIG.TIMEZONE, 'dd')),
      name, rank, (h.rank_diff != null ? h.rank_diff : ''),
      h.video_views || '', h.publish_cnt || '',
      category, classifyValue_(category),
      Utilities.formatDate(first, CONFIG.TIMEZONE, 'yyyy-MM-dd HH:mm'),
      daysAlive, ttClassifyDuration_(daysAlive), status
    ];
  });
  sheet.getRange(sheet.getLastRow() + 1, 1, rows.length, rows[0].length).setValues(rows);
  return true;
}

// ================== 2. ÂM THANH TRENDING ==================
function updateTTSounds_(ss) {
  var data = ttFetch_('sound');
  var list = data ? (data.sound_list || data.list || []) : [];
  if (!list.length) { ttLog_(ss, 'LOI', 'Âm thanh: không lấy được dữ liệu.'); return false; }

  var sheet = getOrCreateSheet_(ss, TT_CONFIG.SHEET_SOUND, [
    'Thời điểm ghi', 'Năm', 'Tháng', 'Ngày', 'Tên bài / âm thanh', 'Nghệ sĩ',
    'Hạng', 'Link nghe thử', 'Gợi ý sử dụng'
  ]);
  var now = new Date();
  var rows = list.map(function (s) {
    return [
      Utilities.formatDate(now, CONFIG.TIMEZONE, 'yyyy-MM-dd HH:mm'),
      Number(Utilities.formatDate(now, CONFIG.TIMEZONE, 'yyyy')),
      Number(Utilities.formatDate(now, CONFIG.TIMEZONE, 'MM')),
      Number(Utilities.formatDate(now, CONFIG.TIMEZONE, 'dd')),
      s.title || '', s.author || '', s.rank || '',
      s.link || (s.clip_id ? 'https://www.tiktok.com/music/x-' + s.clip_id : ''),
      'Nhạc nền Reels/TikTok bắt trend trong tuần'
    ];
  });
  sheet.getRange(sheet.getLastRow() + 1, 1, rows.length, rows[0].length).setValues(rows);
  return true;
}

// ================== 3. CREATOR NỔI BẬT (tham khảo hợp tác KOC/KOL) ==================
function updateTTCreators_(ss) {
  var data = ttFetch_('creator');
  var list = data ? (data.creators || data.list || []) : [];
  if (!list.length) { ttLog_(ss, 'LOI', 'Creator: không lấy được dữ liệu.'); return false; }

  var sheet = getOrCreateSheet_(ss, TT_CONFIG.SHEET_CREATOR, [
    'Thời điểm ghi', 'Năm', 'Tháng', 'Ngày', 'Tên creator', 'Follower',
    'Tổng lượt thích', 'Link kênh', 'Ghi chú đánh giá hợp tác'
  ]);
  var now = new Date();
  var rows = list.map(function (c) {
    return [
      Utilities.formatDate(now, CONFIG.TIMEZONE, 'yyyy-MM-dd HH:mm'),
      Number(Utilities.formatDate(now, CONFIG.TIMEZONE, 'yyyy')),
      Number(Utilities.formatDate(now, CONFIG.TIMEZONE, 'MM')),
      Number(Utilities.formatDate(now, CONFIG.TIMEZONE, 'dd')),
      c.nick_name || c.nickname || '', c.follower_cnt || '', c.liked_cnt || '',
      c.tt_link || c.link || '',
      '' // đội marketing tự ghi chú: phù hợp ngành y tế? chi phí? liên hệ?
    ];
  });
  sheet.getRange(sheet.getLastRow() + 1, 1, rows.length, rows[0].length).setValues(rows);
  return true;
}

// ================== DASHBOARD TIKTOK ==================
function buildTTDashboard_(ss) {
  var sheet = getOrCreateSheet_(ss, TT_CONFIG.SHEET_DASH, []);
  sheet.clear();
  var H = TT_CONFIG.SHEET_HASHTAG, S = TT_CONFIG.SHEET_SOUND;
  var rows = [
    ['VIETLIFE — DASHBOARD TIKTOK TRENDS VIỆT NAM', '', ''],
    ['Cập nhật lần cuối:', Utilities.formatDate(new Date(), CONFIG.TIMEZONE, 'dd/MM/yyyy HH:mm'), ''],
    ['', '', ''],
    ['1. HASHTAG SỨC KHỎE - Y TẾ ĐANG TRENDING (ƯU TIÊN CONTENT VIETLIFE ⭐)', '', ''],
    ['=IFERROR(QUERY(' + H + '!A:O, "select E, max(F), max(H), max(M) where J = \'Sức khỏe - Y tế\' group by E order by max(M) desc limit 15 label E \'Hashtag\', max(F) \'Hạng\', max(H) \'Lượt xem\', max(M) \'Số ngày trending\'"), "Chưa có hashtag y tế trong bảng — xem mục 2 để mượn trend")', '', ''],
    ['', '', ''],
    ['2. HASHTAG ĐANG TĂNG NHANH HÔM NAY — BẮT TREND NGAY', '', ''],
    ['=IFERROR(QUERY(' + H + '!A:O, "select E, F, H, J where O = \'Đang tăng\' and D = " & DAY(TODAY()) & " and C = " & MONTH(TODAY()) & " order by F limit 15 label E \'Hashtag\', F \'Hạng\', H \'Lượt xem\', J \'Chủ đề\'"), "Chưa có dữ liệu hôm nay")', '', ''],
    ['', '', ''],
    ['3. HASHTAG XU HƯỚNG DÀI HẠN (>14 NGÀY) — ĐÁNG ĐẦU TƯ SERIES', '', ''],
    ['=IFERROR(QUERY(' + H + '!A:O, "select E, J, max(M) where N = \'Xu hướng dài hạn\' group by E, J order by max(M) desc limit 15 label E \'Hashtag\', J \'Chủ đề\', max(M) \'Số ngày\'"), "Chưa có dữ liệu")', '', ''],
    ['', '', ''],
    ['4. NHẠC TRENDING TUẦN NÀY — DÙNG CHO REELS/TIKTOK', '', ''],
    ['=IFERROR(QUERY(' + S + '!A:I, "select E, F, G where D = " & DAY(TODAY()) & " and C = " & MONTH(TODAY()) & " order by G limit 10 label E \'Bài hát\', F \'Nghệ sĩ\', G \'Hạng\'"), "Chưa có dữ liệu hôm nay")', '', '']
  ];
  sheet.getRange(1, 1, rows.length, 3).setValues(rows);
  sheet.getRange('A1').setFontSize(14).setFontWeight('bold').setFontColor('#fe2c55');
  ['A4', 'A7', 'A10', 'A13'].forEach(function (a) {
    sheet.getRange(a).setFontWeight('bold').setBackground('#ffe2e8');
  });
  sheet.autoResizeColumns(1, 3);
}

// ================== GỌI ENDPOINT TIKTOK ==================
function ttFetch_(kind) {
  var urls = TT_ENDPOINTS[kind];
  for (var i = 0; i < urls.length; i++) {
    var url = urls[i]
      .replace('{L}', TT_CONFIG.LIMIT)
      .replace('{P}', TT_CONFIG.PERIOD_DAYS)
      .replace('{C}', TT_CONFIG.COUNTRY);
    try {
      var resp = UrlFetchApp.fetch(url, {
        muteHttpExceptions: true,
        followRedirects: true,
        headers: {
          'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
          'Referer': 'https://ads.tiktok.com/business/creativecenter/inspiration/popular/hashtag/pc/en',
          'Accept': 'application/json, text/plain, */*',
          'Accept-Language': 'en-US,en;q=0.9,vi;q=0.8'
        }
      });
      if (resp.getResponseCode() !== 200) continue;
      var body = JSON.parse(resp.getContentText());
      // Creative Center trả về {code: 0, data: {...}} khi thành công
      if (body && body.code === 0 && body.data) return body.data;
    } catch (e) {
      Logger.log('TikTok endpoint lỗi (' + kind + '): ' + e);
    }
  }
  return null;
}

// ================== PHÂN LOẠI & TIỆN ÍCH ==================
// Hashtag viết liền không dấu (vd: suckhoe, giamcan) -> so khớp sau khi bỏ
// dấu + bỏ khoảng trắng của bộ từ khóa CATEGORY_RULES bên Code.gs
// Chuỗi dễ gây nhầm lẫn khi viết liền (vd "khampha" chứa "kham" -> nhầm Y tế)
var TT_HASHTAG_BLOCKLIST = ['khampha', 'chaybo', 'chayban'];

function classifyHashtag_(hashtagName) {
  var t = normalize_(hashtagName).replace(/\s+/g, '');
  if (!t) return 'Khác';
  TT_HASHTAG_BLOCKLIST.forEach(function (b) { t = t.split(b).join('|'); });
  for (var i = 0; i < CATEGORY_RULES.length; i++) {
    var rule = CATEGORY_RULES[i];
    for (var j = 0; j < rule.keywords.length; j++) {
      var k = normalize_(rule.keywords[j]).replace(/\s+/g, '');
      if (k.length >= 4 && t.indexOf(k) !== -1) return rule.name;
    }
  }
  return 'Khác';
}

function ttClassifyDuration_(daysAlive) {
  if (daysAlive < TT_CONFIG.NGAN_HAN_NGAY) return 'Xu hướng ngắn hạn';
  if (daysAlive < TT_CONFIG.TRUNG_HAN_NGAY) return 'Xu hướng trung hạn';
  return 'Xu hướng dài hạn';
}

// Map: tên (cột colName) -> thời điểm xuất hiện sớm nhất (cột colFirst)
function ttFirstSeenMap_(sheet, colName, colFirst) {
  var map = {};
  var last = sheet.getLastRow();
  if (last < 2) return map;
  var data = sheet.getRange(2, 1, last - 1, Math.max(colName, colFirst)).getValues();
  data.forEach(function (r) {
    var key = normalize_(String(r[colName - 1]));
    var d = parseVNDate_(String(r[colFirst - 1])) || parseVNDate_(String(r[0]));
    if (key && d && (!map[key] || d < map[key])) map[key] = d;
  });
  return map;
}

// Map: tên -> hạng ở lần ghi GẦN NHẤT (để tính Đang tăng / Đang giảm)
function ttPrevRankMap_(sheet, colName, colRank) {
  var map = {};
  var last = sheet.getLastRow();
  if (last < 2) return map;
  var data = sheet.getRange(2, 1, last - 1, Math.max(colName, colRank)).getValues();
  var lastBatchTime = String(data[data.length - 1][0]);
  data.forEach(function (r) {
    if (String(r[0]) === lastBatchTime) {
      var key = normalize_(String(r[colName - 1]));
      var rank = Number(r[colRank - 1]);
      if (key && rank) map[key] = rank;
    }
  });
  return map;
}

function ttLog_(ss, status, message) {
  var sheet = getOrCreateSheet_(ss, TT_CONFIG.SHEET_LOG, ['Thời điểm', 'Nguồn', 'Trạng thái', 'Chi tiết']);
  sheet.appendRow([
    Utilities.formatDate(new Date(), CONFIG.TIMEZONE, 'yyyy-MM-dd HH:mm'),
    'TikTok', status, message
  ]);
  // giữ tối đa 300 dòng nhật ký
  var extra = sheet.getLastRow() - 301;
  if (extra > 0) sheet.deleteRows(2, extra);
}

// ================== CÀI ĐẶT ==================
/** Chạy hàm này MỘT LẦN để bật tự động cập nhật TikTok (mặc định 6h/lần) */
function setupTikTokTrigger() {
  ScriptApp.getProjectTriggers().forEach(function (t) {
    if (t.getHandlerFunction() === 'updateTikTokTrends') ScriptApp.deleteTrigger(t);
  });
  ScriptApp.newTrigger('updateTikTokTrends').timeBased().everyHours(TT_CONFIG.UPDATE_EVERY_HOURS).create();
  updateTikTokTrends(); // chạy ngay lần đầu
  SpreadsheetApp.getActiveSpreadsheet().toast(
    'Đã bật tự động cập nhật TikTok mỗi ' + TT_CONFIG.UPDATE_EVERY_HOURS + ' giờ!',
    'Vietlife TikTok Tracker');
}
