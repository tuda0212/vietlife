CREATE OR REPLACE VIEW `gen-lang-client-0738410622.marketing_data.v_report_y_te` AS
WITH
ads_daily AS (
  SELECT 
    start_date AS date, 
    specialty_code, 
    specialty_name, 
    doctor_name,
    SUM(spend) AS spend, 
    SUM(clicks) AS clicks, 
    SUM(impressions) AS impressions,
    SUM(reach) AS reach, 
    SUM(mes) AS mes, 
    SUM(cmt) AS cmt, 
    SUM(mes)+SUM(cmt) AS mes_cmt
  FROM `gen-lang-client-0738410622.marketing_data.fb_ad_insights`
  WHERE specialty_code IN ('CXK', 'TK', 'CS', 'TH')
  GROUP BY 1, 2, 3, 4
),
crm_daily AS (
  SELECT 
    lead_date AS date, 
    specialty_code, 
    specialty_name, 
    doctor_name,
    COUNT(DISTINCT phone) AS phone_count, 
    COUNTIF(is_booking=True) AS booking_count,
    COUNTIF(is_arrival=True) AS arrival_count, 
    SUM(IFNULL(revenue, 0.0)) AS revenue,
    COUNT(DISTINCT CASE WHEN revenue > 0 THEN phone END) AS customer_count
  FROM `gen-lang-client-0738410622.marketing_data.botcake_leads`
  WHERE lead_date IS NOT NULL AND report_group = 'Y tế'
  GROUP BY 1, 2, 3, 4
)
SELECT 
  COALESCE(a.date, c.date) AS date,
  COALESCE(a.specialty_code, c.specialty_code) AS specialty_code,
  COALESCE(a.specialty_name, c.specialty_name) AS specialty_name,
  COALESCE(a.doctor_name, c.doctor_name) AS doctor_name,
  IFNULL(a.spend, 0.0) AS spend, 
  IFNULL(a.clicks, 0) AS clicks, 
  IFNULL(a.impressions, 0) AS impressions,
  IFNULL(a.reach, 0) AS reach, 
  IFNULL(a.mes, 0) AS mes, 
  IFNULL(a.cmt, 0) AS cmt, 
  IFNULL(a.mes_cmt, 0) AS mes_cmt,
  IFNULL(c.phone_count, 0) AS sdts, 
  IFNULL(c.booking_count, 0) AS dat_lich, 
  IFNULL(c.arrival_count, 0) AS den_cua,
  IFNULL(c.revenue, 0.0) AS revenue, 
  IFNULL(c.customer_count, 0) AS so_khach_hang,
  ROUND(SAFE_DIVIDE(IFNULL(a.spend, 0.0), IFNULL(a.mes_cmt, 0)), 0) AS cp_mes_cmt,
  ROUND(SAFE_DIVIDE(IFNULL(a.spend, 0.0), IFNULL(a.mes, 0)), 0) AS cp_mes,
  ROUND(SAFE_DIVIDE(IFNULL(a.spend, 0.0), IFNULL(c.phone_count, 0)), 0) AS cp_lead,
  ROUND(SAFE_DIVIDE(IFNULL(a.spend, 0.0), IFNULL(a.impressions, 0)) * 1000, 0) AS cpm,
  ROUND(SAFE_DIVIDE(IFNULL(a.spend, 0.0), IFNULL(a.clicks, 0)), 0) AS cpc,
  ROUND(SAFE_DIVIDE(IFNULL(a.clicks, 0), IFNULL(a.impressions, 0)), 4) AS ctr,
  ROUND(SAFE_DIVIDE(IFNULL(c.revenue, 0.0), IFNULL(a.spend, 1.0)) * 100, 2) AS roi_percent,
  ROUND(SAFE_DIVIDE(IFNULL(c.revenue, 0.0), IFNULL(c.customer_count, 0)), 0) AS arpu
FROM ads_daily a
FULL OUTER JOIN crm_daily c ON a.date = c.date AND a.specialty_code = c.specialty_code AND a.doctor_name = c.doctor_name
ORDER BY date DESC, specialty_code, doctor_name;
