CREATE OR REPLACE VIEW `gen-lang-client-0738410622.marketing_data.v_crm_y_te` AS
SELECT 
  inserted_at,
  lead_date,
  lead_date AS ngay,
  phone,
  booking_status,
  arrival_status,
  is_booking,
  is_arrival,
  revenue,
  doctor_name,
  specialty_code,
  specialty_name,
  page_id,
  ad_id,
  ad_name,
  subscriber_id,
  conversation_id,
  note
FROM `gen-lang-client-0738410622.marketing_data.botcake_leads`
WHERE report_group = 'Y tế'
  AND phone IS NOT NULL AND phone != '';
