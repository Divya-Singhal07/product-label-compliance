import { useEffect, useMemo, useState } from 'react'
import { LandingPage } from './pages/LandingPage'
import { WorkspacePage } from './pages/WorkspacePage'
import type { AppMode, LabelView, WorkspaceView } from './types/app'
import type { ComplianceResult, MergedFields } from './types/compliance'

function App() {
  const [mode, setMode] = useState<AppMode>('landing')
  const [workspaceView, setWorkspaceView] = useState<WorkspaceView>('scan')
  const [files, setFiles] = useState<Partial<Record<LabelView, File>>>({})
  const [isProcessing, setIsProcessing] = useState(false)
  const [fields] = useState<MergedFields | null>(null)
  const [result] = useState<ComplianceResult | null>(null)

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
    setMode('workspace')
    setWorkspaceView('scan')
    window.scrollTo(0, 0)
  }

  function handleAnalyze() {
    setIsProcessing(true)
    window.setTimeout(() => {
      setIsProcessing(false)
      setWorkspaceView('result')
    }, 800)
  }

  if (mode === 'landing') {
    return <LandingPage onScan={openScan} />
  }

  return (
    <WorkspacePage
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
    />
  )
}

export default App
