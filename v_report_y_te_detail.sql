CREATE OR REPLACE VIEW `gen-lang-client-0738410622.marketing_data.v_report_y_te_detail` AS
WITH
ads_daily AS (
  SELECT
    start_date AS date,
    ad_id,
    MAX(ad_name) AS ad_name,
    MAX(campaign_name) AS campaign_name,
    MAX(specialty_code) AS specialty_code,
    MAX(specialty_name) AS specialty_name,
    MAX(doctor_name) AS doctor_name,
    MAX(post_id) AS post_id,
    MAX(post_link) AS post_link,
    MAX(thumbnail_url) AS thumbnail_url,
    MAX(status) AS status,
    MAX(effective_status) AS effective_status,
    MAX(is_active) AS is_active,
    SUM(spend) AS spend,
    SUM(clicks) AS clicks,
    SUM(impressions) AS impressions,
    SUM(reach) AS reach,
    SUM(mes) AS mes,
    SUM(cmt) AS cmt,
    SUM(mes) + SUM(cmt) AS mes_cmt
  FROM `gen-lang-client-0738410622.marketing_data.v_fb_ads_y_te`
  GROUP BY start_date, ad_id
),
crm_daily AS (
  SELECT
    lead_date AS date,
    ad_id,
    MAX(doctor_name) AS doctor_name,
    MAX(specialty_code) AS specialty_code,
    MAX(specialty_name) AS specialty_name,
    COUNT(DISTINCT phone) AS phone_count,
    COUNTIF(is_booking = TRUE) AS booking_count,
    COUNTIF(is_arrival = TRUE) AS arrival_count,
    SUM(IFNULL(revenue, 0.0)) AS revenue,
    COUNT(DISTINCT CASE WHEN revenue > 0 THEN phone END) AS customer_count
  FROM `gen-lang-client-0738410622.marketing_data.v_crm_y_te`
  WHERE ad_id IS NOT NULL AND ad_id != ''
  GROUP BY lead_date, ad_id
),
-- Kết hợp Ads và CRM theo ad_id + date
ads_with_crm AS (
  SELECT
    COALESCE(a.date, c.date) AS date,
    COALESCE(a.ad_id, c.ad_id) AS ad_id,
    COALESCE(a.ad_name, CONCAT('Ad ID: ', c.ad_id)) AS ad_name,
    COALESCE(a.campaign_name, 'Unmapped Campaign') AS campaign_name,
    COALESCE(a.specialty_code, c.specialty_code) AS specialty_code,
    COALESCE(a.specialty_name, c.specialty_name) AS specialty_name,
    COALESCE(a.doctor_name, c.doctor_name) AS doctor_name,
    a.post_id,
    a.post_link,
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

    -- Chỉ số quảng cáo
    IFNULL(a.clicks, 0) AS clicks,
    IFNULL(a.impressions, 0) AS impressions,
    IFNULL(a.reach, 0) AS reach,
    IFNULL(a.mes, 0) AS mes,
    IFNULL(a.cmt, 0) AS cmt,
    IFNULL(a.mes_cmt, 0) AS mes_cmt,

    -- Chỉ số CRM
    IFNULL(c.phone_count, 0) AS sdts,
    IFNULL(c.booking_count, 0) AS dat_lich,
    IFNULL(c.arrival_count, 0) AS den_cua,
    IFNULL(c.customer_count, 0) AS so_khach_hang
  FROM ads_daily a
  FULL OUTER JOIN crm_daily c ON a.ad_id = c.ad_id AND a.date = c.date
),
-- CRM Y tế tự nhiên/không có ad_id
crm_organic AS (
  SELECT
    lead_date AS date,
    'organic' AS ad_id,
    'Tự nhiên / Khác' AS ad_name,
    'Organic / Không ad_id' AS campaign_name,
    specialty_code,
    specialty_name,
    doctor_name,
    CAST(NULL AS STRING) AS post_id,
    CAST(NULL AS STRING) AS post_link,
    CAST(NULL AS STRING) AS thumbnail_url,
    'TỰ NHIÊN' AS trang_thai_chay,
    CAST(NULL AS STRING) AS status,
    CAST(NULL AS STRING) AS effective_status,
    0.0 AS spend,
    SUM(IFNULL(revenue, 0.0)) AS revenue,
    0 AS clicks,
    0 AS impressions,
    0 AS reach,
    0 AS mes,
    0 AS cmt,
    0 AS mes_cmt,
    COUNT(DISTINCT phone) AS sdts,
    COUNTIF(is_booking = TRUE) AS dat_lich,
    COUNTIF(is_arrival = TRUE) AS den_cua,
    COUNT(DISTINCT CASE WHEN revenue > 0 THEN phone END) AS so_khach_hang
  FROM `gen-lang-client-0738410622.marketing_data.v_crm_y_te`
  WHERE ad_id IS NULL OR ad_id = ''
  GROUP BY lead_date, specialty_code, specialty_name, doctor_name
),
union_all AS (
  SELECT * FROM ads_with_crm
  UNION ALL
  SELECT * FROM crm_organic
)
SELECT
  u.*,
  ROUND(SAFE_DIVIDE(u.spend, u.impressions) * 1000, 0) AS cpm,
  ROUND(SAFE_DIVIDE(u.spend, u.clicks), 0) AS cpc,
  ROUND(SAFE_DIVIDE(u.clicks, u.impressions), 4) AS ctr,
  ROUND(SAFE_DIVIDE(u.spend, u.mes_cmt), 0) AS cp_mes_cmt,
  ROUND(SAFE_DIVIDE(u.spend, u.sdts), 0) AS cp_lead
FROM union_all u
ORDER BY date DESC, spend DESC;
