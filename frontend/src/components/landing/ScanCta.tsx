import { useI18n } from '../../i18n/I18nContext'

interface ScanCtaProps {
  onScan: () => void
}

export function ScanCta({ onScan }: ScanCtaProps) {
  const { t } = useI18n()
  return (
    <section className="cta-band">
      <h2>
        {t('readyToCheck')}
      </h2>
      <button type="button" className="btn-solid invert" onClick={onScan}>
        {t('startScanning')}
      </button>
    </section>
  )
}
