CREATE OR REPLACE VIEW `gen-lang-client-0738410622.marketing_data.v_report` AS
WITH

-- B1: Gom nhiều ad cùng bài post lại thành từng dòng theo ngày
post_metrics AS (
  SELECT
    start_date,
    end_date,
    specialty_code,
    specialty_name,
    doctor_name,
    post_id,
    post_link,
    MAX(thumbnail_url)                                          AS thumbnail_url,
    STRING_AGG(DISTINCT campaign_name, ', ')                    AS campaign_names,
    STRING_AGG(DISTINCT ad_id, ', ')                            AS ad_ids,
    STRING_AGG(DISTINCT ad_name, ', ')                          AS ad_names,
    STRING_AGG(DISTINCT content, ' | ')                         AS content,

    CASE WHEN COUNTIF(is_active = TRUE) > 0
         THEN 'ĐANG BẬT' ELSE 'ĐANG TẮT' END                  AS post_status,

    COUNTIF(is_active = TRUE)                                   AS active_ads,
    COUNTIF(is_active = FALSE)                                  AS paused_ads,
    COUNT(*)                                                    AS total_ads,

    ROUND(SUM(spend), 0)                                        AS spend,
    SUM(mes)                                                    AS mes,
    SUM(cmt)                                                    AS cmt,
    SUM(mes) + SUM(cmt)                                         AS mes_cmt,
    SUM(clicks)                                                 AS clicks,
    SUM(impressions)                                            AS impressions,
    SUM(reach)                                                  AS reach,

    SUM(video_views)                                            AS video_views,
    SUM(video_25)                                               AS video_25,
    SUM(video_50)                                               AS video_50,
    SUM(video_75)                                               AS video_75,
    SUM(video_95)                                               AS video_95,
    SUM(video_100)                                              AS video_100,
    SUM(thruplay)                                               AS thruplay,

    STRING_AGG(DISTINCT status, ', ')                           AS ad_status,
    STRING_AGG(DISTINCT effective_status, ', ')                 AS effective_status

  FROM `gen-lang-client-0738410622.marketing_data.fb_ad_insights`
  WHERE spend > 0
  GROUP BY 1,2,3,4,5,6,7
),

-- B2: Gom CRM theo ad_id và lead_date (bổ sung lead_date, revenue, so_khach_hang)
crm_per_ad AS (
  SELECT
    ad_id,
    lead_date,
    COUNT(DISTINCT phone)                               AS phone_count,
    COUNTIF(is_booking = TRUE)                          AS booking_count,
    COUNTIF(is_arrival = TRUE)                          AS arrival_count,
    SUM(IFNULL(revenue, 0.0))                           AS total_revenue,
    COUNT(DISTINCT CASE WHEN revenue > 0 THEN phone END) AS customer_count
  FROM `gen-lang-client-0738410622.marketing_data.botcake_leads`
  WHERE lead_date IS NOT NULL
  GROUP BY ad_id, lead_date
),

-- B3: Ghép CRM vào từng post theo ngày (JOIN bằng cả ad_id và so khớp date)
crm_per_post AS (
  SELECT
    p.start_date,
    p.end_date,
    p.specialty_code,
    p.specialty_name,
    p.doctor_name,
    p.post_id,
    SUM(IFNULL(c.phone_count, 0))       AS sdts,
    SUM(IFNULL(c.booking_count, 0))     AS dat_lich,
    SUM(IFNULL(c.arrival_count, 0))     AS den_cua,
    SUM(IFNULL(c.total_revenue, 0.0))   AS revenue,
    SUM(IFNULL(c.customer_count, 0))    AS so_khach_hang
  FROM post_metrics p
  CROSS JOIN UNNEST(SPLIT(p.ad_ids, ', ')) AS ad_id
  LEFT JOIN crm_per_ad c 
    ON TRIM(ad_id) = c.ad_id
    AND c.lead_date BETWEEN p.start_date AND p.end_date
  GROUP BY 1,2,3,4,5,6
),

-- Portion 1: Kết quả ghép Ads + CRM (Có quảng cáo phát sinh spend)
portion_ads AS (
  SELECT
    p.start_date,
    p.end_date,
    p.doctor_name,
    p.specialty_name,
    p.specialty_code,
    p.post_status,
    p.post_id,
    p.post_link,
    p.thumbnail_url,
    p.campaign_names,
    p.ad_ids,

    cr.sdts,
    cr.dat_lich,
    cr.den_cua,
    cr.revenue,
    cr.so_khach_hang,

    p.ad_names,
    p.content,
    p.active_ads,
    p.paused_ads,
    p.total_ads,

    p.spend,
    p.mes,
    p.cmt,
    p.mes_cmt,
    p.clicks,
    p.impressions,
    p.reach,
    p.video_views,
    p.video_25,
    p.video_50,
    p.video_75,
    p.video_95,
    p.video_100,
    p.thruplay,
    p.ad_status,
    p.effective_status
  FROM post_metrics p
  LEFT JOIN crm_per_post cr
    ON  p.post_id       = cr.post_id
    AND p.start_date    = cr.start_date
    AND p.end_date      = cr.end_date
    AND p.specialty_code = cr.specialty_code
    AND p.doctor_name   = cr.doctor_name
),

-- B4: Lấy danh sách ad_id + ngày đã được map trong portion_ads
mapped_leads AS (
  SELECT DISTINCT TRIM(ad_id) AS ad_id, start_date AS lead_date
  FROM post_metrics p
  CROSS JOIN UNNEST(SPLIT(p.ad_ids, ', ')) AS ad_id
),

-- Portion 2: Gom CRM chưa được map (Tự nhiên hoặc Ad không chạy trong ngày đó)
portion_crm_unmapped AS (
  SELECT
    c.lead_date                          AS start_date,
    c.lead_date                          AS end_date,
    c.doctor_name,
    c.specialty_name,
    c.specialty_code,
    'TỰ NHIÊN / KHÁC'                    AS post_status,
    CAST(NULL AS STRING)                 AS post_id,
    CAST(NULL AS STRING)                 AS post_link,
    CAST(NULL AS STRING)                 AS thumbnail_url,
    CAST(NULL AS STRING)                 AS campaign_names,
    CAST(NULL AS STRING)                 AS ad_ids,

    COUNT(DISTINCT c.phone)              AS sdts,
    COUNTIF(c.is_booking = TRUE)         AS dat_lich,
    COUNTIF(c.is_arrival = TRUE)         AS den_cua,
    SUM(IFNULL(c.revenue, 0.0))          AS revenue,
    COUNT(DISTINCT CASE WHEN c.revenue > 0 THEN c.phone END) AS so_khach_hang,

    CAST(NULL AS STRING)                 AS ad_names,
    CAST(NULL AS STRING)                 AS content,
    0                                    AS active_ads,
    0                                    AS paused_ads,
    0                                    AS total_ads,

    0.0                                  AS spend,
    0                                    AS mes,
    0                                    AS cmt,
    0                                    AS mes_cmt,
    0                                    AS clicks,
    0                                    AS impressions,
    0                                    AS reach,
    0                                    AS video_views,
    0                                    AS video_25,
    0                                    AS video_50,
    0                                    AS video_75,
    0                                    AS video_95,
    0                                    AS video_100,
    0                                    AS thruplay,
    CAST(NULL AS STRING)                 AS ad_status,
    CAST(NULL AS STRING)                 AS effective_status
  FROM `gen-lang-client-0738410622.marketing_data.botcake_leads` c
  LEFT JOIN mapped_leads m
    ON c.ad_id = m.ad_id
    AND c.lead_date = m.lead_date
  WHERE m.ad_id IS NULL -- Chỉ lấy những leads chưa được map ở Portion 1
    AND c.lead_date IS NOT NULL
  GROUP BY 1,2,3,4,5,6
),

-- B5: UNION cả 2 portion
union_all AS (
  SELECT * FROM portion_ads
  UNION ALL
  SELECT * FROM portion_crm_unmapped
)

-- B6: Final select kèm tính toán tỷ lệ trên dòng
SELECT
  u.*,
  ROUND(SAFE_DIVIDE(u.spend, u.mes_cmt), 0)              AS cp_mes_cmt,
  ROUND(SAFE_DIVIDE(u.spend, u.mes), 0)                  AS cp_mes,
  ROUND(SAFE_DIVIDE(u.spend, u.impressions) * 1000, 0)   AS cpm,
  ROUND(SAFE_DIVIDE(u.spend, u.clicks), 0)               AS cpc,
  ROUND(SAFE_DIVIDE(u.clicks, u.impressions), 4)         AS ctr,
  ROUND(SAFE_DIVIDE(u.video_25, u.video_views), 4)       AS rate_25,
  ROUND(SAFE_DIVIDE(u.video_50, u.video_views), 4)       AS rate_50,
  ROUND(SAFE_DIVIDE(u.video_75, u.video_views), 4)       AS rate_75,
  ROUND(SAFE_DIVIDE(u.video_95, u.video_views), 4)       AS rate_95,
  ROUND(SAFE_DIVIDE(u.video_100, u.video_views), 4)      AS rate_100,
  ROUND(SAFE_DIVIDE(u.thruplay, u.video_views), 4)       AS rate_thruplay,
  ROUND(SAFE_DIVIDE(u.revenue, u.so_khach_hang), 0)      AS arpu
FROM union_all u
