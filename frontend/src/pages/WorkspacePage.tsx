import { useState } from 'react'

import { AccountMenu } from '../components/auth/AccountMenu'
import { UploadSlot } from '../components/workspace/UploadSlot'
import { VisualBoxOverlay } from '../components/workspace/VisualBoxOverlay'
import type { LabelView } from '../types/app'
import { recheckCompliance } from '../services/api'
import { useI18n } from '../i18n/I18nContext'
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

const MANUAL_REVIEW_FIELDS: {
  key: keyof MergedFields
  label: string
}[] = [
  { key: 'mrp', label: 'MRP' },
  { key: 'net_quantity', label: 'Net Quantity' },
  { key: 'manufacturer_address', label: 'Manufacturer' },
  { key: 'consumer_care', label: 'Consumer Care' },
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
  onOpenDashboard: () => void
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
  onOpenDashboard,
  onLogout,
}: WorkspacePageProps) {
  const { t } = useI18n()
  const hasImage = Boolean(files.front || files.back || files.side)
  const violations: Violation[] = result?.violations ?? []

  const translatedFieldLabel = (key: keyof MergedFields) => {
    const labels: Partial<Record<keyof MergedFields, string>> = {
      brand: t('brand'),
      product_name: t('productName'),
      generic_name: t('genericName'),
      net_quantity: t('netQuantity'),
      mrp: t('mrp'),
      manufacturer_address: t('manufacturer'),
      consumer_care: t('consumerCare'),
      country_of_origin: t('countryOfOrigin'),
      mfg_date: t('manufacturingDate'),
    }

    return labels[key] ?? String(key)
  }
  const manualReviewFields = MANUAL_REVIEW_FIELDS
    .map((item) => {
      const value = fields?.[item.key]
      const confidence = fieldConfidence[item.key]

      return {
        ...item,
        value,
        confidence,
      }
    })
    .filter(
      (item) =>
        item.confidence !== undefined &&
        item.confidence < 0.5,
    )



  const [isEditingFields, setIsEditingFields] = useState(false)
  const [isRechecking, setIsRechecking] = useState(false)
  const [editedFields, setEditedFields] = useState<Partial<MergedFields>>({})
  const [manualCorrections, setManualCorrections] = useState<
    Record<string, { original: unknown; corrected: unknown }>
  >({})

  function startEditingFields() {
    setEditedFields({ ...(fields ?? {}) })
    setIsEditingFields(true)
  }

  function cancelEditingFields() {
    setEditedFields({})
    setIsEditingFields(false)
  }

  function updateEditedField(
    key: keyof MergedFields,
    value: string | boolean,
  ) {
    setEditedFields((current) => ({
      ...current,
      [key]: value,
    }))
  }

  async function handleRecheckCompliance() {
    if (!jobId) {
      alert('No inspection job is available for re-check.')
      return
    }

    setIsRechecking(true)

    try {
      const response = await recheckCompliance(
        jobId,
        editedFields as Record<string, unknown>,
      )

      // Update the local correction state immediately so the
      // current page can show "Officer verified" badges.
      setManualCorrections(
        response.manual_corrections ?? {},
      )

      // Keep the parent App state synchronized.
      window.dispatchEvent(
        new CustomEvent('label-lens:compliance-rechecked', {
          detail: response,
        }),
      )

      setEditedFields({})
      setIsEditingFields(false)
    } catch (error) {
      console.error('Compliance re-check failed', error)
      alert(
        error instanceof Error
          ? error.message
          : 'Failed to re-check compliance. Please try again.',
      )
    } finally {
      setIsRechecking(false)
    }
  }

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

        <p className="work-kicker">{t('inspection')}</p>

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
        <button
          type="button"
          className="text-btn dashboard-nav-btn"
          onClick={onOpenDashboard}
        >
          Dashboard
        </button>

        {user && <AccountMenu user={user} onLogout={onLogout} />}
      </header>

      {view === 'scan' ? (
        <section className="work-scan">
          <h1>{t('scanASproduct')}</h1>

          <p className="work-lede">
            {t('uploadInstructions')}
          </p>

          <div className="drop-grid">
            {SLOTS.map((slot) => (
              <UploadSlot
                key={slot.view}
                view={slot.view}
                title={
                  slot.view === 'front'
                    ? t('front')
                    : slot.view === 'back'
                      ? t('back')
                      : t('side')
                }
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
                {t('analyzingKeepOpen')}
              </p>
            ) : (
              <p>{t('readyToAnalyze')}</p>
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
          <p className="section-index">{t('result')}</p>

          <div className="result-hero">
            <div>
              <p className="score-kicker">{t('complianceScore')}</p>

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
                  ? t('compliant')
                  : 'NON-COMPLIANT'
                : t('awaitingAnalysis')}
            </p>
          </div>

          <p className="work-lede">
            {result?.summary ?? 'No compliance summary available.'}
          </p>

          <section className="compliance-breakdown">
            <div className="compliance-breakdown-header">
              <div>
                <p className="section-index">{t('complianceBreakdown')}</p>
                <h2>{t('declarationStatus')}</h2>
              </div>

              {fields?.product_type === 'food' ? (
                <span className="food-review-note">
                  Food-specific checks may also apply
                </span>
              ) : null}
            </div>

            <div className="compliance-field-grid">
              {FIELD_LABELS.map((row) => {
                const raw = fields?.[row.key]
                const empty =
                  raw === null ||
                  raw === undefined ||
                  raw === ''

                return (
                  <div
                    key={row.key}
                    className={
                      empty
                        ? 'compliance-field missing'
                        : 'compliance-field present'
                    }
                  >
                    <span className="compliance-field-icon">
                      {empty ? '×' : '✓'}
                    </span>

                    <div>
                      <strong>{row.label}</strong>
                      <span>
                        {empty
                          ? t('missing')
                          : String(raw)}
                      </span>
                    </div>
                  </div>
                )
              })}
            </div>
          </section>

          {result?.needs_manual_review ? (
            <section className="manual-review-panel">
              <div className="manual-review-header">
                <div>
                  <p className="section-index">{t('attention')}</p>
                  <h2>{t('manualReviewRequired')}</h2>
                  <p>
                    One or more critical label fields were detected
                    with low OCR confidence. Verify these values
                    against the original product image before
                    finalizing the inspection.
                  </p>
                </div>

                <span className="manual-review-badge">
                  VERIFY
                </span>
              </div>

              {manualReviewFields.length > 0 ? (
                <div className="manual-review-list">
                  {manualReviewFields.map((item) => {
                    const empty =
                      item.value === null ||
                      item.value === undefined ||
                      item.value === ''

                    const confidence = item.confidence ?? 0

                    return (
                      <article
                        key={String(item.key)}
                        className="manual-review-item"
                      >
                        <div className="manual-review-item-main">
                          <span className="manual-review-field">
                            {item.label}
                          </span>

                          <strong>
                            {empty
                              ? t('notExtracted')
                              : String(item.value)}
                          </strong>
                        </div>

                        <div className="manual-review-item-side">
                          <span className="manual-review-confidence">
                            {Math.round(confidence * 100)}% confidence
                          </span>

                          <span className="manual-review-reason">
                            Below 50% OCR threshold
                          </span>
                        </div>
                      </article>
                    )
                  })}
                </div>
              ) : (
                <div className="manual-review-generic">
                  <strong>{t('verificationRecommended')}</strong>
                  <span>
                    Review the extracted fields and original label
                    image before completing this inspection.
                  </span>
                </div>
              )}
            </section>
          ) : null}

          <section className="visual-inspection">
            <div className="visual-inspection-heading">
              <div>
                <p className="section-index">{t('visualVerification')}</p>
                <h2>{t('detectedLabelFields')}</h2>
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

          <div className="extracted-fields-header">
            <h2>{t('extractedFields')}</h2>

            {!isEditingFields ? (
              <button
                type="button"
                className="btn-outline"
                onClick={startEditingFields}
                disabled={isRechecking}
              >
                EDIT FIELDS
              </button>
            ) : null}
          </div>

          {isEditingFields ? (
            <section className="field-editor">
              <div className="field-editor-intro">
                <div>
                  <p className="section-index">{t('officerVerification')}</p>
                  <h3>{t('correctExtractedDeclarations')}</h3>
                  <p>
                    Update any value that was missed or incorrectly
                    extracted from the product label. Re-checking uses
                    the same official compliance rules.
                  </p>
                </div>
              </div>

              <div className="field-editor-grid">
                {FIELD_LABELS.map((row) => {
                  const currentValue =
                    editedFields[row.key] ?? fields?.[row.key]

                  const isBoolean =
                    typeof currentValue === 'boolean'

                  return (
                    <label
                      key={row.key}
                      className="field-editor-row"
                    >
                      <span>{row.label}</span>

                      {isBoolean ? (
                        <select
                          value={currentValue ? 'true' : 'false'}
                          onChange={(event) =>
                            updateEditedField(
                              row.key,
                              event.target.value === 'true',
                            )
                          }
                        >
                          <option value="true">{t('yes')}</option>
                          <option value="false">{t('no')}</option>
                        </select>
                      ) : (
                        <input
                          type="text"
                          value={
                            currentValue === null ||
                            currentValue === undefined
                              ? ''
                              : String(currentValue)
                          }
                          placeholder={`Enter ${row.label.toLowerCase()}`}
                          onChange={(event) =>
                            updateEditedField(
                              row.key,
                              event.target.value,
                            )
                          }
                        />
                      )}
                    </label>
                  )
                })}
              </div>

              <div className="field-editor-actions">
                <button
                  type="button"
                  className="btn-outline"
                  onClick={cancelEditingFields}
                  disabled={isRechecking}
                >
                  CANCEL
                </button>

                <button
                  type="button"
                  className="btn-solid"
                  onClick={handleRecheckCompliance}
                  disabled={isRechecking}
                >
                  {isRechecking
                    ? 'RE-CHECKING…'
                    : 'RE-CHECK COMPLIANCE →'}
                </button>
              </div>
            </section>
          ) : (
            <ul className="field-rows dense">
              {FIELD_LABELS.map((row) => {
                const raw = fields?.[row.key]
                const empty =
                  raw === null ||
                  raw === undefined ||
                  raw === ''

                const confidence = fieldConfidence[row.key]

                return (
                  <li
                    key={row.key}
                    className={
                      empty
                        ? 'field-row is-miss'
                        : 'field-row is-ok'
                    }
                  >
                    <span className="field-label">
                      {translatedFieldLabel(row.key)}
                    </span>

                    <span className="field-value">
                      {empty ? '—' : String(raw)}

                      {manualCorrections[row.key] ? (
                        <span className="officer-verified-badge">
                          ✓ Officer verified
                        </span>
                      ) : null}
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
                          ? t('missing').toUpperCase()
                          : confidence !== undefined
                            ? `${getConfidenceLevel(
                                confidence,
                              )} · ${Math.round(
                                confidence * 100,
                              )}%`
                            : t('present').toUpperCase()}
                      </span>
                    </span>
                  </li>
                )
              })}
            </ul>
          )}

          <section className="code-scan-section">
            <div className="section-heading">
              <div>
                <h2>{t('codesDetected')}</h2>
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
                              {barcode.type || t('barcode')}
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
                                  ? t('noOcrMatch')
                                  : t('notVerified')}
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
              <h2>{t('missingFields')}</h2>

              <p>
                {result?.missing_fields?.length
                  ? result.missing_fields.join(', ')
                  : 'None yet.'}
              </p>
            </div>

            <div>
              <h2>{t('warnings')}</h2>

              <p>
                {result?.warnings?.length
                  ? result.warnings.join(' ')
                  : 'None yet.'}
              </p>
            </div>
          </div>

          <h2>{t('ruleDetails')}</h2>

          {violations.length === 0 ? (
            <p>{t('noViolationRecords')}</p>
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
                        <strong>{t('legalReference')}</strong>
                        <span>{item.legal_reference}</span>
                      </div>
                    )}

                    {item.explanation && (
                      <div className="rule-explanation">
                        <strong>{t('whyThisMatters')}</strong>
                        <span>{item.explanation}</span>
                      </div>
                    )}

                    {item.suggestion && (
                      <div className="rule-explanation">
                        <strong>{t('howToFix')}</strong>
                        <span>{item.suggestion}</span>
                      </div>
                    )}

                    {aiFix && (
                      <div className="rule-explanation ai-fix-suggestion">
                        <strong>{t('aiFixSuggestion')}</strong>

                        <span>{aiFix.ai_fix}</span>

                        {aiFix.example && (
                          <span>
                            <strong>{t('example')}</strong> {aiFix.example}
                          </span>
                        )}

                        <span>
                          <strong>{t('aiConfidence')}</strong>{' '}
                          {Math.round(aiFix.confidence * 100)}%
                        </span>
                      </div>
                    )}
                  </li>
                )
              })}
            </ul>
          )}

          <h2>{t('report')}</h2>

          <div className="hero-actions">
            <button
              type="button"
              className="btn-solid"
              disabled={!jobId}
              onClick={handleDownloadPDF}
            >
              {t('downloadPdf')}
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
