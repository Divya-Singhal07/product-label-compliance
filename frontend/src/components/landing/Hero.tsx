import { useEffect, useState } from 'react'
import { useI18n } from '../../i18n/I18nContext'

interface HeroProps {
  onScan: () => void
  onExplore: () => void
}

const HERO_IMAGES = [
  {
    src: '/sih-hero-bg.jpg',
    alt: 'Smart India Hackathon SIH26034 Legal Metrology Solution',
    tag: '01 / SIH26034 OFFICIAL SOLUTION'
  },
  {
    src: '/hero-bg-1.jpg',
    alt: 'Premium packaged consumer goods inspection scene',
    tag: '02 / PACKAGED COMMODITIES AUDIT'
  },
  {
    src: '/hero-bg-2.jpg',
    alt: 'Close-up product label with printed legal metrology declarations',
    tag: '03 / MANDATORY DECLARATIONS VERIFICATION'
  },
  {
    src: '/hero-bg-3.jpg',
    alt: 'Product packaging being visually inspected on auditor workbench',
    tag: '04 / LEGAL METROLOGY RULE 6 AUDIT'
  },
  {
    src: '/hero-bg-4.jpg',
    alt: 'Multiple packaged commodities arranged editorially',
    tag: '05 / COMPLIANCE ENGINE'
  },
  {
    src: '/hero-bg-5.jpg',
    alt: 'Product label with EAN-13 barcode and QR compliance context',
    tag: '06 / BARCODE & QR TRACEABILITY'
  }
]

export function Hero({ onScan, onExplore }: HeroProps) {
  const { t } = useI18n()
  const [activeIndex, setActiveIndex] = useState(0)
  const [isPaused, setIsPaused] = useState(false)

  useEffect(() => {
    if (isPaused) return
    const timer = setInterval(() => {
      setActiveIndex((prev) => (prev + 1) % HERO_IMAGES.length)
    }, 5000)
    return () => clearInterval(timer)
  }, [isPaused])

  const current = HERO_IMAGES[activeIndex]

  return (
    <section 
      className="hero-fullbleed" 
      id="top"
      onMouseEnter={() => setIsPaused(true)}
      onMouseLeave={() => setIsPaused(false)}
    >
      {/* BACKGROUND ROTATOR LAYERS (Full-bleed landscape images) */}
      <div className="hero-bg-stack">
        {HERO_IMAGES.map((item, idx) => {
          const isActive = idx === activeIndex
          return (
            <div
              key={item.src}
              className={`hero-bg-layer ${isActive ? 'active' : ''}`}
            >
              <img
                src={item.src}
                alt={item.alt}
                className={`hero-bg-img ${isActive ? 'ken-burns' : ''}`}
              />
            </div>
          )
        })}

        {/* Softened Dark Overlay for Maximum Typography Readability */}
        <div className="hero-bg-overlay" />
      </div>

      {/* CENTERED CONTENT OVERLAY */}
      <div className="hero-content">
        <div className="hero-badge">
          <span className="hero-badge-pulse" />
          <p className="eyebrow">{t('sihLegalMetrology')}</p>
        </div>

        <h1 className="hero-title">
          COMPLIANCE,
          <br />
          MADE SIMPLE.
        </h1>

        <p className="lede">
          {t('aiPoweredVerification')}
        </p>

        <div className="hero-actions">
          <button type="button" className="btn-solid" onClick={onScan}>
            {t('scanAProduct')} →
          </button>

          <button type="button" className="btn-ghost" onClick={onExplore}>
            {t('exploreHowItWorks')}
          </button>
        </div>

        {/* SUBTLE MINIMAL SLIDE INDICATORS */}
        <div className="hero-slide-indicators" aria-label="Inspection Scene Rotator">
          <span className="hero-scene-tag">{current.tag}</span>
          <div className="indicators-dots">
            {HERO_IMAGES.map((_, idx) => (
              <button
                key={idx}
                type="button"
                className={`indicator-btn ${idx === activeIndex ? 'active' : ''}`}
                onClick={() => setActiveIndex(idx)}
                aria-label={`Go to scene ${idx + 1}`}
              >
                <span className="indicator-line">
                  <span 
                    className="indicator-progress" 
                    style={{
                      animationDuration: '5000ms',
                      animationPlayState: idx === activeIndex && !isPaused ? 'running' : 'paused'
                    }}
                  />
                </span>
              </button>
            ))}
          </div>
        </div>
      </div>
    </section>
  )
}