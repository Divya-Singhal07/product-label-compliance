/**
 * Shared TypeScript contracts aligned with the existing Python models.
 *
 * Sources:
 * - label_lens/rule_engine/models.py (Severity, Violation, ComplianceResult)
 * - label_lens/ocr/ocr_pipeline.py FIELD_DEFAULTS / LLM schema (MergedFields)
 *
 * Do not add backend fields that are not already identified in those models.
 */

export type Severity = 'high' | 'medium' | 'low' | 'info'

export type ProductTypeExtractor =
  | 'food'
  | 'cosmetic'
  | 'electronic'
  | 'general'

export interface MergedFields {
  brand: string | null
  product_name: string | null
  generic_name: string | null
  net_quantity: string | null
  mrp: string | null
  mrp_inclusive_of_taxes: boolean
  unit_sale_price: string | null
  manufacturer_address: string | null
  packer: string | null
  importer: string | null
  consumer_care: string | null
  mfg_date: string | null
  best_before: string | null
  use_by: string | null
  country_of_origin: string | null
  product_type: ProductTypeExtractor | string
  specific_product: string | null
  is_food: boolean
  is_cosmetic: boolean
  is_electronic: boolean
  is_imported: boolean
  has_shelf_life: boolean
}

export interface Violation {
  rule_id: string
  field: string
  message: string
  severity: Severity
  suggestion: string | null
  detected_value: string | null
  expected: string | null
  layer: string | null
}

export interface ComplianceResult {
  is_compliant: boolean
  score: number
  product_type: string
  specific_product: string | null
  violations: Violation[]
  missing_fields: string[]
  warnings: string[]
  needs_manual_review: boolean
  summary: string
  rule_version: string
  layers_applied: string[]
}

/** Combined payload the frontend expects once an HTTP API exists. */
export interface AnalyzeResponse {
  product_id: string
  merged_fields: MergedFields
  compliance: ComplianceResult
}

/** Local UI helper for scan-history rows. Not a backend model. */
export interface ScanHistoryRow {
  id: string
  product: string
  date: string
  is_compliant: boolean
  score: number
  needs_manual_review: boolean
}
