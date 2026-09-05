import type { AnalyzeResponse } from '../types/compliance'

export type LabelView = 'front' | 'back' | 'side'

export interface AnalyzeProductInput {
  views: Partial<Record<LabelView, File>>
}

const API_BASE = '/api/v1/ocr'

export async function analyzeProduct(
  input: AnalyzeProductInput
): Promise<AnalyzeResponse & { job_id: string }> {
  const formData = new FormData()
  const viewNames: string[] = []

  for (const [view, file] of Object.entries(input.views)) {
    formData.append('files', file)
    viewNames.push(view)
  }
  formData.append('view_names', JSON.stringify(viewNames))

  // 1. Create Job
  const response = await fetch(`${API_BASE}/jobs`, {
    method: 'POST',
    credentials: 'include',
    body: formData,
  })

  if (!response.ok) throw new Error('Failed to start analysis')
  const { job_id } = await response.json()

  // 2. Poll for results
  const result = await pollForResult(job_id)

  // Return both result + job_id
  return { ...result, job_id }
}

async function pollForResult(job_id: string): Promise<AnalyzeResponse> {
  const maxAttempts = 40
  for (let i = 0; i < maxAttempts; i++) {
    await new Promise((resolve) => setTimeout(resolve, 2000))

    const statusRes = await fetch(`${API_BASE}/jobs/${job_id}`, {
      credentials: 'include',
    })
    const statusPayload = await statusRes.json()
    const { status } = statusPayload

    if (status === 'completed') {
      const resultRes = await fetch(`${API_BASE}/jobs/${job_id}/result`, {
        credentials: 'include',
      })
      return (await resultRes.json()) as AnalyzeResponse
    }

    if (status === 'failed') {
      throw new Error(statusPayload.error ?? 'Analysis failed')
    }
  }
  throw new Error('Analysis timed out')
}

export interface InspectionRecord {
  id: string
  created_at: string
  officer_id: string
  officer_name?: string
  officer_email?: string
  department?: string
  role?: string
  product_id?: string
  is_compliant: boolean
  confidence_score: number
  summary?: string
  needs_manual_review?: boolean
  extracted_fields?: Record<string, unknown>
  violations?: Array<unknown>
  missing_fields?: string[]
  warnings?: string[]
}

export async function getPastRecords(): Promise<InspectionRecord[]> {
  try {
    const res = await fetch(`${API_BASE}/records`, {
      credentials: 'include',
    })
    if (!res.ok) return []
    return (await res.json()) as InspectionRecord[]
  } catch {
    return []
  }
}
