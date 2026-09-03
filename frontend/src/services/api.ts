import type { AnalyzeResponse } from '../types/compliance'

export type LabelView = 'front' | 'back' | 'side'

export interface AnalyzeProductInput {
  views: Partial<Record<LabelView, File>>
}

/**
 * Future HTTP API surface.
 *
 * No base URL, no endpoint paths, and no network requests.
 * The backend team will add HTTP separately.
 */
export interface LabelLensApi {
  analyzeProduct(input: AnalyzeProductInput): Promise<AnalyzeResponse>
}

export class ApiNotAvailableError extends Error {
  constructor(message = 'The backend HTTP API is not available yet.') {
    super(message)
    this.name = 'ApiNotAvailableError'
  }
}

export function createLabelLensApi(): LabelLensApi {
  return {
    analyzeProduct() {
      return Promise.reject(new ApiNotAvailableError())
    },
  }
}
