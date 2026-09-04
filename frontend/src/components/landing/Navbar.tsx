import { AccountMenu } from '../auth/AccountMenu'
import type { User } from '../../types/auth'

interface NavbarProps {
  user: User | null
  onScan: () => void
  onJump: (id: string) => void
  onLogout: () => void
}

export function Navbar({ user, onScan, onJump, onLogout }: NavbarProps) {
  return (
    <header className="nav">
      <button type="button" className="wordmark" onClick={() => onJump('top')}>
        <img src="/logo.png" alt="Label Lens" className="brand-logo" />
      </button>

      <nav className="nav-links" aria-label="Landing">
        <button type="button" onClick={() => onJump('product')}>Product</button>
        <button type="button" onClick={() => onJump('how')}>How it Works</button>
        <button type="button" onClick={() => onJump('compliance')}>Compliance</button>
        <button type="button" onClick={() => onJump('about')}>About</button>
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
          Scan Product
        </button>
      )}
    </header>
  )
}
