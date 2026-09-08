import { useEffect, useMemo, useState } from 'react'
import { getPastRecords } from '../services/api'
import type { InspectionRecord } from '../services/api'
import { useI18n } from '../i18n/I18nContext'

interface DashboardPageProps {
  onBack: () => void
  onOpenHistory: () => void
  onOpenScan: () => void
}

function formatDate(value: string) {
  return new Date(value).toLocaleDateString(undefined, {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  })
}

function formatTime(value: string) {
  return new Date(value).toLocaleTimeString(undefined, {
    hour: 'numeric',
    minute: '2-digit',
  })
}

const DASHBOARD_CACHE_KEY = 'label-lens-inspection-records'
const DASHBOARD_CACHE_TTL = 60 * 1000

function readCachedRecords(): InspectionRecord[] {
  try {
    const raw = sessionStorage.getItem(DASHBOARD_CACHE_KEY)
    if (!raw) return []

    const cached = JSON.parse(raw)

    if (
      !cached ||
      typeof cached !== 'object' ||
      !Array.isArray(cached.records) ||
      typeof cached.timestamp !== 'number'
    ) {
      return []
    }

    if (Date.now() - cached.timestamp > DASHBOARD_CACHE_TTL) {
      sessionStorage.removeItem(DASHBOARD_CACHE_KEY)
      return []
    }

    return cached.records as InspectionRecord[]
  } catch {
    return []
  }
}

function writeCachedRecords(records: InspectionRecord[]) {
  try {
    sessionStorage.setItem(
      DASHBOARD_CACHE_KEY,
      JSON.stringify({
        timestamp: Date.now(),
        records,
      }),
    )
  } catch {
    // Ignore storage failures.
  }
}

export function DashboardPage({
  onBack,
  onOpenHistory,
  onOpenScan,
}: DashboardPageProps) {
  const { t } = useI18n()

  const [records, setRecords] = useState<InspectionRecord[]>(
    () => readCachedRecords(),
  )
  const [loading, setLoading] = useState(
    () => readCachedRecords().length === 0,
  )

  useEffect(() => {
    let active = true

    getPastRecords().then((data) => {
      if (active) {
        setRecords(data)
        writeCachedRecords(data)
        setLoading(false)
      }
    })

    return () => {
      active = false
    }
  }, [])

  const analytics = useMemo(() => {
    const total = records.length

    const compliant = records.filter(
      (record) => record.is_compliant,
    ).length

    const nonCompliant = total - compliant

    const manualReviews = records.filter(
      (record) => record.needs_manual_review,
    ).length

    const averageConfidence =
      total > 0
        ? records.reduce(
            (sum, record) =>
              sum + Number(record.confidence_score || 0),
            0,
          ) / total
        : 0

    const complianceRate =
      total > 0 ? (compliant / total) * 100 : 0

    const totalViolations = records.reduce(
      (sum, record) => sum + (record.violations?.length ?? 0),
      0,
    )

    const lastSevenDays = Array.from({ length: 7 }, (_, index) => {
      const date = new Date()
      date.setHours(0, 0, 0, 0)
      date.setDate(date.getDate() - (6 - index))

      const dayRecords = records.filter((record) => {
        const recordDate = new Date(record.created_at)
        recordDate.setHours(0, 0, 0, 0)

        return recordDate.getTime() === date.getTime()
      })

      return {
        key: date.toISOString(),
        label: date.toLocaleDateString(undefined, {
          weekday: 'short',
        }),
        count: dayRecords.length,
        compliant: dayRecords.filter(
          (record) => record.is_compliant,
        ).length,
        nonCompliant: dayRecords.filter(
          (record) => !record.is_compliant,
        ).length,
      }
    })

    const violationMap = new Map<string, number>()

    records.forEach((record) => {
      ;(record.violations ?? []).forEach((item) => {
        if (
          item &&
          typeof item === 'object' &&
          'rule_id' in item
        ) {
          const ruleId = String(
            (item as { rule_id?: unknown }).rule_id ||
              'UNKNOWN',
          )

          violationMap.set(
            ruleId,
            (violationMap.get(ruleId) ?? 0) + 1,
          )
        }
      })
    })

    const topViolations = Array.from(
      violationMap.entries(),
    )
      .sort((a, b) => b[1] - a[1])
      .slice(0, 5)

    return {
      total,
      compliant,
      nonCompliant,
      manualReviews,
      averageConfidence,
      complianceRate,
      totalViolations,
      lastSevenDays,
      topViolations,
    }
  }, [records])

  const recentRecords = records.slice(0, 6)

  return (
    <div className="dashboard-page">
      <header className="work-nav dashboard-nav">
        <button type="button" className="wordmark" onClick={onBack}>
          Label Lens
        </button>

        <p className="work-kicker">{t('officerDashboard')}</p>

        <div className="dashboard-nav-actions">
          <button
            type="button"
            className="text-btn"
            onClick={onOpenHistory}
          >
            {t('history')}
          </button>

          <button
            type="button"
            className="text-btn"
            onClick={onOpenScan}
          >
            {t('newScan')}
          </button>
        </div>
      </header>

      <main className="dashboard-content">
        <section className="dashboard-hero">
          <div>
            <p className="section-index">Dashboard</p>
            <h1>{t('inspectionCommandCenter')}</h1>
            <p className="dashboard-hero-copy">
              {t('dashboardHeroCopy')}
            </p>
          </div>

          <button
            type="button"
            className="dashboard-primary-action"
            onClick={onOpenScan}
          >
            <span>+</span>
            {t('scanNewProduct')}
          </button>
        </section>

        {loading ? (
          <div className="dashboard-loading-card">
            <div className="dashboard-spinner" />
            <p>{t('loadingInspectionAnalytics')}</p>
          </div>
        ) : (
          <>
            <section className="dashboard-kpis">
              <article className="dashboard-kpi kpi-primary">
                <div className="dashboard-kpi-top">
                  <span>01</span>
                  <span className="dashboard-kpi-dot" />
                </div>
                <p>{t('totalInspections')}</p>
                <strong>{analytics.total}</strong>
                <small>{t('allRecordedInspections')}</small>
              </article>

              <article className="dashboard-kpi">
                <div className="dashboard-kpi-top">
                  <span>02</span>
                  <span className="dashboard-mini-label">
                    {t('outcome')}
                  </span>
                </div>
                <p>{t('complianceRate')}</p>
                <strong>{analytics.complianceRate.toFixed(0)}%</strong>
                <small>
                  {analytics.compliant} {t('compliant').toLowerCase()} ·{' '}
                  {analytics.nonCompliant} {t('nonCompliant').toLowerCase()}
                </small>
              </article>

              <article className="dashboard-kpi">
                <div className="dashboard-kpi-top">
                  <span>03</span>
                  <span className="dashboard-mini-label">
                    AI + OCR
                  </span>
                </div>
                <p>{t('averageConfidence')}</p>
                <strong>
                  {analytics.averageConfidence.toFixed(0)}%
                </strong>
                <small>{t('acrossSavedInspections')}</small>
              </article>

              <article className="dashboard-kpi">
                <div className="dashboard-kpi-top">
                  <span>04</span>
                  <span className="dashboard-alert-dot" />
                </div>
                <p>{t('needsAttention')}</p>
                <strong>{analytics.manualReviews}</strong>
                <small>
                  {analytics.totalViolations} {t('totalViolations')}
                </small>
              </article>
            </section>

            <section className="dashboard-main-grid">
              <article className="dashboard-panel dashboard-compliance-panel">
                <div className="dashboard-panel-header">
                  <div>
                    <p className="dashboard-panel-kicker">
                      {t('complianceOverview')}
                    </p>
                    <h2>{t('inspectionOutcomes')}</h2>
                  </div>
                  <span className="dashboard-panel-index">
                    01
                  </span>
                </div>

                <div className="compliance-chart-wrap">
                  <div
                    className="compliance-donut"
                    style={{
                      background:
                        analytics.total > 0
                          ? `conic-gradient(
                              #8f3f35 0 ${100 - analytics.complianceRate}%,
                              #355844 ${100 - analytics.complianceRate}% 100%
                            )`
                          : 'conic-gradient(#d8d1c5 0 100%)',
                    }}
                  >
                    <div className="compliance-donut-inner">
                      <strong>
                        {analytics.complianceRate.toFixed(0)}%
                      </strong>
                      <span>{t('compliant').toLowerCase()}</span>
                    </div>
                  </div>

                  <div className="compliance-legend">
                    <div>
                      <span className="legend-marker legend-safe" />
                      <div>
                        <strong>{analytics.compliant}</strong>
                        <span>{t('compliant')}</span>
                      </div>
                    </div>

                    <div>
                      <span className="legend-marker legend-danger" />
                      <div>
                        <strong>{analytics.nonCompliant}</strong>
                        <span>{t('nonCompliant')}</span>
                      </div>
                    </div>

                    <div>
                      <span className="legend-marker legend-review" />
                      <div>
                        <strong>{analytics.manualReviews}</strong>
                        <span>{t('manualReview')}</span>
                      </div>
                    </div>
                  </div>
                </div>
              </article>

              <article className="dashboard-panel dashboard-activity-panel">
                <div className="dashboard-panel-header">
                  <div>
                    <p className="dashboard-panel-kicker">
                      {t('activity')}
                    </p>
                    <h2>{t('last7Days')}</h2>
                  </div>
                  <span className="dashboard-panel-index">
                    02
                  </span>
                </div>

                <div className="activity-chart">
                  {analytics.lastSevenDays.map((day) => {
                    const height =
                      analytics.lastSevenDays.every(
                        (item) => item.count === 0,
                      )
                        ? 4
                        : Math.max(
                            8,
                            (day.count /
                              Math.max(
                                ...analytics.lastSevenDays.map(
                                  (item) => item.count,
                                ),
                                1,
                              )) *
                              100,
                          )

                    return (
                      <div
                        key={day.key}
                        className="activity-column"
                      >
                        <div className="activity-bar-wrap">
                          <span className="activity-value">
                            {day.count}
                          </span>
                          <div
                            className="activity-bar"
                            style={{
                              height: `${height}%`,
                            }}
                          />
                        </div>
                        <span className="activity-label">
                          {day.label}
                        </span>
                      </div>
                    )
                  })}
                </div>

                <div className="activity-summary">
                  <span>
                    <i className="summary-safe" />
                    {t('compliant')}
                  </span>
                  <span>
                    <i className="summary-danger" />
                    {t('nonCompliant')}
                  </span>
                </div>
              </article>
            </section>

            <section className="dashboard-secondary-grid">
              <article className="dashboard-panel">
                <div className="dashboard-panel-header">
                  <div>
                    <p className="dashboard-panel-kicker">
                      {t('ruleAnalysis')}
                    </p>
                    <h2>{t('topViolations')}</h2>
                  </div>
                  <span className="dashboard-panel-index">
                    03
                  </span>
                </div>

                {analytics.topViolations.length === 0 ? (
                  <div className="dashboard-empty-state">
                    <span>✓</span>
                    <p>{t('noRecordedRuleViolations')}</p>
                  </div>
                ) : (
                  <div className="violation-list">
                    {analytics.topViolations.map(
                      ([ruleId, count], index) => {
                        const maxCount =
                          analytics.topViolations[0]?.[1] ?? 1
                        const width =
                          (count / maxCount) * 100

                        return (
                          <div
                            key={ruleId}
                            className="violation-row"
                          >
                            <div className="violation-row-top">
                              <span>
                                <b>{String(index + 1).padStart(2, '0')}</b>
                                {ruleId}
                              </span>
                              <strong>{count}</strong>
                            </div>

                            <div className="violation-track">
                              <div
                                className="violation-fill"
                                style={{ width: `${width}%` }}
                              />
                            </div>
                          </div>
                        )
                      },
                    )}
                  </div>
                )}
              </article>

              <article className="dashboard-panel">
                <div className="dashboard-panel-header">
                  <div>
                    <p className="dashboard-panel-kicker">
                      {t('officerWorkload')}
                    </p>
                    <h2>{t('attentionQueue')}</h2>
                  </div>
                  <span className="dashboard-panel-index">
                    04
                  </span>
                </div>

                <div className="attention-grid">
                  <div>
                    <span>{t('manualReview')}</span>
                    <strong>{analytics.manualReviews}</strong>
                    <small>{t('inspectionsRequiringAttention')}</small>
                  </div>

                  <div>
                    <span>{t('criticalViolations')}</span>
                    <strong>{analytics.totalViolations}</strong>
                    <small>{t('rulesTriggeredAcrossRecords')}</small>
                  </div>
                </div>

                <button
                  type="button"
                  className="dashboard-outline-action"
                  onClick={onOpenHistory}
                >
                  {t('viewInspectionHistory')}
                </button>
              </article>
            </section>

            <section className="dashboard-panel dashboard-recent-panel">
              <div className="dashboard-panel-header">
                <div>
                  <p className="dashboard-panel-kicker">
                    {t('activityLog')}
                  </p>
                  <h2>{t('recentInspections')}</h2>
                </div>

                <button
                  type="button"
                  className="dashboard-panel-link"
                  onClick={onOpenHistory}
                >
                  {t('viewAll')}
                </button>
              </div>

              {recentRecords.length === 0 ? (
                <div className="dashboard-empty-state">
                  <span>—</span>
                  <p>{t('noInspectionsYet')}</p>
                </div>
              ) : (
                <div className="recent-table">
                  <div className="recent-table-head">
                    <span>{t('product')}</span>
                    <span>{t('date')}</span>
                    <span>{t('score')}</span>
                    <span>{t('status')}</span>
                  </div>

                  {recentRecords.map((record) => {
                    const extracted =
                      record.extracted_fields ?? {}

                    const productName =
                      typeof extracted.product_name === 'string' &&
                      extracted.product_name.trim()
                        ? extracted.product_name
                        : typeof extracted.generic_name === 'string' &&
                            extracted.generic_name.trim()
                          ? extracted.generic_name
                          : record.product_id ||
                            t('productInspection')

                    return (
                      <div
                        key={record.id}
                        className="recent-table-row"
                      >
                        <div>
                          <strong>{productName}</strong>
                          <span>
                            {record.product_id ||
                              t('inspectionRecord')}
                          </span>
                        </div>

                        <span className="recent-date">
                          {formatDate(record.created_at)}
                          <small>
                            {formatTime(record.created_at)}
                          </small>
                        </span>

                        <strong className="recent-score">
                          {Number(
                            record.confidence_score || 0,
                          ).toFixed(0)}
                          %
                        </strong>

                        <span
                          className={
                            record.is_compliant
                              ? 'dashboard-status status-compliant'
                              : 'dashboard-status status-noncompliant'
                          }
                        >
                          {record.is_compliant
                            ? t('compliant')
                            : t('nonCompliant')}
                        </span>
                      </div>
                    )
                  })}
                </div>
              )}
            </section>

            <section className="dashboard-quick-actions">
              <button
                type="button"
                className="quick-action quick-action-primary"
                onClick={onOpenScan}
              >
                <span className="quick-action-icon">+</span>
                <div>
                  <strong>{t('startNewInspection')}</strong>
                  <small>
                    {t('scanFrontBackSideLabels')}
                  </small>
                </div>
                <span className="quick-action-arrow">→</span>
              </button>

              <button
                type="button"
                className="quick-action"
                onClick={onOpenHistory}
              >
                <span className="quick-action-icon">◷</span>
                <div>
                  <strong>{t('reviewInspectionHistory')}</strong>
                  <small>
                    {t('browsePreviouslyRecordedProducts')}
                  </small>
                </div>
                <span className="quick-action-arrow">→</span>
              </button>
            </section>
          </>
        )}
      </main>
    </div>
  )
}
