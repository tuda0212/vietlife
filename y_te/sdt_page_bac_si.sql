CREATE OR REPLACE VIEW `gen-lang-client-0738410622.marketing_data.v_sdt_page_bac_si` AS
SELECT 
  inserted_at,
  lead_date,
  page_id,
  doctor_name,
  specialty_code,
  specialty_name,
  subscriber_id,
  phone,
  ad_id,
  ad_name,
  conversation_id,
  note
FROM `gen-lang-client-0738410622.marketing_data.botcake_leads`
WHERE report_group = 'Y tế'
  AND phone IS NOT NULL AND phone != '';
