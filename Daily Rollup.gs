// =====================================================================
// 📊 DAILY ROLLUP – Tổng hợp theo NGÀY (đầy đủ chỉ số phễu)
// ---------------------------------------------------------------------
// Lark dashboard KHÔNG có "chỉ số tính toán" => không tự chia được.
// Hàm này tính sẵn TẤT CẢ tỷ lệ ở cấp độ TỪNG NGÀY rồi đẩy sang bảng
// "Tổng hợp theo ngày". Mỗi dòng = 1 ngày nên mọi tỷ lệ là ratio-of-sums
// hợp lệ; dashboard chỉ đọc, không chia/không Average => luôn đúng.
//
// NGUỒN DỮ LIỆU (gom theo ngày):
//   • Bảng ADS  -> Tổng Chi Tiêu (Chi phí), Mess (Mes)   theo cột "Ngày" (ngày chạy ad)
//   • Bảng CRM  -> Tổng Doanh Thu (THÀNH TIỀN), SĐT, Số KH theo "NGÀY ĐĂNG KÝ"
//
// ĐỊNH NGHĨA (đã chốt):
//   • SĐT     = số bản ghi CRM có SDT CHUẨN không rỗng
//   • Số KH   = số bản ghi CRM có THÀNH TIỀN > 0 (khách đã mua)
//   • % Chi/Thu = Tổng Chi Tiêu / Tổng Doanh Thu
//   • SĐT/Mess  = SĐT / Mess
//   • KH/SĐT    = Số KH / SĐT
//   • TB Đơn/KH = Tổng Doanh Thu / Số KH
//
// Dùng chung helper + FUSION_CONFIG với file "ROI V2.gs"
// (phải dán file này CÙNG project Apps Script với ROI V2.gs).
// =====================================================================

// ⚙️ CẤU HÌNH BẢNG "TỔNG HỢP THEO NGÀY"
const TABLE_DAILY = "PASTE_TABLE_ID_HERE";   // <-- DÁN Table ID bảng ngày vào đây

// --- Tên cột bảng NGÀY (phải KHỚP TUYỆT ĐỐI với Lark) ---
const FLD_DAILY_DATE       = "Ngày";
const FLD_DAILY_SPEND      = "Tổng Chi Tiêu";
const FLD_DAILY_REVENUE    = "Tổng Doanh Thu";
const FLD_DAILY_PHONE      = "SĐT";
const FLD_DAILY_MESS       = "Mess";
const FLD_DAILY_CUST       = "Số KH";
const FLD_DAILY_RATIO      = "% Chi/Thu";     // thập phân -> format cột dạng %
const FLD_DAILY_PHONE_MESS = "SĐT/Mess";      // thập phân -> format cột dạng %
const FLD_DAILY_CUST_PHONE = "KH/SĐT";        // thập phân -> format cột dạng %
const FLD_DAILY_AOV        = "TB Đơn/KH";     // tiền VNĐ

// --- Tên cột nguồn (khớp với CONFIG/ROI V2.gs) ---
const FLD_ADS_MESS = "Mes";          // bảng ADS: số tin nhắn
const FLD_KH_PHONE = "SDT CHUẨN";    // bảng CRM: số điện thoại
// (FLD_ADS_DATE, FLD_SPEND_ADS, FLD_KH_DATE, FLD_REVENUE_KH đã khai báo ở ROI V2.gs)

// =====================================================================
// 🚀 HÀM CHÍNH – gọi sau runTableFusion() trong luồng chạy hàng giờ
// =====================================================================
function syncDailyRollup() {
  Logger.log("📊 BẮT ĐẦU DAILY ROLLUP (tổng hợp theo ngày)...");

  if (!TABLE_DAILY || TABLE_DAILY.indexOf("PASTE") === 0) {
    return Logger.log("❌ Chưa cấu hình TABLE_DAILY. Tạo bảng ngày trong Lark rồi dán Table ID.");
  }

  const token = getTenantAccessToken();
  if (!token) return Logger.log("❌ Daily rollup: không lấy được token Lark.");

  let byDay = {};   // { "yyyy-MM-dd": { chi, mess, thu, sdt, kh } }
  function dayBucket(dk) {
    if (!byDay[dk]) byDay[dk] = { chi: 0, mess: 0, thu: 0, sdt: 0, kh: 0 };
    return byDay[dk];
  }

  // 1) ADS -> Chi phí + Mess theo "Ngày" (ngày chạy ad)
  const adsRecords = fetchAllRecords(FUSION_CONFIG.TABLE_ADS, token);
  Logger.log(`⏳ ADS: ${adsRecords.length} dòng.`);
  adsRecords.forEach(r => {
    let f = r.fields || {};
    let dk = extractDateKey(f[FLD_ADS_DATE]);
    if (!dk) return;
    let b = dayBucket(dk);
    b.chi  += extractNumber(f[FLD_SPEND_ADS]);
    b.mess += extractNumber(f[FLD_ADS_MESS]);
  });

  // 2) CRM -> Doanh thu + SĐT + Số KH theo "NGÀY ĐĂNG KÝ"
  const khRecords = fetchAllRecords(FUSION_CONFIG.TABLE_KH, token);
  Logger.log(`⏳ CRM: ${khRecords.length} dòng.`);
  khRecords.forEach(r => {
    let f = r.fields || {};
    let dk = extractDateKey(f[FLD_KH_DATE]);
    if (!dk) return;
    let b = dayBucket(dk);
    let rev = extractNumber(f[FLD_REVENUE_KH]);
    b.thu += rev;
    if (extractText(f[FLD_KH_PHONE]) !== "") b.sdt += 1;   // SĐT: có số điện thoại
    if (rev > 0) b.kh += 1;                                // Số KH: đã mua
  });

  // 3) Map ngày -> record_id đã có (để upsert)
  const dailyRecords = fetchAllRecords(TABLE_DAILY, token);
  let dayMap = {};
  dailyRecords.forEach(r => {
    let dk = extractDateKey((r.fields || {})[FLD_DAILY_DATE]);
    if (dk) dayMap[dk] = r.record_id;
  });

  // 4) Dựng danh sách thêm mới / cập nhật
  let toAdd = [], toUpdate = [];
  for (let dk in byDay) {
    let d = byDay[dk];
    let fields = {};
    fields[FLD_DAILY_DATE]    = new Date(dk + "T00:00:00+07:00").getTime();
    fields[FLD_DAILY_SPEND]   = d.chi;
    fields[FLD_DAILY_REVENUE] = d.thu;
    fields[FLD_DAILY_PHONE]   = d.sdt;
    fields[FLD_DAILY_MESS]    = d.mess;
    fields[FLD_DAILY_CUST]    = d.kh;

    // Tỷ lệ: chỉ ghi khi mẫu số > 0, tránh hiểu nhầm 0%
    if (d.thu  > 0) fields[FLD_DAILY_RATIO]      = d.chi / d.thu;   // % Chi/Thu
    if (d.mess > 0) fields[FLD_DAILY_PHONE_MESS] = d.sdt / d.mess;  // SĐT/Mess
    if (d.sdt  > 0) fields[FLD_DAILY_CUST_PHONE] = d.kh  / d.sdt;   // KH/SĐT
    if (d.kh   > 0) fields[FLD_DAILY_AOV]        = d.thu / d.kh;    // TB Đơn/KH

    if (dayMap[dk]) toUpdate.push({ record_id: dayMap[dk], fields: fields });
    else            toAdd.push({ fields: fields });
  }

  // 5) Đẩy lên Lark
  if (toAdd.length > 0) {
    Logger.log(`🚀 Thêm mới ${toAdd.length} ngày...`);
    chunkAndSend(TABLE_DAILY, toAdd, "batch_create", token);
  }
  if (toUpdate.length > 0) {
    Logger.log(`🔄 Cập nhật ${toUpdate.length} ngày...`);
    chunkAndSend(TABLE_DAILY, toUpdate, "batch_update", token);
  }

  Logger.log(`✅ DAILY ROLLUP XONG: thêm ${toAdd.length}, cập nhật ${toUpdate.length} ngày.`);
}

// =====================================================================
// 🐞 HÀM DEBUG – chạy riêng để soi lỗi nếu bảng ngày không lên data.
// Chọn hàm "debugDailyRollup" -> Run -> mở Execution log -> gửi mình log.
// =====================================================================
function debugDailyRollup() {
  Logger.log("===== DEBUG DAILY ROLLUP =====");
  Logger.log("1) TABLE_DAILY = '" + TABLE_DAILY + "'");
  if (!TABLE_DAILY || TABLE_DAILY.indexOf("PASTE") === 0) {
    return Logger.log("❌ DỪNG: Chưa dán Table ID bảng ngày vào TABLE_DAILY.");
  }

  const token = getTenantAccessToken();
  Logger.log("2) Token: " + (token ? "OK" : "❌ KHÔNG LẤY ĐƯỢC"));
  if (!token) return;

  const adsRecords = fetchAllRecords(FUSION_CONFIG.TABLE_ADS, token);
  const khRecords  = fetchAllRecords(FUSION_CONFIG.TABLE_KH, token);
  Logger.log("3) ADS: " + adsRecords.length + " dòng | CRM: " + khRecords.length + " dòng.");
  if (adsRecords.length > 0) Logger.log("   Cột ADS: " + JSON.stringify(Object.keys(adsRecords[0].fields || {})));
  if (khRecords.length  > 0) Logger.log("   Cột CRM: " + JSON.stringify(Object.keys(khRecords[0].fields || {})));

  // Gom thử 1 ngày
  let byDay = {};
  adsRecords.forEach(r => {
    let f = r.fields || {}; let dk = extractDateKey(f[FLD_ADS_DATE]); if (!dk) return;
    if (!byDay[dk]) byDay[dk] = { chi:0, mess:0, thu:0, sdt:0, kh:0 };
    byDay[dk].chi += extractNumber(f[FLD_SPEND_ADS]);
    byDay[dk].mess += extractNumber(f[FLD_ADS_MESS]);
  });
  khRecords.forEach(r => {
    let f = r.fields || {}; let dk = extractDateKey(f[FLD_KH_DATE]); if (!dk) return;
    if (!byDay[dk]) byDay[dk] = { chi:0, mess:0, thu:0, sdt:0, kh:0 };
    let rev = extractNumber(f[FLD_REVENUE_KH]);
    byDay[dk].thu += rev;
    if (extractText(f[FLD_KH_PHONE]) !== "") byDay[dk].sdt += 1;
    if (rev > 0) byDay[dk].kh += 1;
  });
  let days = Object.keys(byDay);
  Logger.log("4) Số NGÀY gom được: " + days.length);
  if (days.length === 0) return Logger.log("❌ DỪNG: Không gom được ngày. Kiểm tra tên cột ngày ở ADS/CRM.");
  Logger.log("   Ví dụ: " + days[0] + " => " + JSON.stringify(byDay[days[0]]));

  // Ghi thử 1 dòng, in nguyên văn phản hồi Lark
  let dk = days[0], d = byDay[dk];
  let fields = {};
  fields[FLD_DAILY_DATE]    = new Date(dk + "T00:00:00+07:00").getTime();
  fields[FLD_DAILY_SPEND]   = d.chi;
  fields[FLD_DAILY_REVENUE] = d.thu;
  fields[FLD_DAILY_PHONE]   = d.sdt;
  fields[FLD_DAILY_MESS]    = d.mess;
  fields[FLD_DAILY_CUST]    = d.kh;
  if (d.thu  > 0) fields[FLD_DAILY_RATIO]      = d.chi / d.thu;
  if (d.mess > 0) fields[FLD_DAILY_PHONE_MESS] = d.sdt / d.mess;
  if (d.sdt  > 0) fields[FLD_DAILY_CUST_PHONE] = d.kh  / d.sdt;
  if (d.kh   > 0) fields[FLD_DAILY_AOV]        = d.thu / d.kh;

  let url = `https://open.larksuite.com/open-apis/bitable/v1/apps/${FUSION_CONFIG.BASE_TOKEN}/tables/${TABLE_DAILY}/records/batch_create`;
  let res = UrlFetchApp.fetch(url, {
    method: "post",
    headers: { "Authorization": "Bearer " + token },
    contentType: "application/json",
    payload: JSON.stringify({ records: [{ fields: fields }] }),
    muteHttpExceptions: true
  });
  Logger.log("5) PHẢN HỒI TỪ LARK khi ghi thử:");
  Logger.log(res.getContentText());
  Logger.log("===== HẾT DEBUG =====");
}
