import { useI18n } from '../../i18n/I18nContext'

interface FooterProps {
  onScan: () => void
  onJump: (id: string) => void
}

export function Footer({ onScan, onJump }: FooterProps) {
  const { t } = useI18n()
  return (
    <footer className="site-footer">
      <div>
        <p className="wordmark">Label Lens</p>
        <p>SIH26034</p>
        <p>Legal Metrology Compliance</p>
      </div>
      <div className="footer-links">
        <button type="button" onClick={() => onJump('product')}>
          {t('product')}
        </button>
        <button type="button" onClick={() => onJump('how')}>
          {t('howItWorks')}
        </button>
        <button type="button" onClick={onScan}>
          {t('contact')}
        </button>
      </div>
    </footer>
  )
}
