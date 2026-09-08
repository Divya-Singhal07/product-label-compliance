import { useI18n } from '../../i18n/I18nContext'

export function Intro() {
  const { t } = useI18n()

  return (
    <section className="intro" id="product">
      <p className="section-index">{t('productSection')}</p>
      <h2>
        {t('oneLabel')}
        <br />
        {t('dozensDeclarations')}
        <br />
        {t('oneComplianceCheck')}
      </h2>
      <p className="intro-body">
{t('introBody')}
      </p>
    </section>
  )
}
