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
  const [jobId, setJobId] = useState<string | null>(null)

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

  function openScan() {
    if (user) {
      setMode('workspace')
      setWorkspaceView('scan')
      window.scrollTo(0, 0)
    } else {
      setMode('auth')
    }
  }

  function handleAuthSuccess(loggedInUser: User) {
    setUser(loggedInUser)
    setMode('workspace')
    setWorkspaceView('scan')
    window.scrollTo(0, 0)
  }

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
      setJobId(response.job_id)
      setWorkspaceView('result')
    } catch (error) {
      console.error('Analysis failed', error)
      alert(error instanceof Error ? error.message : 'Failed to analyze product. Please try again.')
    } finally {
      setIsProcessing(false)
    }
  }

  if (!authChecked) {
    return null
  }

  return (
    <>
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
          jobId={jobId}
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
