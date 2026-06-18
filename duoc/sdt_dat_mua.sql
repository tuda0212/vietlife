CREATE OR REPLACE VIEW `gen-lang-client-0738410622.marketing_data.v_sdt_dat_mua` AS
SELECT 
  inserted_at,
  lead_date,
  phone,
  revenue,
  doctor_name AS product_name,
  specialty_code,
  specialty_name,
  page_id,
  ad_id,
  ad_name
FROM `gen-lang-client-0738410622.marketing_data.botcake_leads`
WHERE report_group = 'Dược Nano'
  AND phone IS NOT NULL AND phone != '';
