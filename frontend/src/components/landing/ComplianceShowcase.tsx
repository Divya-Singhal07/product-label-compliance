/** Illustrative marketing composition. Not live OCR or rule-engine output. */
export function ComplianceShowcase() {
  return (
    <section className="score-section" id="compliance">
      <div className="score-copy">
        <p className="section-index light">03 — Result</p>
        <h2>
          A score you
          <br />
          can stand behind.
        </h2>
        <p>
          Compliant means no high-severity violations. Medium and low findings
          still surface for review. Manual review flags low-confidence reads.
        </p>
      </div>
      <div className="score-stage">
        <p className="score-kicker">COMPLIANCE SCORE</p>
        <p className="score-giant">94 / 100</p>
        <p className="score-status">COMPLIANT</p>
        <dl className="score-meta">
          <div>
            <dt>Rules checked</dt>
            <dd>3 layers</dd>
          </div>
          <div>
            <dt>Critical violations</dt>
            <dd>0</dd>
          </div>
          <div>
            <dt>Warnings</dt>
            <dd>2</dd>
          </div>
        </dl>
      </div>
    </section>
  )
}
