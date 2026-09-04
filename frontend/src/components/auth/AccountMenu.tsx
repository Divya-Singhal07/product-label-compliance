import { useState } from 'react'
import { logout } from '../../services/auth'
import type { User } from '../../types/auth'

interface AccountMenuProps {
  user: User
  onLogout: () => void
}

export function AccountMenu({ user, onLogout }: AccountMenuProps) {
  const [loading, setLoading] = useState(false)

  async function handleLogout() {
    setLoading(true)
    try {
      await logout()
    } finally {
      setLoading(false)
      onLogout()
    }
  }

  return (
    <div className="account-menu">
      <span className="account-email" title={user.email}>
        {user.email}
      </span>
      <button
        id="account-logout-btn"
        type="button"
        className="nav-cta"
        onClick={handleLogout}
        disabled={loading}
      >
        {loading ? '…' : 'Log out'}
      </button>
    </div>
  )
}
