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
  legal_reference: string | null
  explanation: string | null
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

export interface AIFixSuggestion {
  rule_id: string
  field: string
  ai_fix: string
  example: string | null
  confidence: number
}

/** Combined payload returned by the backend OCR job result endpoint. */

export interface VisualBox {
  field: string
  text: string
  confidence: number
  similarity: number
  ocr_confidence: number
  box: [number, number, number, number] | null
  polygon: [number, number][]
  orientation: string
}

export type VisualBoxes = Record<string, Record<string, VisualBox>>

export interface CodeVerification {
  status: 'DECODED' | 'LABEL_MATCH' | 'NO_OCR_MATCH' | 'UNVERIFIED'
  message: string
}

export interface CodeScan {
  image: string | null
  qr_codes: Array<{
    data: string
    type: string
    polygon: [number, number][]
    verification?: CodeVerification
  }>
  barcodes: Array<{
    data: string
    type: string
    polygon: [number, number][] | null
    verification?: CodeVerification
  }>
  total_codes: number
}

export interface AnalyzeResponse {
  product_id: string
  product_folder: string
  merged_fields: MergedFields
  field_confidence: Record<string, number>
  visual_boxes: VisualBoxes
  code_scans: Record<string, CodeScan>
  ai_fix_suggestions: AIFixSuggestion[]
  compliance_result: ComplianceResult | null
  views: Record<string, unknown>
  metadata: Record<string, unknown>
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
