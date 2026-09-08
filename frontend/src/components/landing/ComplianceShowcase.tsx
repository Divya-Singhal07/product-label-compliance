import { useI18n } from '../../i18n/I18nContext'

/** Illustrative marketing composition. Not live OCR or rule-engine output. */
export function ComplianceShowcase() {
  const { t } = useI18n()
  return (
    <section className="score-section" id="compliance">
      <div className="score-copy">
        <p className="section-index light">03 — Result</p>
        <h2>{t('scoreYouCanStandBehind')}</h2>
        <p>
          {t('complianceExplanation')}
        </p>
      </div>
      <div className="score-stage">
        <p className="score-kicker">{t('complianceScore')}</p>
        <p className="score-giant">94 / 100</p>
        <p className="score-status">{t('compliant')}</p>
        <dl className="score-meta">
          <div>
            <dt>{t('rulesChecked')}</dt>
            <dd>3 layers</dd>
          </div>
          <div>
            <dt>{t('criticalViolations')}</dt>
            <dd>0</dd>
          </div>
          <div>
            <dt>{t('warnings')}</dt>
            <dd>2</dd>
          </div>
        </dl>
      </div>
    </section>
  )
}
