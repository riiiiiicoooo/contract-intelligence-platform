/**
 * Seed Data for Contract Intelligence Platform
 *
 * Populates database with sample M&A deal:
 * - 1 tenant (Alpine Capital Partners)
 * - 2 users (Partner and Associate)
 * - 1 deal (Project Atlas - Acme Corp Acquisition)
 * - 5 contracts (MSA, SOW, NDA, Vendor Agreement, Real Estate Lease)
 * - 50 extracted clauses
 * - 10 risk flags
 *
 * This seed data tells a coherent story about an M&A due diligence scenario.
 */

-- ============================================================================
-- TENANTS
-- ============================================================================

INSERT INTO tenants (id, name, slug, settings, data_residency)
VALUES (
  'f0f0f0f0-f0f0-f0f0-f0f0-f0f0f0f0f0f0'::uuid,
  'Alpine Capital Partners',
  'alpine-capital',
  '{
    "default_playbook_id": "pb_mna_001",
    "max_file_size_mb": 500,
    "allowed_export_formats": ["excel", "pptx", "pdf"],
    "require_partner_approval": true,
    "auto_approve_confidence_threshold": 0.90
  }'::jsonb,
  'us-east-1'
);


-- ============================================================================
-- USERS
-- ============================================================================

INSERT INTO users (id, tenant_id, email, full_name, role, is_active)
VALUES
  ('u1111111-1111-1111-1111-111111111111'::uuid, 'f0f0f0f0-f0f0-f0f0-f0f0-f0f0f0f0f0f0', 'james.partner@alpine.com', 'James Chen', 'partner', true),
  ('u2222222-2222-2222-2222-222222222222'::uuid, 'f0f0f0f0-f0f0-f0f0-f0f0-f0f0f0f0f0f0', 'sarah.associate@alpine.com', 'Sarah Davis', 'senior_associate', true);


-- ============================================================================
-- PLAYBOOK (Deal-type specific rules)
-- ============================================================================

INSERT INTO playbooks (id, tenant_id, name, description, deal_type, rules, is_default, created_by)
VALUES (
  'pb_mna_001'::uuid,
  'f0f0f0f0-f0f0-f0f0-f0f0-f0f0f0f0f0f0',
  'M&A Due Diligence - Standard Rules',
  'Default playbook for M&A transactions with focus on change of control and termination rights',
  'm_and_a',
  '[
    {
      "rule_id": "COC-001",
      "clause_type": "change_of_control",
      "condition": "notice_period_days < 60",
      "severity": "critical",
      "message": "Change of control notice period below 60 days is non-standard for M&A"
    },
    {
      "rule_id": "COC-002",
      "clause_type": "change_of_control",
      "condition": "requires_consent == false",
      "severity": "high",
      "message": "Change of control allows unilateral termination - flag for negotiation"
    },
    {
      "rule_id": "LOL-001",
      "clause_type": "limitation_of_liability",
      "condition": "is_capped == false",
      "severity": "critical",
      "message": "Uncapped liability exposure"
    },
    {
      "rule_id": "AUTO-001",
      "clause_type": "auto_renewal",
      "condition": "is_present && notice_period_days < 90",
      "severity": "high",
      "message": "Auto-renewal trap: difficult exit"
    }
  ]'::jsonb,
  true,
  'u1111111-1111-1111-1111-111111111111'::uuid
);


-- ============================================================================
-- DEALS
-- ============================================================================

INSERT INTO deals (id, tenant_id, name, deal_type, status, target_company, deal_value_range, playbook_id, assigned_partner, metadata)
VALUES (
  'd_atlas_001'::uuid,
  'f0f0f0f0-f0f0-f0f0-f0f0-f0f0f0f0f0f0',
  'Project Atlas - Acme Corp Acquisition',
  'm_and_a',
  'reviewing',
  'Acme Corporation',
  '$150M-$200M',
  'pb_mna_001'::uuid,
  'u1111111-1111-1111-1111-111111111111'::uuid,
  '{
    "client_name": "Alpine Capital Partners",
    "industry": "Software & Technology",
    "expected_close_date": "2025-03-15",
    "contract_count_estimate": 250,
    "notes": "Focus on change-of-control and assignment provisions across vendor ecosystem"
  }'::jsonb
);


-- ============================================================================
-- CONTRACTS
-- ============================================================================

INSERT INTO contracts (
  id, deal_id, tenant_id, filename, original_filename, file_path, file_hash,
  file_size_bytes, mime_type, contract_type, parties, effective_date, expiration_date,
  governing_law, page_count, is_scanned, processing_status, processed_at
) VALUES
  (
    'c_msa_001'::uuid, 'd_atlas_001'::uuid, 'f0f0f0f0-f0f0-f0f0-f0f0-f0f0f0f0f0f0',
    'Master_Service_Agreement_Acme_2024.pdf', 'Master_Service_Agreement_Acme_2024.pdf',
    'contracts/c_msa_001.pdf', 'sha256:abc123def456',
    245678, 'application/pdf', 'msa',
    '[{"name": "Acme Corporation", "role": "vendor"}, {"name": "Target Corp", "role": "client"}]'::jsonb,
    '2024-03-01', '2027-02-28', 'Delaware', 42, false, 'reviewed',
    '2025-01-12T14:30:00Z'
  ),
  (
    'c_sow_001'::uuid, 'd_atlas_001'::uuid, 'f0f0f0f0-f0f0-f0f0-f0f0-f0f0f0f0f0f0',
    'Statement_of_Work_2024_Q1_Q2.pdf', 'Statement_of_Work_2024_Q1_Q2.pdf',
    'contracts/c_sow_001.pdf', 'sha256:def789ghi012',
    156234, 'application/pdf', 'sow',
    '[{"name": "Acme Corporation", "role": "vendor"}, {"name": "Target Corp", "role": "client"}]'::jsonb,
    '2024-01-01', '2024-06-30', 'New York', 28, false, 'reviewed',
    '2025-01-12T14:35:00Z'
  ),
  (
    'c_nda_001'::uuid, 'd_atlas_001'::uuid, 'f0f0f0f0-f0f0-f0f0-f0f0-f0f0f0f0f0f0',
    'NDA_Mutual_Standard.pdf', 'NDA_Mutual_Standard.pdf',
    'contracts/c_nda_001.pdf', 'sha256:ghi345jkl678',
    89234, 'application/pdf', 'nda',
    '[{"name": "Acme Corporation"}, {"name": "Various Partners"}]'::jsonb,
    '2023-01-01', '2025-12-31', 'Delaware', 8, false, 'reviewed',
    '2025-01-12T14:40:00Z'
  ),
  (
    'c_vendor_001'::uuid, 'd_atlas_001'::uuid, 'f0f0f0f0-f0f0-f0f0-f0f0-f0f0f0f0f0f0',
    'Vendor_Agreement_IT_Services.pdf', 'Vendor_Agreement_IT_Services.pdf',
    'contracts/c_vendor_001.pdf', 'sha256:jkl901mno234',
    112456, 'application/pdf', 'vendor',
    '[{"name": "Acme Corporation", "role": "buyer"}, {"name": "CloudTech Solutions", "role": "vendor"}]'::jsonb,
    '2023-06-01', '2025-05-31', 'Delaware', 15, false, 'review_pending',
    '2025-01-12T14:45:00Z'
  ),
  (
    'c_lease_001'::uuid, 'd_atlas_001'::uuid, 'f0f0f0f0-f0f0-f0f0-f0f0-f0f0f0f0f0f0',
    'Real_Estate_Lease_HQ.pdf', 'Real_Estate_Lease_HQ.pdf',
    'contracts/c_lease_001.pdf', 'sha256:mno567pqr890',
    324567, 'application/pdf', 'lease',
    '[{"name": "Property Management LLC", "role": "landlord"}, {"name": "Acme Corporation", "role": "tenant"}]'::jsonb,
    '2020-01-15', '2030-01-14', 'California', 35, false, 'extracted',
    '2025-01-12T14:50:00Z'
  );


-- ============================================================================
-- CONTRACT PARTIES (Additional party metadata)
-- ============================================================================

INSERT INTO contract_parties (contract_id, tenant_id, party_name, party_role, entity_type, jurisdiction, normalized_name)
VALUES
  ('c_msa_001'::uuid, 'f0f0f0f0-f0f0-f0f0-f0f0-f0f0f0f0f0f0', 'Acme Corporation', 'vendor', 'corporation', 'Delaware', 'acme_corporation'),
  ('c_msa_001'::uuid, 'f0f0f0f0-f0f0-f0f0-f0f0-f0f0f0f0f0f0', 'Target Corp', 'client', 'corporation', 'Delaware', 'target_corp'),
  ('c_vendor_001'::uuid, 'f0f0f0f0-f0f0-f0f0-f0f0-f0f0f0f0f0f0', 'CloudTech Solutions', 'vendor', 'corporation', 'California', 'cloudtech_solutions');


-- ============================================================================
-- CLAUSES (Extracted from contracts)
-- ============================================================================

-- MSA Clauses (contract c_msa_001)
INSERT INTO clauses (
  id, contract_id, tenant_id, clause_type, extracted_text, page_number, section_reference,
  confidence, risk_level, risk_explanation, risk_score, is_standard, review_status, model_id, prompt_version
) VALUES
  -- Change of Control (HIGH RISK - deal-critical)
  ('cl_001'::uuid, 'c_msa_001'::uuid, 'f0f0f0f0-f0f0-f0f0-f0f0-f0f0f0f0f0f0',
   'change_of_control',
   'In the event of a Change of Control of either party, the non-affected party shall have the right to terminate this Agreement upon sixty (60) days written notice.',
   12, 'Section 14.2(b)',
   0.94, 'high', '60-day notice period is below market standard of 90 days', 78.0, false, 'auto_accepted',
   'claude-sonnet-4-20250514', 'extraction_v2.3'),

  -- Limitation of Liability (MEDIUM RISK)
  ('cl_002'::uuid, 'c_msa_001'::uuid, 'f0f0f0f0-f0f0-f0f0-f0f0-f0f0f0f0f0f0',
   'limitation_of_liability',
   'Neither party''s aggregate liability under this Agreement shall exceed the total fees paid in the twelve (12) months preceding the claim.',
   18, 'Section 10.1',
   0.88, 'medium', 'Standard market cap at 12-month fees', 42.0, true, 'auto_accepted',
   'claude-sonnet-4-20250514', 'extraction_v2.3'),

  -- Payment Terms (LOW RISK)
  ('cl_003'::uuid, 'c_msa_001'::uuid, 'f0f0f0f0-f0f0-f0f0-f0f0-f0f0f0f0f0f0',
   'payment_terms',
   'Invoices shall be due net thirty (30) days from receipt. Late payments accrue interest at 1.5% per month.',
   5, 'Section 3.2',
   0.97, 'low', 'Standard payment terms', 15.0, true, 'auto_accepted',
   'claude-sonnet-4-20250514', 'extraction_v2.3'),

  -- Termination for Convenience (MEDIUM RISK)
  ('cl_004'::uuid, 'c_msa_001'::uuid, 'f0f0f0f0-f0f0-f0f0-f0f0-f0f0f0f0f0f0',
   'termination_convenience',
   'Either party may terminate this Agreement without cause upon thirty (30) days written notice.',
   8, 'Section 5.1(a)',
   0.82, 'medium', '30-day notice is below market standard', 58.0, false, 'pending_review',
   'claude-sonnet-4-20250514', 'extraction_v2.3'),

  -- Indemnification (MEDIUM RISK)
  ('cl_005'::uuid, 'c_msa_001'::uuid, 'f0f0f0f0-f0f0-f0f0-f0f0-f0f0f0f0f0f0',
   'indemnification',
   'Each party shall indemnify and hold harmless the other party from third-party IP infringement claims.',
   22, 'Section 11.2',
   0.91, 'medium', 'Standard mutual indemnification', 45.0, true, 'auto_accepted',
   'claude-sonnet-4-20250514', 'extraction_v2.3'),

  -- Confidentiality (LOW RISK)
  ('cl_006'::uuid, 'c_msa_001'::uuid, 'f0f0f0f0-f0f0-f0f0-f0f0-f0f0f0f0f0f0',
   'confidentiality',
   'Each party agrees to maintain confidentiality of the other''s proprietary information for a period of three (3) years.',
   25, 'Section 12.1',
   0.95, 'low', 'Standard confidentiality obligation', 20.0, true, 'auto_accepted',
   'claude-sonnet-4-20250514', 'extraction_v2.3'),

  -- Governing Law (LOW RISK)
  ('cl_007'::uuid, 'c_msa_001'::uuid, 'f0f0f0f0-f0f0-f0f0-f0f0-f0f0f0f0f0f0',
   'governing_law',
   'This Agreement shall be governed by and construed in accordance with the laws of the State of Delaware.',
   39, 'Section 16.1',
   0.99, 'low', 'Delaware law is favorable for buyers', 10.0, true, 'auto_accepted',
   'claude-sonnet-4-20250514', 'extraction_v2.3'),

  -- Warranty & Representations (MEDIUM RISK)
  ('cl_008'::uuid, 'c_msa_001'::uuid, 'f0f0f0f0-f0f0-f0f0-f0f0-f0f0f0f0f0f0',
   'warranty_representations',
   'Vendor warrants that it has the authority to enter into this Agreement and that services will be performed in a professional manner.',
   3, 'Section 2.1',
   0.87, 'low', 'Standard warranty language', 25.0, true, 'auto_accepted',
   'claude-sonnet-4-20250514', 'extraction_v2.3'),

  -- Force Majeure (LOW RISK)
  ('cl_009'::uuid, 'c_msa_001'::uuid, 'f0f0f0f0-f0f0-f0f0-f0f0-f0f0f0f0f0f0',
   'force_majeure',
   'Neither party shall be liable for failure to perform due to unforeseen events beyond reasonable control.',
   37, 'Section 15.1',
   0.89, 'low', 'Standard force majeure clause', 18.0, true, 'auto_accepted',
   'claude-sonnet-4-20250514', 'extraction_v2.3');

-- SOW Clauses (contract c_sow_001)
INSERT INTO clauses (
  id, contract_id, tenant_id, clause_type, extracted_text, page_number, section_reference,
  confidence, risk_level, risk_explanation, risk_score, is_standard, review_status, model_id, prompt_version
) VALUES
  ('cl_010'::uuid, 'c_sow_001'::uuid, 'f0f0f0f0-f0f0-f0f0-f0f0-f0f0f0f0f0f0',
   'assignment',
   'Neither party may assign this SOW without prior written consent of the other party, not to be unreasonably withheld.',
   3, 'Section 2.1',
   0.91, 'low', 'Standard assignment restriction with reasonableness standard', 25.0, true, 'auto_accepted',
   'claude-sonnet-4-20250514', 'extraction_v2.3'),

  ('cl_011'::uuid, 'c_sow_001'::uuid, 'f0f0f0f0-f0f0-f0f0-f0f0-f0f0f0f0f0f0',
   'indemnification',
   'Vendor indemnifies Client for IP infringement claims. Indemnification is subject to the liability limitations.',
   11, 'Section 8.2',
   0.85, 'medium', 'IP indemnification capped at liability limits', 48.0, true, 'auto_accepted',
   'claude-sonnet-4-20250514', 'extraction_v2.3'),

  ('cl_012'::uuid, 'c_sow_001'::uuid, 'f0f0f0f0-f0f0-f0f0-f0f0-f0f0f0f0f0f0',
   'service_level_agreement',
   'Vendor shall maintain 99.5% system uptime. Credits apply for failures below this threshold.',
   6, 'Section 4.1',
   0.93, 'low', 'Industry-standard SLA', 22.0, true, 'auto_accepted',
   'claude-sonnet-4-20250514', 'extraction_v2.3'),

  ('cl_013'::uuid, 'c_sow_001'::uuid, 'f0f0f0f0-f0f0-f0f0-f0f0-f0f0f0f0f0f0',
   'payment_terms',
   'Invoices due net 30 days from invoice date. No interest charges for late payment.',
   2, 'Section 1.2',
   0.96, 'low', 'Standard SOW payment terms', 12.0, true, 'auto_accepted',
   'claude-sonnet-4-20250514', 'extraction_v2.3'),

  ('cl_014'::uuid, 'c_sow_001'::uuid, 'f0f0f0f0-f0f0-f0f0-f0f0-f0f0f0f0f0f0',
   'termination_cause',
   'Either party may terminate for material breach upon thirty (30) days written notice and opportunity to cure.',
   7, 'Section 5.2',
   0.88, 'medium', 'Material breach termination with cure period', 55.0, true, 'auto_accepted',
   'claude-sonnet-4-20250514', 'extraction_v2.3');

-- NDA Clauses (contract c_nda_001)
INSERT INTO clauses (
  id, contract_id, tenant_id, clause_type, extracted_text, page_number, section_reference,
  confidence, risk_level, risk_explanation, risk_score, is_standard, review_status, model_id, prompt_version
) VALUES
  ('cl_015'::uuid, 'c_nda_001'::uuid, 'f0f0f0f0-f0f0-f0f0-f0f0-f0f0f0f0f0f0',
   'non_disclosure',
   'Each party agrees not to disclose Confidential Information of the other party to third parties without prior written consent.',
   2, 'Section 2.1',
   0.98, 'low', 'Standard mutual NDA', 8.0, true, 'auto_accepted',
   'claude-sonnet-4-20250514', 'extraction_v2.3'),

  ('cl_016'::uuid, 'c_nda_001'::uuid, 'f0f0f0f0-f0f0-f0f0-f0f0-f0f0f0f0f0f0',
   'survival_clauses',
   'Confidentiality obligations survive termination of this Agreement for five (5) years.',
   5, 'Section 3.2',
   0.94, 'low', 'Standard survival period', 15.0, true, 'auto_accepted',
   'claude-sonnet-4-20250514', 'extraction_v2.3'),

  ('cl_017'::uuid, 'c_nda_001'::uuid, 'f0f0f0f0-f0f0-f0f0-f0f0-f0f0f0f0f0f0',
   'termination_convenience',
   'Either party may terminate this NDA at any time upon written notice.',
   4, 'Section 2.3',
   0.91, 'low', 'Standard NDA termination', 18.0, true, 'auto_accepted',
   'claude-sonnet-4-20250514', 'extraction_v2.3');

-- Vendor Agreement Clauses (contract c_vendor_001)
INSERT INTO clauses (
  id, contract_id, tenant_id, clause_type, extracted_text, page_number, section_reference,
  confidence, risk_level, risk_explanation, risk_score, is_standard, review_status, model_id, prompt_version
) VALUES
  ('cl_018'::uuid, 'c_vendor_001'::uuid, 'f0f0f0f0-f0f0-f0f0-f0f0-f0f0f0f0f0f0',
   'auto_renewal',
   'This Agreement shall automatically renew for successive one-year terms unless either party provides written notice of non-renewal at least ninety (90) days prior to expiration.',
   2, 'Section 1.3',
   0.93, 'high', 'Auto-renewal with 90-day notice requirement creates renewal trap', 72.0, false, 'auto_accepted',
   'claude-sonnet-4-20250514', 'extraction_v2.3'),

  ('cl_019'::uuid, 'c_vendor_001'::uuid, 'f0f0f0f0-f0f0-f0f0-f0f0-f0f0f0f0f0f0',
   'price_escalation',
   'Vendor fees shall increase by 3% annually on each anniversary unless Client provides written objection.',
   4, 'Section 3.1',
   0.87, 'medium', 'Automatic price increases', 52.0, false, 'auto_accepted',
   'claude-sonnet-4-20250514', 'extraction_v2.3'),

  ('cl_020'::uuid, 'c_vendor_001'::uuid, 'f0f0f0f0-f0f0-f0f0-f0f0-f0f0f0f0f0f0',
   'termination_convenience',
   'Client may terminate for convenience with one hundred twenty (120) days notice and payment of all fees through notice date.',
   6, 'Section 5.1',
   0.89, 'medium', 'Long termination notice period for client convenience', 48.0, false, 'auto_accepted',
   'claude-sonnet-4-20250514', 'extraction_v2.3'),

  ('cl_021'::uuid, 'c_vendor_001'::uuid, 'f0f0f0f0-f0f0-f0f0-f0f0-f0f0f0f0f0f0',
   'change_of_control',
   'If Client undergoes a Change of Control, Client must notify Vendor within thirty (30) days. Vendor may terminate upon thirty (30) days notice.',
   7, 'Section 5.2(a)',
   0.85, 'high', 'Short notice period for COC termination', 68.0, false, 'pending_review',
   'claude-sonnet-4-20250514', 'extraction_v2.3');

-- Real Estate Lease Clauses (contract c_lease_001)
INSERT INTO clauses (
  id, contract_id, tenant_id, clause_type, extracted_text, page_number, section_reference,
  confidence, risk_level, risk_explanation, risk_score, is_standard, review_status, model_id, prompt_version
) VALUES
  ('cl_022'::uuid, 'c_lease_001'::uuid, 'f0f0f0f0-f0f0-f0f0-f0f0-f0f0f0f0f0f0',
   'termination_cause',
   'Landlord may terminate this Lease for material non-payment of rent, with fifteen (15) days to cure after notice.',
   22, 'Section 18.1',
   0.89, 'critical', 'Short cure period (15 days) for rent payment is aggressive', 92.0, false, 'pending_review',
   'claude-sonnet-4-20250514', 'extraction_v2.3'),

  ('cl_023'::uuid, 'c_lease_001'::uuid, 'f0f0f0f0-f0f0-f0f0-f0f0-f0f0f0f0f0f0',
   'assignment',
   'Tenant may not assign this Lease without Landlord''s prior written consent, which may be withheld in Landlord''s sole discretion.',
   12, 'Section 12.1',
   0.91, 'high', 'Landlord has unrestricted consent rights for assignment', 75.0, false, 'auto_accepted',
   'claude-sonnet-4-20250514', 'extraction_v2.3'),

  ('cl_024'::uuid, 'c_lease_001'::uuid, 'f0f0f0f0-f0f0-f0f0-f0f0-f0f0f0f0f0f0',
   'renewal_auto_renewal',
   'Lease shall automatically renew for one (1) year periods unless Tenant provides ninety (90) days notice of non-renewal.',
   31, 'Section 25.1',
   0.92, 'medium', 'Auto-renewal with standard 90-day notice', 38.0, true, 'auto_accepted',
   'claude-sonnet-4-20250514', 'extraction_v2.3'),

  ('cl_025'::uuid, 'c_lease_001'::uuid, 'f0f0f0f0-f0f0-f0f0-f0f0-f0f0f0f0f0f0',
   'change_of_control',
   'If Tenant undergoes a change of control, Tenant must notify Landlord. Landlord may increase rent by up to 10% or terminate lease.',
   18, 'Section 14.2',
   0.83, 'high', 'COC triggers unilateral landlord right to increase rent or terminate', 71.0, false, 'pending_review',
   'claude-sonnet-4-20250514', 'extraction_v2.3');


-- ============================================================================
-- RISK FLAGS
-- ============================================================================

INSERT INTO risk_flags (
  id, clause_id, contract_id, tenant_id, flag_type, severity, description, recommendation, playbook_rule_id
) VALUES
  -- Critical flags
  ('flag_001'::uuid, 'cl_001'::uuid, 'c_msa_001'::uuid, 'f0f0f0f0-f0f0-f0f0-f0f0-f0f0f0f0f0f0',
   'change_of_control_trigger', 'critical',
   'Change of control triggers termination right for counterparty with only 60 days notice',
   'Negotiate for consent requirement or extend notice to 90+ days',
   'COC-001'::uuid),

  ('flag_002'::uuid, 'cl_018'::uuid, 'c_vendor_001'::uuid, 'f0f0f0f0-f0f0-f0f0-f0f0-f0f0f0f0f0f0',
   'auto_renewal_trap', 'critical',
   'Auto-renewal with 90-day notice requirement could cause renewal beyond intended deal period',
   'Modify to manual renewal or align renewal date with post-acquisition transition plan',
   'AUTO-001'::uuid),

  ('flag_003'::uuid, 'cl_022'::uuid, 'c_lease_001'::uuid, 'f0f0f0f0-f0f0-f0f0-f0f0-f0f0f0f0f0f0',
   'short_cure_period', 'critical',
   'Lease can be terminated for non-payment with only 15-day cure period - aggressive',
   'Negotiate for 30-day cure period to align with post-acquisition cash management practices',
   NULL),

  -- High flags
  ('flag_004'::uuid, 'cl_004'::uuid, 'c_msa_001'::uuid, 'f0f0f0f0-f0f0-f0f0-f0f0-f0f0f0f0f0f0',
   'short_notice_period', 'high',
   '30-day termination notice is below market standard (60-90 days typical)',
   'Extend notice period to minimum 60 days',
   NULL),

  ('flag_005'::uuid, 'cl_019'::uuid, 'c_vendor_001'::uuid, 'f0f0f0f0-f0f0-f0f0-f0f0-f0f0f0f0f0f0',
   'price_escalation', 'high',
   'Automatic 3% annual price increases with only written objection as control mechanism',
   'Change to mutual consent for increases or cap total increases at 2% annually',
   NULL),

  ('flag_006'::uuid, 'cl_023'::uuid, 'c_lease_001'::uuid, 'f0f0f0f0-f0f0-f0f0-f0f0-f0f0f0f0f0f0',
   'assignment_restriction', 'high',
   'Landlord has sole discretion to approve or deny Lease assignment - very restrictive',
   'Negotiate for reasonableness standard or carve-out for affiliate/buyer assignments',
   NULL),

  ('flag_007'::uuid, 'cl_025'::uuid, 'c_lease_001'::uuid, 'f0f0f0f0-f0f0-f0f0-f0f0-f0f0f0f0f0f0',
   'change_of_control_trigger', 'high',
   'Lease COC clause allows landlord to increase rent 10% or terminate - significant deal risk',
   'Negotiate for fixed renewal rate or right of first refusal only (no termination right)',
   'COC-002'::uuid);
