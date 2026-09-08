import { useI18n } from '../../i18n/I18nContext'

const RULES: { name: string; state: 'pass' | 'warn' }[] = [
  { name: 'MRP Declaration', state: 'pass' },
  { name: 'Net Quantity', state: 'pass' },
  { name: 'Manufacturer Details', state: 'pass' },
  { name: 'Consumer Care', state: 'warn' },
  { name: 'Country of Origin', state: 'pass' },
]

export function RuleEngine() {
  const { t } = useI18n()
  return (
    <section className="rules-section" id="about">
      <p className="section-index">05 — Engine</p>
      <div className="rules-layout">
        <h2>
          {t('universal')}
          <br />
          {t('category')}
          <br />
          {t('productLevel')}
        </h2>
        <ul className="rule-rows">
          {RULES.map((rule) => (
            <li key={rule.name}>
              <span>{rule.name}</span>
              <span className={rule.state === 'pass' ? 'tick' : 'caution'}>
                {rule.state === 'pass' ? '✓' : '⚠'}
              </span>
            </li>
          ))}
        </ul>
      </div>
    </section>
  )
}
