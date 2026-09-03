interface HeroProps {
  onScan: () => void
  onExplore: () => void
}

export function Hero({ onScan, onExplore }: HeroProps) {
  return (
    <section className="hero" id="top">
      <div className="hero-copy">
        <p className="eyebrow">SIH26034 · Legal Metrology</p>

        <h1>
          COMPLIANCE,
          <br />
          MADE SIMPLE.
        </h1>

        <p className="lede">
          AI-powered packaged commodity label verification.
        </p>

        <div className="hero-actions">
          <button type="button" className="btn-solid" onClick={onScan}>
            SCAN A PRODUCT →
          </button>

          <button type="button" className="btn-ghost" onClick={onExplore}>
            EXPLORE HOW IT WORKS
          </button>
        </div>
      </div>

      <div className="hero-visual">
        <img
          src="/hero-product.png"
          alt="AI-powered product label compliance scan"
        />
      </div>
    </section>
  )
}