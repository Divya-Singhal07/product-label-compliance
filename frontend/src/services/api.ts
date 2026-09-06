import type { LabelView } from '../types/app'
import type { AnalyzeResponse } from '../types/compliance'

export type { LabelView }

export interface AnalyzeProductInput {
  views: Partial<Record<LabelView, File>>
}

export class ApiError extends Error {
  status: number

  constructor(message: string, status = 0) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

const API_BASE = '/api/v1/ocr'
const ALLOWED_VIEWS: LabelView[] = ['front', 'back', 'side']
const MAX_FILE_BYTES = 15 * 1024 * 1024
/** First Paddle load + OCR + LLM often exceeds 40s. Match the UI copy (up to a few minutes). */
const POLL_TIMEOUT_MS = 10 * 60 * 1000
const POLL_INTERVAL_MS = 2_000

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

async function readBody(res: Response): Promise<unknown> {
  const text = await res.text()
  if (!text) return null
  try {
    return JSON.parse(text)
  } catch {
    return text
  }
}

function detailToMessage(detail: unknown, fallback: string): string {
  if (typeof detail === 'string' && detail.trim()) return detail
  if (Array.isArray(detail)) {
    const parts = detail
      .map((item) => {
        if (typeof item === 'string') return item
        if (item && typeof item === 'object' && 'msg' in item) {
          return String((item as { msg: unknown }).msg)
        }
        return ''
      })
      .filter(Boolean)
    if (parts.length) return parts.join('; ')
  }
  return fallback
}

function messageFromBody(body: unknown, fallback: string): string {
  if (typeof body === 'string' && body.trim()) return body
  if (!body || typeof body !== 'object') return fallback
  const record = body as Record<string, unknown>
  if (typeof record.error === 'string' && record.error.trim()) return record.error
  return detailToMessage(record.detail, fallback)
}

async function readError(res: Response, fallback: string): Promise<ApiError> {
  const body = await readBody(res)
  if (res.status === 401) {
    return new ApiError(messageFromBody(body, 'Not authenticated. Please sign in again.'), 401)
  }
  if (res.status === 403) {
    return new ApiError(messageFromBody(body, 'Not authorized to access this job.'), 403)
  }
  return new ApiError(messageFromBody(body, fallback), res.status)
}

function collectUploads(views: Partial<Record<LabelView, File>>) {
  const uploads: { view: LabelView; file: File }[] = []

  for (const view of ALLOWED_VIEWS) {
    const file = views[view]
    if (!file) continue
    if (!(file instanceof File) || file.size === 0) {
      throw new ApiError(`The ${view} image is empty. Choose another file.`, 400)
    }
    if (file.size > MAX_FILE_BYTES) {
      throw new ApiError(`The ${view} image is larger than 15 MB.`, 400)
    }
    if (file.type && !file.type.startsWith('image/')) {
      throw new ApiError(`The ${view} file must be an image.`, 400)
    }
    uploads.push({ view, file })
  }

  if (uploads.length === 0) {
    throw new ApiError('Upload at least one of front, back, or side.', 400)
  }

  return uploads
}

function jobStatus(payload: unknown): string {
  if (payload && typeof payload === 'object' && 'status' in payload) {
    return String((payload as { status: unknown }).status)
  }
  return ''
}

async function fetchResult(jobId: string): Promise<AnalyzeResponse> {
  const url = `${API_BASE}/jobs/${encodeURIComponent(jobId)}/result`

  for (let attempt = 0; attempt < 8; attempt += 1) {
    const res = await fetch(url, { credentials: 'include' })

    if (res.status === 409) {
      await sleep(500)
      continue
    }
    if (!res.ok) {
      throw await readError(res, 'Failed to load analysis result')
    }

    const payload = await readBody(res)
    if (!payload || typeof payload !== 'object' || !('merged_fields' in payload)) {
      throw new ApiError('Analysis result was malformed.', res.status)
    }
    return payload as AnalyzeResponse
  }

  throw new ApiError('Analysis finished but the result was not ready in time.', 409)
}

async function pollForResult(jobId: string): Promise<AnalyzeResponse> {
  const deadline = Date.now() + POLL_TIMEOUT_MS
  const url = `${API_BASE}/jobs/${encodeURIComponent(jobId)}`
  let lastNetworkError: Error | null = null

  while (Date.now() < deadline) {
    let res: Response
    try {
      res = await fetch(url, { credentials: 'include' })
    } catch (error) {
      lastNetworkError = error instanceof Error ? error : new Error('Network error')
      await sleep(POLL_INTERVAL_MS)
      continue
    }

    if (res.status === 404) throw await readError(res, 'Job not found')
    if (res.status === 401 || res.status === 403) {
      throw await readError(res, 'Not authorized')
    }
    if (res.status >= 500) {
      lastNetworkError = await readError(res, 'Server error while checking job status')
      await sleep(POLL_INTERVAL_MS)
      continue
    }
    if (!res.ok) {
      throw await readError(res, 'Failed to check analysis status')
    }

    const payload = await readBody(res)
    const status = jobStatus(payload)

    if (status === 'completed') return fetchResult(jobId)

    if (status === 'failed') {
      const error =
        payload && typeof payload === 'object' && 'error' in payload
          ? (payload as { error?: unknown }).error
          : null
      throw new ApiError(
        typeof error === 'string' && error.trim() ? error : 'Analysis failed',
        500,
      )
    }

    await sleep(POLL_INTERVAL_MS)
  }

  throw new ApiError(
    lastNetworkError
      ? `Analysis timed out after a network error: ${lastNetworkError.message}`
      : 'Analysis timed out after 10 minutes. The backend may still be running — wait for it to finish before scanning again.',
    408,
  )
}

export async function analyzeProduct(input: AnalyzeProductInput): Promise<AnalyzeResponse & { job_id: string }> {
  const uploads = collectUploads(input.views)
  const formData = new FormData()
  const viewNames: LabelView[] = []

  for (const { view, file } of uploads) {
    formData.append('files', file, file.name || `${view}.png`)
    viewNames.push(view)
  }
  formData.append('view_names', JSON.stringify(viewNames))

  const response = await fetch(`${API_BASE}/jobs`, {
    method: 'POST',
    credentials: 'include',
    body: formData,
  })

  if (!response.ok) {
    throw await readError(response, 'Failed to start analysis')
  }

  const body = await readBody(response)
  const jobId =
    body && typeof body === 'object' && typeof (body as { job_id?: unknown }).job_id === 'string'
      ? (body as { job_id: string }).job_id
      : ''

  if (!jobId) {
    throw new ApiError('Server did not return a job id.', response.status)
  }

  const result = await pollForResult(jobId)
  return { ...result, job_id: jobId }
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
    const res = await fetch(`${API_BASE}/records`, { credentials: 'include' })
    if (!res.ok) return []
    const body = await readBody(res)
    return Array.isArray(body) ? (body as InspectionRecord[]) : []
  } catch {
    return []
  }
}