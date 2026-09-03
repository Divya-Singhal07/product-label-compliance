import { UploadSlot } from '../components/workspace/UploadSlot'
import type { LabelView } from '../types/app'
import type { ComplianceResult, MergedFields, Violation } from '../types/compliance'

const SLOTS: { view: LabelView; title: string }[] = [
  { view: 'front', title: 'Front' },
  { view: 'back', title: 'Back' },
  { view: 'side', title: 'Side' },
]

const FIELD_LABELS: { key: keyof MergedFields; label: string }[] = [
  { key: 'brand', label: 'Brand' },
  { key: 'product_name', label: 'Product Name' },
  { key: 'generic_name', label: 'Generic Name' },
  { key: 'net_quantity', label: 'Net Quantity' },
  { key: 'mrp', label: 'MRP' },
  { key: 'manufacturer_address', label: 'Manufacturer' },
  { key: 'consumer_care', label: 'Consumer Care' },
  { key: 'country_of_origin', label: 'Country of Origin' },
  { key: 'mfg_date', label: 'Manufacturing Date' },
]

interface WorkspacePageProps {
  view: 'scan' | 'result'
  files: Partial<Record<LabelView, File>>
  previewUrls: Partial<Record<LabelView, string>>
  isProcessing: boolean
  fields: MergedFields | null
  result: ComplianceResult | null
  onSelect: (view: LabelView, file: File) => void
  onClear: (view: LabelView) => void
  onAnalyze: () => void
  onBackHome: () => void
  onOpenScan: () => void
}

export function WorkspacePage({
  view,
  files,
  previewUrls,
  isProcessing,
  fields,
  result,
  onSelect,
  onClear,
  onAnalyze,
  onBackHome,
  onOpenScan,
}: WorkspacePageProps) {
  const hasImage = Boolean(files.front || files.back || files.side)
  const violations: Violation[] = result?.violations ?? []

  return (
    <div className="workspace">
      <header className="work-nav">
        <button type="button" className="wordmark" onClick={onBackHome}>
          Label Lens
        </button>
        <p className="work-kicker">Inspection</p>
        <button type="button" className="text-btn" onClick={onBackHome}>
          ← Home
        </button>
      </header>

      {view === 'scan' ? (
        <section className="work-scan">
          <h1>Scan a product</h1>
          <p className="work-lede">
            Front, back and optional side. Analysis will use the backend pipeline
            when the HTTP API is available — this screen does not run OCR.
          </p>
          <div className="drop-grid">
            {SLOTS.map((slot) => (
              <UploadSlot
                key={slot.view}
                view={slot.view}
                title={slot.title}
                file={files[slot.view] ?? null}
                previewUrl={previewUrls[slot.view] ?? null}
                onSelect={(file) => onSelect(slot.view, file)}
                onClear={() => onClear(slot.view)}
              />
            ))}
          </div>
          <div className="work-process">
            {isProcessing ? (
              <p className="processing" role="status">
                Staging images… the rule engine is not called from this UI yet.
              </p>
            ) : (
              <p>Idle. No network request is sent.</p>
            )}
          </div>
          <button
            type="button"
            className="btn-solid"
            disabled={!hasImage || isProcessing}
            onClick={onAnalyze}
          >
            ANALYZE PRODUCT →
          </button>
        </section>
      ) : (
        <section className="work-result">
          <p className="section-index">Result</p>
          <div className="result-hero">
            <div>
              <p className="score-kicker">COMPLIANCE SCORE</p>
              <p className="score-giant small">
                {result ? result.score.toFixed(0) : '—'}
              </p>
              <p className="score-denom">/ 100</p>
            </div>
            <p
              className={
                result?.is_compliant === false
                  ? 'score-status danger'
                  : 'score-status'
              }
            >
              {result
                ? result.is_compliant
                  ? 'COMPLIANT'
                  : 'NON-COMPLIANT'
                : 'AWAITING ANALYSIS'}
            </p>
          </div>
          <p className="work-lede">
            {result?.summary ??
              'Score, fields, violations and the report will fill in from ComplianceResult once the API exists.'}
          </p>
          {result?.needs_manual_review ? (
            <p className="caution-line">Manual review required</p>
          ) : null}

          <h2>Extracted fields</h2>
          <ul className="field-rows dense">
            {FIELD_LABELS.map((row) => {
              const raw = fields?.[row.key]
              const empty = raw === null || raw === undefined || raw === ''
              return (
                <li
                  key={row.key}
                  className={empty ? 'field-row is-miss' : 'field-row is-ok'}
                >
                  <span className="field-label">{row.label}</span>
                  <span className="field-value">
                    {empty ? '—' : String(raw)}
                  </span>
                  <span className="field-mark">
                    {empty ? 'MISSING' : 'PRESENT'}
                  </span>
                </li>
              )
            })}
          </ul>

          <div className="split-notes">
            <div>
              <h2>Missing fields</h2>
              <p>
                {result?.missing_fields.length
                  ? result.missing_fields.join(', ')
                  : 'None yet.'}
              </p>
            </div>
            <div>
              <h2>Warnings</h2>
              <p>
                {result?.warnings.length
                  ? result.warnings.join(' ')
                  : 'None yet.'}
              </p>
            </div>
          </div>

          <h2>Rule details</h2>
          {violations.length === 0 ? (
            <p>No Violation records to display.</p>
          ) : (
            <ul className="violation-stack">
              {violations.map((item) => (
                <li key={`${item.rule_id}-${item.field}`}>
                  <strong>
                    {item.rule_id} · {item.field} · {item.severity}
                  </strong>
                  <p>{item.message}</p>
                  <p>{item.suggestion ?? ''}</p>
                </li>
              ))}
            </ul>
          )}

          <h2>Report</h2>
          <p>
            PDF export will attach to the existing Python report generator. Download
            is not wired.
          </p>
          <div className="hero-actions">
            <button type="button" className="btn-solid" disabled>
              DOWNLOAD PDF →
            </button>
            <button type="button" className="btn-ghost dark" onClick={onOpenScan}>
              SCAN ANOTHER
            </button>
          </div>
        </section>
      )}
    </div>
  )
}
