import { useEffect, useState } from 'react'
import { getPastRecords } from '../services/api'
import type { InspectionRecord } from '../services/api'

interface HistoryPageProps {
  onBack: () => void
}

export function HistoryPage({ onBack }: HistoryPageProps) {
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

        <p className="work-kicker">Inspection History</p>

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

        <h1>Inspection History</h1>

        <p className="work-lede">
          Previous product inspections recorded for your account.
        </p>

        {loading ? (
          <p className="history-loading">Loading inspection history…</p>
        ) : records.length === 0 ? (
          <div className="history-empty">
            <h2>No inspections yet</h2>
            <p>Your completed product inspections will appear here.</p>
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
                'Product inspection'

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
                        <span>Net {netQuantity}</span>
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
                        ? 'COMPLIANT'
                        : 'NON-COMPLIANT'}
                    </span>

                    <span className="history-score">
                      Score {record.confidence_score.toFixed(0)}%
                    </span>

                    {record.needs_manual_review ? (
                      <span className="history-review">
                        Manual review
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
