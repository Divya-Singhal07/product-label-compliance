import { useI18n } from '../../i18n/I18nContext'

interface HeroProps {
  onScan: () => void
  onExplore: () => void
}

export function Hero({ onScan, onExplore }: HeroProps) {
  const { t } = useI18n()

  return (
    <section className="hero" id="top">
      <div className="hero-copy">
        <p className="eyebrow">{t('sihLegalMetrology')}</p>

        <h1>
          COMPLIANCE,
          <br />
          MADE SIMPLE.
        </h1>

        <p className="lede">
          {t('aiPoweredVerification')}
        </p>

        <div className="hero-actions">
          <button type="button" className="btn-solid" onClick={onScan}>
            {t('scanAProduct')}
          </button>

          <button type="button" className="btn-ghost" onClick={onExplore}>
            {t('exploreHowItWorks')}
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