  WITH                                                                                                                                              
  ads_daily AS (                                                                                                                                    
    SELECT                                                                                                                                          
      start_date,                                                                                                                                   
      specialty_code,                                                                                                                               
      specialty_name,                                                                                                                               
      SUM(spend) AS spend,                                                                                                                          
      SUM(clicks) AS clicks,                                                                                                                        
      SUM(impressions) AS impressions,                                                                                                              
      SUM(reach) AS reach,                                                                                                                          
      SUM(mes) AS mes,                                                                                                                              
      SUM(cmt) AS cmt,                                                                                                                              
      SUM(mes) + SUM(cmt) AS mes_cmt                                                                                                                
    FROM `gen-lang-client-0738410622.marketing_data.fb_ad_insights`                                                                                 
    WHERE specialty_code IN ('VT', 'BA')                                                                                                            
    GROUP BY 1, 2, 3                                                                                                                                
  ),                                                                                                                                                
  crm_daily AS (                                                                                                                                    
    SELECT                                                                                                                                          
      lead_date,                                                                                                                                    
      specialty_code,                                                                                                                               
      COUNT(DISTINCT NULLIF(phone, '')) AS phone_count,                                                                                             
      COUNT(DISTINCT CASE WHEN revenue > 0 THEN NULLIF(phone, '') END) AS customer_count,                                                           
      SUM(IFNULL(revenue, 0)) AS revenue                                                                                                            
    FROM `gen-lang-client-0738410622.marketing_data.botcake_leads`                                                                                  
    WHERE lead_date IS NOT NULL                                                                                                                     
      AND specialty_code IN ('VT', 'BA')                                                                                                            
    GROUP BY 1, 2                                                                                                                                   
  )                                                                                                                                                 
  SELECT                                                                                                                                            
    COALESCE(a.start_date, c.lead_date) AS date,                                                                                                    
    COALESCE(a.specialty_code, c.specialty_code) AS specialty_code,                                                                                 
    COALESCE(a.specialty_name, CASE WHEN COALESCE(a.specialty_code, c.specialty_code) = 'BA' THEN 'Bình An' ELSE 'Vệ Tinh' END) AS specialty_name,  
    IFNULL(a.spend, 0) AS spend,                                                                                                                    
    IFNULL(a.clicks, 0) AS clicks,                                                                                                                  
    IFNULL(a.impressions, 0) AS impressions,                                                                                                        
    IFNULL(a.reach, 0) AS reach,                                                                                                                    
    IFNULL(a.mes, 0) AS mes,                                                                                                                        
    IFNULL(a.cmt, 0) AS cmt,                                                                                                                        
    IFNULL(a.mes_cmt, 0) AS mes_cmt,                                                                                                                
    IFNULL(c.phone_count, 0) AS sdts,                                                                                                               
    IFNULL(c.phone_count, 0) AS leads,                                                                                                              
    IFNULL(c.customer_count, 0) AS so_khach_hang,                                                                                                   
    IFNULL(c.revenue, 0) AS revenue,                                                                                                                
    ROUND(SAFE_DIVIDE(a.spend, c.phone_count), 0) AS cp_lead,                                                                                       
    ROUND(SAFE_DIVIDE(c.revenue, a.spend) * 100, 2) AS roi_percent,                                                                                 
    ROUND(SAFE_DIVIDE(c.revenue, c.customer_count), 0) AS arpu                                                                                      
  FROM ads_daily a                                                                                                                                  
  FULL OUTER JOIN crm_daily c                                                                                                                       
    ON a.start_date = c.lead_date                                                                                                                   
    AND a.specialty_code = c.specialty_code                                                                                                         
  ORDER BY date DESC, specialty_code
