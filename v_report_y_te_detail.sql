CREATE OR REPLACE VIEW `gen-lang-client-0738410622.marketing_data.v_report_y_te_detail` AS
WITH

-- B1: Lấy thông tin metadata duy nhất của từng ad_id từ Facebook Ads
ad_meta AS (
  SELECT
    ad_id,
    MAX(ad_name)                                AS ad_name,
    MAX(campaign_name)                          AS campaign_name,
    MAX(post_id)                                AS post_id,
    MAX(post_link)                              AS post_link,
    MAX(thumbnail_url)                          AS thumbnail_url,
    MAX(specialty_code)                         AS ad_specialty_code,
    MAX(specialty_name)                         AS ad_specialty_name
  FROM `gen-lang-client-0738410622.marketing_data.fb_ad_insights`
  GROUP BY ad_id
)

-- B2: Lấy chi tiết từng lead và JOIN với thông tin quảng cáo tương ứng
SELECT
  c.lead_date,
  c.phone,
  c.subscriber_id,
  c.doctor_name,
  c.specialty_code,
  c.specialty_name,
  c.booking_status,
  c.arrival_status,
  c.is_booking,
  c.is_arrival,
  c.revenue,
  c.page_id,
  
  -- Thông tin bài quảng cáo ghép nối được
  c.ad_id,
  CASE 
    WHEN c.ad_id IS NULL OR c.ad_id = '' THEN 'TỰ NHIÊN / KHÁC'
    ELSE COALESCE(a.ad_name, 'AD CHƯA ĐỒNG BỘ / KHÁC')
  END                                           AS ad_name,
  a.campaign_name,
  a.post_id,
  a.post_link,
  a.thumbnail_url

FROM `gen-lang-client-0738410622.marketing_data.botcake_leads` c
LEFT JOIN ad_meta a
  ON c.ad_id = a.ad_id
WHERE c.lead_date IS NOT NULL
  AND c.report_group = 'Y tế'
