CREATE OR REPLACE VIEW `gen-lang-client-0738410622.marketing_data.v_report_duoc` AS
WITH
ads_daily AS (
  SELECT
    start_date AS date,
    specialty_code,
    specialty_name,
    SUM(spend) AS spend,
    SUM(clicks) AS clicks,
    SUM(impressions) AS impressions,
    SUM(reach) AS reach,
    SUM(mes) AS mes,
    SUM(cmt) AS cmt,
    SUM(mes) + SUM(cmt) AS mes_cmt
  FROM `gen-lang-client-0738410622.marketing_data.v_fb_ads_duoc`
  GROUP BY 1, 2, 3
),
crm_daily AS (
  SELECT
    lead_date AS date,
    specialty_code,
    COUNT(DISTINCT NULLIF(phone, '')) AS phone_count,
    COUNT(DISTINCT CASE WHEN revenue > 0 THEN NULLIF(phone, '') END) AS customer_count,
    SUM(IFNULL(revenue, 0)) AS revenue
  FROM `gen-lang-client-0738410622.marketing_data.v_sdt_dat_mua`
  GROUP BY 1, 2
)
SELECT
  COALESCE(a.date, c.date) AS date,
  COALESCE(a.specialty_code, c.specialty_code) AS specialty_code,
  COALESCE(a.specialty_name, CASE WHEN COALESCE(a.specialty_code, c.specialty_code) = 'BA' THEN 'Bình An' ELSE 'Vệ Tinh' END) AS specialty_name,
  
  IFNULL(a.spend, 0.0) AS spend,
  IFNULL(c.revenue, 0.0) AS revenue,
  
  -- Các chỉ số hiệu quả
  ROUND(SAFE_DIVIDE(IFNULL(a.spend, 0.0), IFNULL(a.impressions, 0)) * 1000, 0) AS cpm,
  ROUND(SAFE_DIVIDE(IFNULL(a.spend, 0.0), IFNULL(a.clicks, 0)), 0) AS cpc,
  ROUND(SAFE_DIVIDE(IFNULL(a.clicks, 0), IFNULL(a.impressions, 0)), 4) AS ctr,
  
  IFNULL(a.mes, 0) AS mes,
  IFNULL(a.cmt, 0) AS cmt,
  IFNULL(a.mes_cmt, 0) AS mes_cmt,
  
  IFNULL(c.phone_count, 0) AS sdts,
  IFNULL(c.phone_count, 0) AS leads,
  IFNULL(c.customer_count, 0) AS so_khach_hang, -- Đây là số đơn hàng
  
  ROUND(SAFE_DIVIDE(a.spend, c.phone_count), 0) AS cp_lead,
  ROUND(SAFE_DIVIDE(c.revenue, a.spend) * 100, 2) AS roi_percent,
  ROUND(SAFE_DIVIDE(c.revenue, c.customer_count), 0) AS arpu
FROM ads_daily a
FULL OUTER JOIN crm_daily c
  ON a.date = c.date
  AND a.specialty_code = c.specialty_code
ORDER BY date DESC, specialty_code;
