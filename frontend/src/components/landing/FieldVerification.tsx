const FIELDS: { label: string; value: string; state: 'ok' | 'warn' | 'miss' }[] =
  [
    { label: 'Brand', value: 'Present', state: 'ok' },
    { label: 'Product Name', value: 'Present', state: 'ok' },
    { label: 'Net Quantity', value: '500 g', state: 'ok' },
    { label: 'MRP', value: 'Declaration incomplete', state: 'warn' },
    { label: 'Manufacturer', value: 'Present', state: 'ok' },
    { label: 'Consumer Care', value: 'Missing', state: 'miss' },
    { label: 'Country of Origin', value: 'India', state: 'ok' },
    { label: 'Manufacturing Date', value: '03 / 2026', state: 'ok' },
  ]

const MARK = { ok: 'VERIFIED', warn: 'WARNING', miss: 'MISSING' }

export function FieldVerification() {
  return (
    <section className="fields-section">
      <div className="fields-head">
        <p className="section-index">04 — Extraction</p>
        <h2>
          Every declaration,
          <br />
          in one reading.
        </h2>
      </div>
      <ul className="field-rows">
        {FIELDS.map((field) => (
          <li key={field.label} className={`field-row is-${field.state}`}>
            <span className="field-label">{field.label}</span>
            <span className="field-value">{field.value}</span>
            <span className="field-mark">{MARK[field.state]}</span>
          </li>
        ))}
      </ul>
    </section>
  )
}
