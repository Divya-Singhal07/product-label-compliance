const STEPS = [
  {
    n: '01',
    title: 'SCAN',
    body: 'Upload front, back and side label images.',
  },
  {
    n: '02',
    title: 'EXTRACT',
    body: 'OCR extracts relevant declaration fields.',
  },
  {
    n: '03',
    title: 'VERIFY',
    body: 'The compliance rule engine checks applicable rules.',
  },
  {
    n: '04',
    title: 'REPORT',
    body: 'Receive a compliance score, violations, warnings and recommendations.',
  },
]

export function HowItWorks() {
  return (
    <section className="how" id="how">
      <p className="section-index">02 — Process</p>
      <h2>How Label Lens works</h2>
      <ol className="how-list">
        {STEPS.map((step) => (
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
