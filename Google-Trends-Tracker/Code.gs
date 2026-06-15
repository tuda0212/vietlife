/**
 * ============================================================
 *  VIETLIFE — GOOGLE TRENDS TRACKER
 *  Tự động lấy chủ đề trending tại Việt Nam mỗi 1 giờ,
 *  ghi vào Google Sheet và phân loại content phục vụ marketing.
 *
 *  Cài đặt: xem file HUONG-DAN-CAI-DAT.md
 *  Sau khi dán code: chạy hàm setupTrigger() MỘT LẦN để bật tự động.
 * ============================================================
 */

// ----------------- CẤU HÌNH -----------------
var CONFIG = {
  GEO: 'VN', // Quốc gia theo dõi
  // Endpoint chính + dự phòng (Google đôi khi đổi đường dẫn)
  RSS_URLS: [
    'https://trends.google.com/trending/rss?geo=VN',
    'https://trends.google.com/trends/trendingsearches/daily/rss?geo=VN'
  ],
  SHEET_RAW: 'DuLieuTho',       // dữ liệu thô tích lũy
  SHEET_ACTIVE: 'DangTrending', // snapshot trending hiện tại
  SHEET_DASH: 'Dashboard',      // tổng hợp + phân tích
  TIMEZONE: 'Asia/Ho_Chi_Minh',
  // Ngưỡng phân loại xu hướng theo số GIỜ tồn tại trên bảng trending
  NGAN_HAN_GIO: 24,   // dưới 24h  -> Ngắn hạn
  TRUNG_HAN_GIO: 168  // 24h-7ngày -> Trung hạn; trên 7 ngày -> Dài hạn
};

// Bộ từ khóa phân loại chủ đề content (có thể bổ sung thoải mái)
var CATEGORY_RULES = [
  { name: 'Sức khỏe - Y tế', keywords: ['bệnh', 'benh', 'sức khỏe', 'suc khoe', 'ung thư', 'ung thu', 'vaccine', 'vắc xin', 'vac xin', 'bác sĩ', 'bac si', 'bệnh viện', 'benh vien', 'phòng khám', 'phong kham', 'thuốc', 'thuoc', 'dịch', 'virus', 'cúm', 'cum', 'sốt', 'sot', 'đột quỵ', 'dot quy', 'tiểu đường', 'tieu duong', 'huyết áp', 'huyet ap', 'xương khớp', 'xuong khop', 'thoát vị', 'thoat vi', 'khám', 'kham', 'y tế', 'y te', 'dinh dưỡng', 'dinh duong', 'tâm lý', 'tam ly', 'mang thai', 'sinh con', 'nội soi', 'noi soi'] },
  { name: 'Giải trí', keywords: ['phim', 'ca sĩ', 'ca si', 'concert', 'mv', 'showbiz', 'hoa hậu', 'hoa hau', 'idol', 'rapper', 'diễn viên', 'dien vien', 'gameshow', 'game show', 'netflix', 'trailer', 'album', 'liveshow', 'tiktoker', 'youtuber', 'streamer', 'scandal', 'hot girl', 'người mẫu', 'nguoi mau', 'kpop', 'k-pop', 'vpop', 'v-pop', 'anh trai', 'chị đẹp', 'chi dep'] },
  { name: 'Thể thao', keywords: ['bóng đá', 'bong da', 'việt nam vs', 'viet nam vs', 'u23', 'u22', 'sea games', 'world cup', 'champions league', 'ngoại hạng', 'ngoai hang', 'premier league', 'v-league', 'vleague', 'tennis', 'cầu lông', 'cau long', 'boxing', 'mma', 'pickleball', 'marathon', 'olympic', 'fifa', 'hlv', 'đội tuyển', 'doi tuyen', 'tỷ số', 'ty so', 'lịch thi đấu', 'lich thi dau'] },
  { name: 'Thời sự - Xã hội', keywords: ['bão', 'bao so', 'lũ', 'lu lut', 'lụt', 'động đất', 'dong dat', 'tai nạn', 'tai nan', 'cháy', 'chay', 'bắt', 'bat giu', 'khởi tố', 'khoi to', 'nghị định', 'nghi dinh', 'luật', 'luat', 'chính phủ', 'chinh phu', 'quốc hội', 'quoc hoi', 'thời tiết', 'thoi tiet', 'giá xăng', 'gia xang', 'giá vàng', 'gia vang', 'lương', 'luong', 'thuế', 'thue', 'bhyt', 'bảo hiểm', 'bao hiem'] },
  { name: 'Công nghệ', keywords: ['iphone', 'samsung', 'android', 'ai ', 'chatgpt', 'gemini', 'app', 'ứng dụng', 'ung dung', 'laptop', 'chip', 'tesla', 'vinfast', 'crypto', 'bitcoin', 'update', 'ios', 'google', 'facebook', 'zalo', 'tiktok ban'] },
  { name: 'Giáo dục - Hữu ích', keywords: ['điểm thi', 'diem thi', 'tuyển sinh', 'tuyen sinh', 'đại học', 'dai hoc', 'thi tốt nghiệp', 'thi tot nghiep', 'học bổng', 'hoc bong', 'lịch nghỉ', 'lich nghi', 'cách ', 'cach lam', 'hướng dẫn', 'huong dan', 'mẹo', 'meo ', 'tra cứu', 'tra cuu', 'đăng ký', 'dang ky', 'hồ sơ', 'ho so', 'thủ tục', 'thu tuc'] }
];

// Chủ đề được coi là "có giá trị dài hạn cho người dùng" (evergreen)
var EVERGREEN_CATEGORIES = ['Sức khỏe - Y tế', 'Giáo dục - Hữu ích'];

// ================== HÀM CHÍNH (trigger gọi mỗi giờ) ==================
function updateTrends() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var items = fetchTrendingItems_();
  if (!items.length) {
    Logger.log('Không lấy được dữ liệu trending. Sẽ thử lại ở lần chạy sau.');
    return;
  }

  var rawSheet = getOrCreateSheet_(ss, CONFIG.SHEET_RAW, [
    'Thời điểm ghi', 'Năm', 'Tháng', 'Ngày', 'Giờ', 'Từ khóa',
    'Lượt tìm kiếm (ước tính)', 'Tin liên quan', 'Nguồn tin', 'Link tham khảo',
    'Chủ đề content', 'Tính chất', 'Lần đầu xuất hiện', 'Số giờ trên trending', 'Loại xu hướng'
  ]);

  var now = new Date();
  var firstSeenMap = buildFirstSeenMap_(rawSheet);
  var rows = [];

  items.forEach(function (it) {
    var firstSeen = firstSeenMap[normalize_(it.title)] || now;
    var hoursAlive = Math.max(1, Math.round((now - firstSeen) / 3600000) + 1);
    var category = classifyCategory_(it.title + ' ' + it.newsTitle);
    rows.push([
      Utilities.formatDate(now, CONFIG.TIMEZONE, 'yyyy-MM-dd HH:mm'),
      Number(Utilities.formatDate(now, CONFIG.TIMEZONE, 'yyyy')),
      Number(Utilities.formatDate(now, CONFIG.TIMEZONE, 'MM')),
      Number(Utilities.formatDate(now, CONFIG.TIMEZONE, 'dd')),
      Number(Utilities.formatDate(now, CONFIG.TIMEZONE, 'HH')),
      it.title,
      it.traffic,
      it.newsTitle,
      it.newsSource,
      it.newsUrl,
      category,
      classifyValue_(category),
      Utilities.formatDate(firstSeen, CONFIG.TIMEZONE, 'yyyy-MM-dd HH:mm'),
      hoursAlive,
      classifyDuration_(hoursAlive)
    ]);
  });

  rawSheet.getRange(rawSheet.getLastRow() + 1, 1, rows.length, rows[0].length).setValues(rows);
  writeActiveSnapshot_(ss, rows);
  buildDashboard_(ss);
}

// ================== LẤY & PHÂN TÍCH DỮ LIỆU ==================
function fetchTrendingItems_() {
  for (var i = 0; i < CONFIG.RSS_URLS.length; i++) {
    try {
      var resp = UrlFetchApp.fetch(CONFIG.RSS_URLS[i], { muteHttpExceptions: true, followRedirects: true });
      if (resp.getResponseCode() !== 200) continue;
      var items = parseRss_(resp.getContentText());
      if (items.length) return items;
    } catch (e) {
      Logger.log('Endpoint lỗi: ' + CONFIG.RSS_URLS[i] + ' — ' + e);
    }
  }
  return [];
}

function parseRss_(xmlText) {
  var doc = XmlService.parse(xmlText);
  var channel = doc.getRootElement().getChild('channel');
  if (!channel) return [];
  var ht = XmlService.getNamespace('ht', 'https://trends.google.com/trending/rss');
  var htOld = XmlService.getNamespace('ht', 'https://trends.google.co.uk/trends/trendingsearches/daily'); // namespace cũ
  var out = [];
  channel.getChildren('item').forEach(function (item) {
    var title = item.getChildText('title') || '';
    if (!title) return;
    var traffic = item.getChildText('approx_traffic', ht) || item.getChildText('approx_traffic', htOld) || '';
    var news = item.getChild('news_item', ht) || item.getChild('news_item', htOld);
    out.push({
      title: title.trim(),
      traffic: traffic,
      newsTitle: news ? (news.getChildText('news_item_title', ht) || news.getChildText('news_item_title', htOld) || '') : '',
      newsSource: news ? (news.getChildText('news_item_source', ht) || news.getChildText('news_item_source', htOld) || '') : '',
      newsUrl: news ? (news.getChildText('news_item_url', ht) || news.getChildText('news_item_url', htOld) || '') : ''
    });
  });
  return out;
}

function classifyCategory_(text) {
  var t = ' ' + normalize_(text) + ' ';
  for (var i = 0; i < CATEGORY_RULES.length; i++) {
    var rule = CATEGORY_RULES[i];
    for (var j = 0; j < rule.keywords.length; j++) {
      if (t.indexOf(normalize_(rule.keywords[j])) !== -1) return rule.name;
    }
  }
  return 'Khác';
}

function classifyValue_(category) {
  if (EVERGREEN_CATEGORIES.indexOf(category) !== -1) return 'Giá trị cho người dùng';
  if (category === 'Giải trí' || category === 'Thể thao') return 'Giải trí / bắt trend';
  if (category === 'Thời sự - Xã hội') return 'Thời sự / cập nhật';
  return 'Cần đánh giá thủ công';
}

function classifyDuration_(hoursAlive) {
  if (hoursAlive < CONFIG.NGAN_HAN_GIO) return 'Xu hướng ngắn hạn';
  if (hoursAlive < CONFIG.TRUNG_HAN_GIO) return 'Xu hướng trung hạn';
  return 'Xu hướng dài hạn';
}

// Tra cứu thời điểm một từ khóa xuất hiện lần đầu trong dữ liệu cũ
function buildFirstSeenMap_(rawSheet) {
  var map = {};
  var last = rawSheet.getLastRow();
  if (last < 2) return map;
  var data = rawSheet.getRange(2, 1, last - 1, 13).getValues();
  data.forEach(function (r) {
    var key = normalize_(String(r[5]));
    var firstSeen = parseVNDate_(String(r[12])) || parseVNDate_(String(r[0]));
    if (key && firstSeen && (!map[key] || firstSeen < map[key])) map[key] = firstSeen;
  });
  return map;
}

// ================== GHI SHEET ==================
function writeActiveSnapshot_(ss, rows) {
  var sheet = getOrCreateSheet_(ss, CONFIG.SHEET_ACTIVE, []);
  sheet.clear();
  var headers = ['Cập nhật lúc', 'Từ khóa', 'Lượt tìm kiếm', 'Chủ đề content', 'Tính chất', 'Loại xu hướng', 'Số giờ trên trending', 'Tin liên quan', 'Link'];
  var view = rows.map(function (r) { return [r[0], r[5], r[6], r[10], r[11], r[14], r[13], r[7], r[9]]; });
  sheet.getRange(1, 1, 1, headers.length).setValues([headers]).setFontWeight('bold').setBackground('#1a73e8').setFontColor('#ffffff');
  if (view.length) sheet.getRange(2, 1, view.length, headers.length).setValues(view);
  sheet.setFrozenRows(1);
  sheet.autoResizeColumns(1, headers.length);
}

function buildDashboard_(ss) {
  var sheet = getOrCreateSheet_(ss, CONFIG.SHEET_DASH, []);
  sheet.clear();
  var raw = CONFIG.SHEET_RAW;
  var rows = [
    ['VIETLIFE — DASHBOARD GOOGLE TRENDS VIỆT NAM', '', ''],
    ['Cập nhật lần cuối:', Utilities.formatDate(new Date(), CONFIG.TIMEZONE, 'dd/MM/yyyy HH:mm'), ''],
    ['', '', ''],
    ['1. PHÂN BỔ CHỦ ĐỀ HÔM NAY', 'Số chủ đề trending', ''],
    ['Sức khỏe - Y tế', '=COUNTIFS(' + raw + '!K:K,A5,' + raw + '!D:D,DAY(TODAY()),' + raw + '!C:C,MONTH(TODAY()))', '⭐ Ưu tiên content Vietlife'],
    ['Giải trí', '=COUNTIFS(' + raw + '!K:K,A6,' + raw + '!D:D,DAY(TODAY()),' + raw + '!C:C,MONTH(TODAY()))', ''],
    ['Thể thao', '=COUNTIFS(' + raw + '!K:K,A7,' + raw + '!D:D,DAY(TODAY()),' + raw + '!C:C,MONTH(TODAY()))', ''],
    ['Thời sự - Xã hội', '=COUNTIFS(' + raw + '!K:K,A8,' + raw + '!D:D,DAY(TODAY()),' + raw + '!C:C,MONTH(TODAY()))', ''],
    ['Công nghệ', '=COUNTIFS(' + raw + '!K:K,A9,' + raw + '!D:D,DAY(TODAY()),' + raw + '!C:C,MONTH(TODAY()))', ''],
    ['Giáo dục - Hữu ích', '=COUNTIFS(' + raw + '!K:K,A10,' + raw + '!D:D,DAY(TODAY()),' + raw + '!C:C,MONTH(TODAY()))', ''],
    ['Khác', '=COUNTIFS(' + raw + '!K:K,A11,' + raw + '!D:D,DAY(TODAY()),' + raw + '!C:C,MONTH(TODAY()))', ''],
    ['', '', ''],
    ['2. TOP TỪ KHÓA SỨC KHỎE - Y TẾ (30 NGÀY GẦN NHẤT)', '', ''],
    ['=IFERROR(QUERY(' + raw + '!A:O, "select F, max(N), max(G) where K = \'Sức khỏe - Y tế\' group by F order by max(N) desc limit 15 label F \'Từ khóa\', max(N) \'Số giờ trending\', max(G) \'Lượt tìm kiếm\'"), "Chưa có dữ liệu")', '', ''],
    ['', '', ''],
    ['3. XU HƯỚNG DÀI HẠN (TỒN TẠI > 7 NGÀY) — NÊN LÀM CONTENT CHUYÊN SÂU', '', ''],
    ['=IFERROR(QUERY(' + raw + '!A:O, "select F, K, max(N) where O = \'Xu hướng dài hạn\' group by F, K order by max(N) desc limit 15 label F \'Từ khóa\', K \'Chủ đề\', max(N) \'Số giờ trending\'"), "Chưa có dữ liệu")', '', ''],
    ['', '', ''],
    ['4. XU HƯỚNG NGẮN HẠN HÔM NAY — BẮT TREND NHANH (REELS/TIKTOK/POST)', '', ''],
    ['=IFERROR(QUERY(' + raw + '!A:O, "select F, K, G where O = \'Xu hướng ngắn hạn\' and D = " & DAY(TODAY()) & " and C = " & MONTH(TODAY()) & " group by F, K, G order by F limit 20 label F \'Từ khóa\', K \'Chủ đề\', G \'Lượt tìm kiếm\'"), "Chưa có dữ liệu")', '', '']
  ];
  sheet.getRange(1, 1, rows.length, 3).setValues(rows);
  sheet.getRange('A1').setFontSize(14).setFontWeight('bold').setFontColor('#1a73e8');
  sheet.getRange('A4').setFontWeight('bold').setBackground('#e8f0fe');
  sheet.getRange('A13').setFontWeight('bold').setBackground('#e8f0fe');
  sheet.getRange('A16').setFontWeight('bold').setBackground('#e8f0fe');
  sheet.getRange('A19').setFontWeight('bold').setBackground('#e8f0fe');
  sheet.autoResizeColumns(1, 3);
}

// ================== CÀI ĐẶT & TIỆN ÍCH ==================
/** Chạy hàm này MỘT LẦN để bật tự động cập nhật mỗi 1 giờ */
function setupTrigger() {
  ScriptApp.getProjectTriggers().forEach(function (t) {
    if (t.getHandlerFunction() === 'updateTrends') ScriptApp.deleteTrigger(t);
  });
  ScriptApp.newTrigger('updateTrends').timeBased().everyHours(1).create();
  updateTrends(); // chạy ngay lần đầu
  SpreadsheetApp.getActiveSpreadsheet().toast('Đã bật tự động cập nhật mỗi 1 giờ!', 'Vietlife Trends Tracker');
}

/** Menu trên thanh công cụ của Sheet */
function onOpen() {
  var menu = SpreadsheetApp.getUi()
    .createMenu('📈 Trends Tracker')
    .addItem('Cập nhật Google Trends ngay', 'updateTrends')
    .addItem('Bật tự động Google 1h/lần', 'setupTrigger');
  // Menu TikTok chỉ hiện khi đã cài thêm file TikTok-Tracker.gs
  if (typeof updateTikTokTrends === 'function') {
    menu.addSeparator()
      .addItem('Cập nhật TikTok ngay', 'updateTikTokTrends')
      .addItem('Bật tự động TikTok 6h/lần', 'setupTikTokTrigger');
  }
  menu.addToUi();
}

function getOrCreateSheet_(ss, name, headers) {
  var sheet = ss.getSheetByName(name);
  if (!sheet) {
    sheet = ss.insertSheet(name);
    if (headers && headers.length) {
      sheet.getRange(1, 1, 1, headers.length).setValues([headers]).setFontWeight('bold').setBackground('#1a73e8').setFontColor('#ffffff');
      sheet.setFrozenRows(1);
    }
  }
  return sheet;
}

function normalize_(s) {
  return String(s).toLowerCase()
    .normalize('NFD').replace(/[\u0300-\u036f]/g, '')
    .replace(/đ/g, 'd').trim();
}

function parseVNDate_(s) {
  // dạng 'yyyy-MM-dd HH:mm'
  var m = String(s).match(/(\d{4})-(\d{2})-(\d{2})[ T](\d{2}):(\d{2})/);
  if (!m) { var d = new Date(s); return isNaN(d) ? null : d; }
  return new Date(Number(m[1]), Number(m[2]) - 1, Number(m[3]), Number(m[4]), Number(m[5]));
}
