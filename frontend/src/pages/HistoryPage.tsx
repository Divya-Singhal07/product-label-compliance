import { useEffect, useState } from 'react'
import { getPastRecords } from '../services/api'
import type { InspectionRecord } from '../services/api'
import { useI18n } from '../i18n/I18nContext'

interface HistoryPageProps {
  onBack: () => void
}

export function HistoryPage({ onBack }: HistoryPageProps) {
  const { t } = useI18n()

  const [records, setRecords] = useState<InspectionRecord[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let active = true

    getPastRecords().then((data) => {
      if (active) {
        setRecords(data)
        setLoading(false)
      }
    })

    return () => {
      active = false
    }
  }, [])

  return (
    <div className="history-page">
      <header className="work-nav history-nav">
        <button type="button" className="wordmark" onClick={onBack}>
          Label Lens
        </button>

        <p className="work-kicker">{t('inspectionHistory')}</p>

        <button
          type="button"
          className="history-back-btn"
          onClick={onBack}
        >
          ← Back
        </button>
      </header>

      <main className="history-content">
        <p className="section-index">History</p>

        <h1>{t('inspectionHistory')}</h1>

        <p className="work-lede">
          {t('previousInspections')}
        </p>

        {loading ? (
          <p className="history-loading">{t('loadingHistory')}</p>
        ) : records.length === 0 ? (
          <div className="history-empty">
            <h2>{t('noInspectionsYet')}</h2>
            <p>{t('completedInspectionsAppear')}</p>
          </div>
        ) : (
          <div className="history-list">
            {records.map((record) => {
              const extracted = record.extracted_fields ?? {}

              const getField = (key: string) => {
                const value = extracted[key]
                return typeof value === 'string' && value.trim()
                  ? value
                  : null
              }

              const productName =
                getField('product_name') ||
                getField('generic_name') ||
                record.product_id ||
                t('productInspection')

              const genericName = getField('generic_name')
              const netQuantity = getField('net_quantity')
              const mrp = getField('mrp')

              return (
                <article key={record.id} className="history-card">
                  <div className="history-main">
                    <p className="history-product">{productName}</p>

                    {genericName && genericName !== productName ? (
                      <p className="history-detail">{genericName}</p>
                    ) : null}

                    <div className="history-details">
                      {netQuantity ? (
                        <span>{t('net')} {netQuantity}</span>
                      ) : null}

                      {mrp ? (
                        <span>MRP ₹{mrp}</span>
                      ) : null}
                    </div>

                    <p className="history-date">
                      {new Date(record.created_at).toLocaleString()}
                    </p>
                  </div>

                  <div className="history-meta">
                    <span
                      className={
                        record.is_compliant
                          ? 'history-status compliant'
                          : 'history-status non-compliant'
                      }
                    >
                      {record.is_compliant
                        ? t('compliant')
                        : t('nonCompliant')}
                    </span>

                    <span className="history-score">
                      {t('scoreLabel')} {record.confidence_score.toFixed(0)}%
                    </span>

                    {record.needs_manual_review ? (
                      <span className="history-review">
                        {t('manualReview')}
                      </span>
                    ) : null}
                  </div>
                </article>
              )
            })}
          </div>
        )}
      </main>
    </div>
  )
}
