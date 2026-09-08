import { useEffect, useState } from 'react'
import { AccountMenu } from '../auth/AccountMenu'
import type { User } from '../../types/auth'
import { useI18n } from '../../i18n/I18nContext'

interface NavbarProps {
  user: User | null
  onScan: () => void
  onJump: (id: string) => void
  onLogout: () => void
}

export function Navbar({ user, onScan, onJump, onLogout }: NavbarProps) {
  const { t } = useI18n()
  const [scrolled, setScrolled] = useState(false)

  useEffect(() => {
    const handleScroll = () => {
      setScrolled(window.scrollY > 20)
    }

    handleScroll()
    window.addEventListener('scroll', handleScroll, { passive: true })
    return () => window.removeEventListener('scroll', handleScroll)
  }, [])

  return (
    <header className={`nav ${scrolled ? 'scrolled' : ''}`}>
      <button type="button" className="wordmark" onClick={() => onJump('top')}>
        <img src="/logo.png" alt="Label Lens" className="brand-logo" />
      </button>

      <nav className="nav-links" aria-label="Landing">
        <button type="button" onClick={() => onJump('product')}>{t('product')}</button>
        <button type="button" onClick={() => onJump('how')}>{t('howItWorks')}</button>
        <button type="button" onClick={() => onJump('compliance')}>{t('compliance')}</button>
        <button type="button" onClick={() => onJump('about')}>{t('about')}</button>
      </nav>

      {user ? (
        <AccountMenu user={user} onLogout={onLogout} />
      ) : (
        <button
          id="navbar-scan-btn"
          type="button"
          className="nav-cta"
          onClick={onScan}
        >
          {t('scanProduct')}
        </button>
      )}
    </header>
  )
}
