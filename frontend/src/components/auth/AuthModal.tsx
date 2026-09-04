import { useEffect, useRef, useState } from 'react'
import { forgotPassword, login, register } from '../../services/auth'
import type { AuthMode, User } from '../../types/auth'

interface AuthModalProps {
  initialMode?: AuthMode
  onSuccess: (user: User) => void
  onClose: () => void
}

export function AuthModal({ initialMode = 'login', onSuccess, onClose }: AuthModalProps) {
  const [mode, setMode] = useState<AuthMode>(initialMode)
  const [fullName, setFullName] = useState('')
  const [officerId, setOfficerId] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [department, setDepartment] = useState('')
  const [role, setRole] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const overlayRef = useRef<HTMLDivElement>(null)

  // Close on Escape key
  useEffect(() => {
    function handleKey(e: KeyboardEvent) {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', handleKey)
    return () => document.removeEventListener('keydown', handleKey)
  }, [onClose])

  // Prevent body scroll while open
  useEffect(() => {
    document.body.style.overflow = 'hidden'
    return () => {
      document.body.style.overflow = ''
    }
  }, [])

  function switchMode(next: AuthMode) {
    setMode(next)
    setError(null)
    setNotice(null)
    setPassword('')
    setConfirmPassword('')
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    setNotice(null)
    setLoading(true)

    try {
      if (mode === 'login') {
        if (!officerId.trim()) {
          setError('Please enter your officer ID.')
          setLoading(false)
          return
        }
        if (!password) {
          setError('Please enter your password.')
          setLoading(false)
          return
        }
        const result = await login({ officer_id: officerId.trim(), password })
        if ('error' in result) {
          setError(result.error)
        } else {
          onSuccess({ email: result.email, officer_id: officerId.trim() })
        }
      } else if (mode === 'forgot') {
        if (!officerId.trim()) {
          setError('Please enter your officer ID.')
          setLoading(false)
          return
        }
        const result = await forgotPassword(officerId.trim())
        if (result.error) {
          setError(result.error)
        } else {
          setNotice(result.message || 'Password reset link sent! Check your registered email inbox.')
        }
      } else {
        if (!fullName.trim()) {
          setError('Please enter your full name.')
          setLoading(false)
          return
        }
        if (!officerId.trim()) {
          setError('Please enter your officer ID.')
          setLoading(false)
          return
        }
        if (!email.trim()) {
          setError('Please enter your official email.')
          setLoading(false)
          return
        }
        if (!department.trim()) {
          setError('Please enter your department.')
          setLoading(false)
          return
        }
        if (!role) {
          setError('Please select your role.')
          setLoading(false)
          return
        }
        if (password !== confirmPassword) {
          setError('Passwords do not match.')
          setLoading(false)
          return
        }
        if (password.length < 6) {
          setError('Password must be at least 6 characters.')
          setLoading(false)
          return
        }

        const result = await register({
          full_name: fullName.trim(),
          officer_id: officerId.trim(),
          email: email.trim(),
          password,
          confirm_password: confirmPassword,
          department: department.trim(),
          role,
        })

        if ('error' in result) {
          setError(result.error)
        } else if ('notice' in result) {
          setNotice(result.notice)
          setMode('login')
        } else {
          onSuccess({
            email: result.email,
            officer_id: officerId,
            full_name: fullName,
            department,
            role,
          })
        }
      }
    } catch {
      setError('Something went wrong. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  function handleOverlayClick(e: React.MouseEvent) {
    if (e.target === overlayRef.current) onClose()
  }

  return (
    <div
      className="auth-overlay"
      ref={overlayRef}
      onClick={handleOverlayClick}
      aria-modal="true"
      role="dialog"
    >
      <div className={`auth-modal ${mode === 'register' ? 'auth-modal-wide' : ''}`}>
        {/* Close button */}
        <button className="auth-modal-close" onClick={onClose} aria-label="Close">
          ✕
        </button>

        {/* Header */}
        <p className="eyebrow">SIH26034 · Legal Metrology</p>
        <h2 className="auth-modal-title">
          {mode === 'login' ? (
            <>
              SIGN IN,
              <br />
              THEN SCAN.
            </>
          ) : mode === 'forgot' ? (
            <>
              RESET YOUR
              <br />
              PASSWORD.
            </>
          ) : (
            <>
              CREATE
              <br />
              AN ACCOUNT.
            </>
          )}
        </h2>
        <p className="auth-modal-lede">
          {mode === 'login'
            ? 'Log in to continue packaged commodity label verification.'
            : mode === 'forgot'
            ? "Enter your Officer ID and we'll send a reset link to your registered email."
            : 'Register to start AI-powered label compliance checks.'}
        </p>

        {/* Tab switcher */}
        <div className="auth-tabs" role="tablist">
          <button
            role="tab"
            aria-selected={mode === 'login'}
            className={mode === 'login' ? 'auth-tab active' : 'auth-tab'}
            onClick={() => switchMode('login')}
            type="button"
          >
            Log In
          </button>
          <button
            role="tab"
            aria-selected={mode === 'register'}
            className={mode === 'register' ? 'auth-tab active' : 'auth-tab'}
            onClick={() => switchMode('register')}
            type="button"
          >
            Register
          </button>
        </div>

        {/* Banner */}
        {error && (
          <p className="auth-banner auth-banner-error" role="alert">
            {error}
          </p>
        )}
        {notice && (
          <p className="auth-banner auth-banner-ok" role="status">
            {notice}
          </p>
        )}

        {/* Form */}
        <form className="auth-modal-form" onSubmit={handleSubmit} noValidate>
          {mode === 'login' ? (
            <>
              <label>
                <span>Officer ID</span>
                <input
                  id="auth-officer-id"
                  type="text"
                  value={officerId}
                  onChange={(e) => setOfficerId(e.target.value)}
                  autoComplete="username"
                  placeholder="e.g. OFC-2024-001"
                  required
                  disabled={loading}
                />
              </label>

              <label>
                <span>Password</span>
                <input
                  id="auth-password"
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  autoComplete="current-password"
                  placeholder="Enter your password"
                  required
                  minLength={6}
                  disabled={loading}
                />
              </label>

              <div className="auth-forgot-row">
                <button
                  type="button"
                  className="auth-forgot-link"
                  onClick={() => switchMode('forgot')}
                  disabled={loading}
                >
                  Forgot password?
                </button>
              </div>
            </>
          ) : mode === 'forgot' ? (
            <>
              <label>
                <span>Officer ID</span>
                <input
                  id="forgot-officer-id"
                  type="text"
                  value={officerId}
                  onChange={(e) => setOfficerId(e.target.value)}
                  autoComplete="username"
                  placeholder="e.g. OFC-2024-001"
                  required
                  disabled={loading}
                />
              </label>
            </>
          ) : (
            <>
              <div className="form-row">
                <label>
                  <span>Full Name</span>
                  <input
                    id="reg-full-name"
                    type="text"
                    value={fullName}
                    onChange={(e) => setFullName(e.target.value)}
                    autoComplete="name"
                    placeholder="Your full name"
                    required
                    disabled={loading}
                  />
                </label>
                <label>
                  <span>Officer ID</span>
                  <input
                    id="reg-officer-id"
                    type="text"
                    value={officerId}
                    onChange={(e) => setOfficerId(e.target.value)}
                    autoComplete="username"
                    placeholder="e.g. OFC-2024-001"
                    required
                    disabled={loading}
                  />
                </label>
              </div>

              <label>
                <span>Official Email</span>
                <input
                  id="reg-email"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  autoComplete="email"
                  placeholder="you@department.gov.in"
                  required
                  disabled={loading}
                />
              </label>

              <div className="form-row">
                <label>
                  <span>Password</span>
                  <input
                    id="reg-password"
                    type="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    autoComplete="new-password"
                    placeholder="Min. 6 characters"
                    required
                    minLength={6}
                    disabled={loading}
                  />
                </label>
                <label>
                  <span>Confirm Password</span>
                  <input
                    id="reg-confirm-password"
                    type="password"
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    autoComplete="new-password"
                    placeholder="Repeat password"
                    required
                    minLength={6}
                    disabled={loading}
                  />
                </label>
              </div>

              <div className="form-row">
                <label>
                  <span>Department</span>
                  <input
                    id="reg-department"
                    type="text"
                    value={department}
                    onChange={(e) => setDepartment(e.target.value)}
                    placeholder="e.g. Legal Metrology Division"
                    required
                    disabled={loading}
                  />
                </label>
                <label>
                  <span>Role</span>
                  <select
                    id="reg-role"
                    value={role}
                    onChange={(e) => setRole(e.target.value)}
                    required
                    disabled={loading}
                  >
                    <option value="" disabled>
                      Select role
                    </option>
                    <option value="inspector">Inspector</option>
                    <option value="senior_inspector">Senior Inspector</option>
                    <option value="controller">Controller</option>
                    <option value="admin">Admin</option>
                  </select>
                </label>
              </div>
            </>
          )}

          <div className="auth-modal-actions">
            <button
              id={mode === 'forgot' ? 'auth-forgot-submit' : 'auth-submit'}
              type="submit"
              className="btn-solid"
              disabled={loading}
            >
              {loading
                ? 'Please wait…'
                : mode === 'login'
                ? 'Log in →'
                : mode === 'forgot'
                ? 'Send reset link →'
                : 'Create account →'}
            </button>
            <button
              type="button"
              className="btn-ghost"
              onClick={() => {
                if (mode === 'forgot') switchMode('login')
                else switchMode(mode === 'login' ? 'register' : 'login')
              }}
              disabled={loading}
            >
              {mode === 'forgot'
                ? 'Back to log in'
                : mode === 'login'
                ? 'Need an account?'
                : 'Already registered?'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
