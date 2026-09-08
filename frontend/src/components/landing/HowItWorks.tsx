import { useI18n } from '../../i18n/I18nContext'

export function HowItWorks() {
  const { t } = useI18n()

  const steps = [
    {
      n: '01',
      title: 'SCAN',
      body: t('uploadLabelImages'),
    },
    {
      n: '02',
      title: 'EXTRACT',
      body: t('ocrExtractsFields'),
    },
    {
      n: '03',
      title: 'VERIFY',
      body: t('ruleEngineChecks'),
    },
    {
      n: '04',
      title: 'REPORT',
      body: t('receiveResults'),
    },
  ]

  return (
    <section className="how" id="how">
      <p className="section-index">02 — Process</p>
      <h2>{t('howItWorks')}</h2>

      <ol className="how-list">
        {steps.map((step) => (
          <li key={step.n}>
            <span className="how-n">{step.n}</span>

            <div>
              <h3>{step.title}</h3>
              <p>{step.body}</p>
            </div>
          </li>
        ))}
      </ol>
    </section>
  )
}
