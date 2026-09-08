import { AccountMenu } from '../components/auth/AccountMenu'
import { UploadSlot } from '../components/workspace/UploadSlot'
import { VisualBoxOverlay } from '../components/workspace/VisualBoxOverlay'
import type { LabelView } from '../types/app'
import type { User } from '../types/auth'
import type {
  AIFixSuggestion,
  ComplianceResult,
  MergedFields,
  VisualBoxes,
  CodeScan,
  Violation,
} from '../types/compliance'

const SLOTS: { view: LabelView; title: string }[] = [
  { view: 'front', title: 'Front' },
  { view: 'back', title: 'Back' },
  { view: 'side', title: 'Side' },
]

function getConfidenceLevel(confidence: number) {
  if (confidence >= 0.9) return 'HIGH'
  if (confidence >= 0.7) return 'MEDIUM'
  return 'LOW'
}

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
  user: User | null
  view: 'scan' | 'result'
  files: Partial<Record<LabelView, File>>
  previewUrls: Partial<Record<LabelView, string>>
  isProcessing: boolean
  fields: MergedFields | null
  fieldConfidence: Record<string, number>
  visualBoxes: VisualBoxes
  codeScans: Record<string, CodeScan>
  result: ComplianceResult | null
  aiFixSuggestions: AIFixSuggestion[]
  jobId: string | null
  onSelect: (view: LabelView, file: File) => void
  onClear: (view: LabelView) => void
  onAnalyze: () => void
  onBackHome: () => void
  onOpenScan: () => void
  onOpenHistory: () => void
  onLogout: () => void
}

export function WorkspacePage({
  user,
  view,
  files,
  previewUrls,
  isProcessing,
  fields,
  fieldConfidence,
  visualBoxes,
  codeScans,
  result,
  aiFixSuggestions,
  jobId,
  onSelect,
  onClear,
  onAnalyze,
  onBackHome,
  onOpenScan,
  onOpenHistory,
  onLogout,
}: WorkspacePageProps) {
  const hasImage = Boolean(files.front || files.back || files.side)
  const violations: Violation[] = result?.violations ?? []

  const getAIFixSuggestion = (ruleId: string, field: string) =>
    aiFixSuggestions.find(
      (item) => item.rule_id === ruleId && item.field === field,
    )

  async function handleDownloadPDF() {
    if (!jobId) return

    try {
      const res = await fetch(`/api/v1/ocr/jobs/${jobId}/pdf`, {
        credentials: 'include',
      })

      if (!res.ok) throw new Error('Failed to generate PDF')

      const blob = await res.blob()
      const url = window.URL.createObjectURL(blob)

      const a = document.createElement('a')
      a.href = url
      a.download = `Compliance_Report_${jobId.slice(0, 8)}.pdf`

      document.body.appendChild(a)
      a.click()
      a.remove()

      window.URL.revokeObjectURL(url)
    } catch (err) {
      console.error(err)
      alert('Could not download PDF. Please try again.')
    }
  }

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
        <button
          type="button"
          className="text-btn history-nav-btn"
          onClick={onOpenHistory}
        >
          History
        </button>

        {user && <AccountMenu user={user} onLogout={onLogout} />}
      </header>

      {view === 'scan' ? (
        <section className="work-scan">
          <h1>Scan a product</h1>

          <p className="work-lede">
            Upload front, back and optional side images. The backend will run
            OCR extraction and compliance checking automatically.
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
                Analyzing… Keep this tab open.
              </p>
            ) : (
              <p>Ready to analyze.</p>
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
            {result?.summary ?? 'No compliance summary available.'}
          </p>

          {result?.needs_manual_review ? (
            <p className="caution-line">Manual review required</p>
          ) : null}

          <section className="visual-inspection">
            <div className="visual-inspection-heading">
              <div>
                <p className="section-index">Visual verification</p>
                <h2>Detected label fields</h2>
              </div>
              <p>
                Highlighted regions show where the OCR engine found the
                extracted fields on the original product images.
              </p>
            </div>

            <div className="visual-inspection-grid">
              {SLOTS.map((slot) => {
                const previewUrl = previewUrls[slot.view]
                const boxes = visualBoxes[slot.view] ?? {}

                if (!previewUrl) return null

                return (
                  <article
                    key={slot.view}
                    className="visual-inspection-card"
                  >
                    <header>
                      <div>
                        <span className="visual-view-kicker">
                          {slot.title}
                        </span>
                        <h3>{slot.title} label</h3>
                      </div>

                      <span className="visual-box-count">
                        {Object.keys(boxes).length} detected
                      </span>
                    </header>

                    <VisualBoxOverlay
                      src={previewUrl}
                      boxes={boxes}
                      codeScan={codeScans[slot.view]}
                    />
                  </article>
                )
              })}
            </div>
          </section>

          <h2>Extracted fields</h2>

          <ul className="field-rows dense">
            {FIELD_LABELS.map((row) => {
              const raw = fields?.[row.key]
              const empty = raw === null || raw === undefined || raw === ''
              const confidence = fieldConfidence[row.key]

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
                    <span
                      className={
                        empty
                          ? 'field-mark'
                          : confidence !== undefined
                            ? `field-mark confidence-${getConfidenceLevel(
                                confidence,
                              ).toLowerCase()}`
                            : 'field-mark'
                      }
                    >
                      {empty
                        ? 'MISSING'
                        : confidence !== undefined
                          ? `${getConfidenceLevel(confidence)} · ${Math.round(
                              confidence * 100,
                            )}%`
                          : 'PRESENT'}
                    </span>
                  </span>
                </li>
              )
            })}
          </ul>

          <section className="code-scan-section">
            <div className="section-heading">
              <div>
                <h2>Codes Detected</h2>
                <p>
                  QR codes and barcodes detected on the uploaded product views.
                </p>
              </div>
            </div>

            <div className="code-scan-grid">
              {Object.entries(codeScans).map(([viewName, scan]) => {
                if (scan.total_codes === 0) return null

                return (
                  <article
                    key={viewName}
                    className="code-scan-card"
                  >
                    <header>
                      <div>
                        <span className="visual-view-kicker">
                          {viewName}
                        </span>
                        <h3>
                          {viewName.charAt(0).toUpperCase() +
                            viewName.slice(1)}{' '}
                          label
                        </h3>
                      </div>

                      <span className="visual-box-count">
                        {scan.total_codes} detected
                      </span>
                    </header>

                    {scan.qr_codes.map((qr, index) => (
                      <div
                        key={`qr-${index}-${qr.data}`}
                        className="code-result"
                      >
                        <div className="code-result-header">
                          <div className="code-result-type">
                            QR CODE
                          </div>
                          <span className="code-status is-info">
                            Decoded ✓
                          </span>
                        </div>

                        <div className="code-result-value">
                          {/^(https?:\/\/)/i.test(qr.data) ? (
                            <a
                              href={qr.data}
                              target="_blank"
                              rel="noreferrer"
                            >
                              {qr.data}
                            </a>
                          ) : (
                            qr.data
                          )}
                        </div>

                        <div className="code-result-message">
                          {qr.verification?.message ??
                            'QR payload decoded successfully.'}
                        </div>
                      </div>
                    ))}

                    {scan.barcodes.map((barcode, index) => {
                      const status =
                        barcode.verification?.status ?? 'UNVERIFIED'

                      return (
                        <div
                          key={`barcode-${index}-${barcode.data}`}
                          className="code-result"
                        >
                          <div className="code-result-header">
                            <div className="code-result-type">
                              {barcode.type || 'BARCODE'}
                            </div>

                            <span
                              className={`code-status ${
                                status === 'LABEL_MATCH'
                                  ? 'is-success'
                                  : 'is-warning'
                              }`}
                            >
                              {status === 'LABEL_MATCH'
                                ? 'Label Match ✓'
                                : status === 'NO_OCR_MATCH'
                                  ? 'No OCR Match'
                                  : 'Not Verified'}
                            </span>
                          </div>

                          <div className="code-result-value">
                            {barcode.data}
                          </div>

                          <div className="code-result-message">
                            {barcode.verification?.message ??
                              'Barcode decoded successfully.'}
                          </div>
                        </div>
                      )
                    })}

                  </article>
                )
              })}

              {Object.values(codeScans).every(
                (scan) => scan.total_codes === 0,
              ) && (
                <p className="code-scan-empty">
                  No QR codes or barcodes detected.
                </p>
              )}
            </div>
          </section>

          <div className="split-notes">
            <div>
              <h2>Missing fields</h2>

              <p>
                {result?.missing_fields?.length
                  ? result.missing_fields.join(', ')
                  : 'None yet.'}
              </p>
            </div>

            <div>
              <h2>Warnings</h2>

              <p>
                {result?.warnings?.length
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
              {violations.map((item) => {
                const aiFix = getAIFixSuggestion(
                  item.rule_id,
                  item.field,
                )

                return (
                  <li key={`${item.rule_id}-${item.field}`}>
                    <div className="violation-header">
                      <strong>
                        {item.rule_id} · {item.field}
                      </strong>

                      <span
                        className={`severity-badge severity-${item.severity}`}
                      >
                        {item.severity.toUpperCase()}
                      </span>
                    </div>

                    <p>{item.message}</p>

                    {item.legal_reference && (
                      <div className="rule-explanation">
                        <strong>Legal Reference</strong>
                        <span>{item.legal_reference}</span>
                      </div>
                    )}

                    {item.explanation && (
                      <div className="rule-explanation">
                        <strong>Why this matters</strong>
                        <span>{item.explanation}</span>
                      </div>
                    )}

                    {item.suggestion && (
                      <div className="rule-explanation">
                        <strong>How to fix</strong>
                        <span>{item.suggestion}</span>
                      </div>
                    )}

                    {aiFix && (
                      <div className="rule-explanation ai-fix-suggestion">
                        <strong>AI Fix Suggestion</strong>

                        <span>{aiFix.ai_fix}</span>

                        {aiFix.example && (
                          <span>
                            <strong>Example:</strong> {aiFix.example}
                          </span>
                        )}

                        <span>
                          <strong>AI Confidence:</strong>{' '}
                          {Math.round(aiFix.confidence * 100)}%
                        </span>
                      </div>
                    )}
                  </li>
                )
              })}
            </ul>
          )}

          <h2>Report</h2>

          <div className="hero-actions">
            <button
              type="button"
              className="btn-solid"
              disabled={!jobId}
              onClick={handleDownloadPDF}
            >
              DOWNLOAD PDF →
            </button>

            <button
              type="button"
              className="btn-ghost dark"
              onClick={onOpenScan}
            >
              SCAN ANOTHER
            </button>
          </div>
        </section>
      )}
    </div>
  )
}
