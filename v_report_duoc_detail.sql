CREATE OR REPLACE VIEW `gen-lang-client-0738410622.marketing_data.v_report_duoc_detail` AS
WITH ads AS (
  SELECT
    start_date AS date,
    ad_id,
    ad_name,
    campaign_name,
    specialty_code,
    specialty_name,
    doctor_name,
    thumbnail_url,
    status,
    effective_status,
    is_active,
    spend,
    mes,
    cmt,
    clicks,
    impressions,
    reach
  FROM `gen-lang-client-0738410622.marketing_data.v_fb_ads_duoc`
),
-- CRM có ad_id → gom theo ad_id + ngày
crm_with_ad AS (
  SELECT
    r.ad_id AS crm_ad_id,
    c.Ng__y_nh___p_li___u AS lead_date,
    c.S______i___n_tho___i AS sdt_val,
    c.K___t_qu____li__n_h___ AS trang_thai,
    SAFE_CAST(
      REPLACE(REPLACE(REPLACE(c.Doanh_s___, '.', ''), ' đ', ''), ',', '')
      AS FLOAT64
    ) AS revenue_val,
    CASE
      WHEN r.specialty_code IS NOT NULL THEN r.specialty_code
      WHEN c.K__nh = 'Bình an Nano' THEN 'BA'
      WHEN c.K__nh = 'Hỏi đáp đau đầu' THEN 'VT'
      ELSE 'OTHER'
    END AS specialty_code
  FROM `gen-lang-client-0738410622.marketing_data.pharmacy_revenue` c
  JOIN (
    SELECT 
      r_raw.S__T,
      MAX(r_raw.AD_ID) as ad_id,
      MAX(a.specialty_code) as specialty_code
    FROM `gen-lang-client-0738410622.marketing_data.data_fb_realtime` r_raw
    LEFT JOIN ads a 
      ON r_raw.AD_ID = a.ad_id
    WHERE r_raw.S__T IS NOT NULL AND r_raw.S__T != ''
      AND r_raw.AD_ID IS NOT NULL AND r_raw.AD_ID != ''
    GROUP BY r_raw.S__T
  ) r ON REGEXP_REPLACE(c.S______i___n_tho___i, r'\D', '') = REGEXP_REPLACE(r.S__T, r'\D', '')
  WHERE c.Ng__y_nh___p_li___u IS NOT NULL 
    AND c.S______i___n_tho___i IS NOT NULL 
    AND c.S______i___n_tho___i != ''
),
crm_agg AS (
  SELECT
    crm_ad_id,
    lead_date,
    specialty_code,
    COUNT(DISTINCT sdt_val) AS sdt_count,
    COUNT(DISTINCT CASE WHEN trang_thai = 'Đặt đơn' OR revenue_val > 0 THEN sdt_val END) AS kh_count,
    SUM(IFNULL(revenue_val, 0)) AS revenue
  FROM crm_with_ad
  GROUP BY crm_ad_id, lead_date, specialty_code
),
-- CRM không có ad_id nhưng có doanh thu → organic, ghi cho BA
crm_organic AS (
  SELECT
    c.Ng__y_nh___p_li___u AS lead_date,
    COUNT(DISTINCT c.S______i___n_tho___i) AS sdt_count,
    COUNT(DISTINCT CASE WHEN c.K___t_qu____li__n_h___ = 'Đặt đơn' OR SAFE_CAST(REPLACE(REPLACE(REPLACE(c.Doanh_s___, '.', ''), ' đ', ''), ',', '') AS FLOAT64) > 0 THEN c.S______i___n_tho___i END) AS kh_count,
    SUM(
      SAFE_CAST(
        REPLACE(REPLACE(REPLACE(c.Doanh_s___, '.', ''), ' đ', ''), ',', '')
        AS FLOAT64
      )
    ) AS revenue
  FROM `gen-lang-client-0738410622.marketing_data.pharmacy_revenue` c
  LEFT JOIN (
    SELECT DISTINCT S__T 
    FROM `gen-lang-client-0738410622.marketing_data.data_fb_realtime`
    WHERE S__T IS NOT NULL AND S__T != ''
      AND AD_ID IS NOT NULL AND AD_ID != ''
  ) r ON REGEXP_REPLACE(c.S______i___n_tho___i, r'\D', '') = REGEXP_REPLACE(r.S__T, r'\D', '')
  WHERE r.S__T IS NULL 
    AND c.Ng__y_nh___p_li___u IS NOT NULL 
    AND c.S______i___n_tho___i IS NOT NULL 
    AND c.S______i___n_tho___i != ''
    AND SAFE_CAST(REPLACE(REPLACE(REPLACE(c.Doanh_s___, '.', ''), ' đ', ''), ',', '') AS FLOAT64) > 0
  GROUP BY lead_date
),
-- Kết hợp ads + CRM có ad_id
ads_with_crm AS (
  SELECT
    COALESCE(a.date, c.lead_date) AS date,
    COALESCE(a.ad_id, c.crm_ad_id) AS ad_id,
    COALESCE(a.ad_name, CONCAT('Ad ID: ', c.crm_ad_id)) AS ad_name,
    COALESCE(a.campaign_name, 'Unmapped Campaign') AS campaign_name,
    COALESCE(a.specialty_code, c.specialty_code) AS specialty_code,
    COALESCE(a.specialty_name, 
      CASE 
        WHEN COALESCE(a.specialty_code, c.specialty_code) = 'BA' THEN 'Bình An'
        WHEN COALESCE(a.specialty_code, c.specialty_code) = 'VT' THEN 'Vệ Tinh'
        ELSE 'Khác'
      END
    ) AS specialty_name,
    a.doctor_name,
    a.thumbnail_url,
    
    -- Trạng thái bài Ads
    CASE 
      WHEN a.is_active = TRUE THEN 'ĐANG CHẠY'
      WHEN a.is_active = FALSE THEN 'ĐÃ TẮT'
      ELSE 'KHÔNG XÁC ĐỊNH'
    END AS trang_thai_chay,
    COALESCE(a.status, 'UNKNOWN') AS status,
    COALESCE(a.effective_status, 'UNKNOWN') AS effective_status,

    IFNULL(a.spend, 0.0) AS spend,
    IFNULL(c.revenue, 0.0) AS revenue,
    IFNULL(a.mes, 0) AS mess,
    IFNULL(c.sdt_count, 0) AS sdt,
    IFNULL(c.kh_count, 0) AS kh,
    
    -- Các chỉ số Ads
    IFNULL(a.clicks, 0) AS clicks,
    IFNULL(a.impressions, 0) AS impressions,
    IFNULL(a.reach, 0) AS reach,
    IFNULL(a.cmt, 0) AS cmt,
    IFNULL(a.mes, 0) + IFNULL(a.cmt, 0) AS mes_cmt
  FROM ads a
  FULL OUTER JOIN crm_agg c ON a.ad_id = c.crm_ad_id AND a.date = c.lead_date
),
-- Dòng organic (không có ad_id nhưng có doanh thu) → ghi cho BA
organic_rows AS (
  SELECT
    o.lead_date AS date,
    'organic' AS ad_id,
    'Organic' AS ad_name,
    'Organic' AS campaign_name,
    'BA' AS specialty_code,
    'Bình An' AS specialty_name,
    CAST(NULL AS STRING) AS doctor_name,
    CAST(NULL AS STRING) AS thumbnail_url,
    'TỰ NHIÊN' AS trang_thai_chay,
    CAST(NULL AS STRING) AS status,
    CAST(NULL AS STRING) AS effective_status,
    0.0 AS spend,
    IFNULL(o.revenue, 0.0) AS revenue,
    0 AS mess,
    IFNULL(o.sdt_count, 0) AS sdt,
    IFNULL(o.kh_count, 0) AS kh,
    
    -- Các chỉ số Ads bằng 0
    0 AS clicks,
    0 AS impressions,
    0 AS reach,
    0 AS cmt,
    0 AS mes_cmt
  FROM crm_organic o
),
union_all AS (
  SELECT * FROM ads_with_crm
  UNION ALL
  SELECT * FROM organic_rows
)
SELECT 
  u.*,
  ROUND(SAFE_DIVIDE(u.spend, u.impressions) * 1000, 0) AS cpm,
  ROUND(SAFE_DIVIDE(u.spend, u.clicks), 0) AS cpc,
  ROUND(SAFE_DIVIDE(u.clicks, u.impressions), 4) AS ctr,
  ROUND(SAFE_DIVIDE(u.spend, u.revenue), 2) AS spend_per_revenue,
  ROUND(SAFE_DIVIDE(u.spend, u.mess), 2) AS spend_per_mess,
  CAST(ROUND(SAFE_DIVIDE(u.spend, u.sdt), 0) AS INT64) AS spend_per_sdt,
  CAST(ROUND(SAFE_DIVIDE(u.spend, u.kh), 0) AS INT64) AS spend_per_kh
FROM union_all u
ORDER BY date DESC, spend DESC;
