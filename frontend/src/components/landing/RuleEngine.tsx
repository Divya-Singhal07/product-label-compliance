const RULES: { name: string; state: 'pass' | 'warn' }[] = [
  { name: 'MRP Declaration', state: 'pass' },
  { name: 'Net Quantity', state: 'pass' },
  { name: 'Manufacturer Details', state: 'pass' },
  { name: 'Consumer Care', state: 'warn' },
  { name: 'Country of Origin', state: 'pass' },
]

export function RuleEngine() {
  return (
    <section className="rules-section" id="about">
      <p className="section-index">05 — Engine</p>
      <div className="rules-layout">
        <h2>
          Universal.
          <br />
          Category.
          <br />
          Product.
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
