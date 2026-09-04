import { useEffect, useMemo, useState } from 'react'
import { AuthModal } from './components/auth/AuthModal'
import { LandingPage } from './pages/LandingPage'
import { WorkspacePage } from './pages/WorkspacePage'
import { getMe } from './services/auth'
import { analyzeProduct } from './services/api'
import type { AppMode, LabelView, WorkspaceView } from './types/app'
import type { AuthMode, User } from './types/auth'
import type { ComplianceResult, MergedFields } from './types/compliance'

function App() {
  const [mode, setMode] = useState<AppMode>('landing')
  const [authInitialMode, setAuthInitialMode] = useState<AuthMode>('login')
  const [user, setUser] = useState<User | null>(null)
  const [authChecked, setAuthChecked] = useState(false)
  const [workspaceView, setWorkspaceView] = useState<WorkspaceView>('scan')
  const [files, setFiles] = useState<Partial<Record<LabelView, File>>>({})
  const [isProcessing, setIsProcessing] = useState(false)
  const [fields, setFields] = useState<MergedFields | null>(null)
  const [result, setResult] = useState<ComplianceResult | null>(null)

  // Check session on startup and query parameters (?mode=forgot|login|register)
  useEffect(() => {
    getMe().then((u) => {
      setUser(u)
      setAuthChecked(true)
      const params = new URLSearchParams(window.location.search)
      const qMode = params.get('mode')
      if (qMode === 'forgot' || qMode === 'login' || qMode === 'register') {
        if (!u) {
          setAuthInitialMode(qMode as AuthMode)
          setMode('auth')
        }
      }
    })
  }, [])

  const previewUrls = useMemo(() => {
    const urls: Partial<Record<LabelView, string>> = {}
    for (const view of Object.keys(files) as LabelView[]) {
      const file = files[view]
      if (file) urls[view] = URL.createObjectURL(file)
    }
    return urls
  }, [files])

  useEffect(() => {
    return () => {
      for (const url of Object.values(previewUrls)) {
        if (url) URL.revokeObjectURL(url)
      }
    }
  }, [previewUrls])

  /** Called whenever any "Scan Product" button is pressed. */
  function openScan() {
    if (user) {
      // Already authenticated — go straight to workspace
      setMode('workspace')
      setWorkspaceView('scan')
      window.scrollTo(0, 0)
    } else {
      // Not authenticated — show the auth modal
      setMode('auth')
    }
  }

  /** Called by AuthModal on successful login/register. */
  function handleAuthSuccess(loggedInUser: User) {
    setUser(loggedInUser)
    setMode('workspace')
    setWorkspaceView('scan')
    window.scrollTo(0, 0)
  }

  /** Called by AccountMenu logout button. */
  function handleLogout() {
    setUser(null)
    setMode('landing')
  }

  async function handleAnalyze() {
    setIsProcessing(true)
    try {
      const response = await analyzeProduct({ views: files })
      setFields(response.merged_fields)
      setResult(response.compliance_result ?? null)
      setWorkspaceView('result')
    } catch (error) {
      console.error('Analysis failed', error)
      alert('Failed to analyze product. Please try again.')
    } finally {
      setIsProcessing(false)
    }
  }

  // Don't render until we've resolved the session (avoids flash)
  if (!authChecked) {
    return null
  }

  return (
    <>
      {/* Auth modal — sits on top of whatever page is showing */}
      {mode === 'auth' && (
        <AuthModal
          initialMode={authInitialMode}
          onSuccess={handleAuthSuccess}
          onClose={() => {
            setMode('landing')
            if (window.location.search) {
              window.history.replaceState({}, '', window.location.pathname)
            }
          }}
        />
      )}

      {mode === 'workspace' ? (
        <WorkspacePage
          user={user}
          view={workspaceView}
          files={files}
          previewUrls={previewUrls}
          isProcessing={isProcessing}
          fields={fields}
          result={result}
          onSelect={(view, file) =>
            setFiles((current) => ({ ...current, [view]: file }))
          }
          onClear={(view) =>
            setFiles((current) => {
              const next = { ...current }
              delete next[view]
              return next
            })
          }
          onAnalyze={handleAnalyze}
          onBackHome={() => setMode('landing')}
          onOpenScan={() => setWorkspaceView('scan')}
          onLogout={handleLogout}
        />
      ) : (
        <LandingPage
          user={user}
          onScan={openScan}
          onLogout={handleLogout}
        />
      )}
    </>
  )
}

export default App
