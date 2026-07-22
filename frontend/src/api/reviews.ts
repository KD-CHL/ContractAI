import client, { del, get, patch, post } from './client'
import type {
  PaginatedResponse,
  ReviewDecisionRequest,
  ReviewDetail,
  ReviewListParams,
  ReviewSummary,
  ReviewTextRequest,
} from '@/types/api'

export function listReviews(params?: ReviewListParams): Promise<PaginatedResponse<ReviewSummary>> {
  return get<PaginatedResponse<ReviewSummary>>('/reviews', { params })
}

export function getReview(id: string): Promise<ReviewDetail> {
  return get<ReviewDetail>(`/reviews/${id}`)
}

export function createReviewFromText(data: ReviewTextRequest): Promise<ReviewDetail> {
  return post<ReviewDetail>('/reviews/text', data)
}

export function createReviewFromFile(file: File, contractId?: string): Promise<ReviewDetail> {
  const formData = new FormData()
  formData.append('file', file)
  if (contractId) {
    formData.append('contract_id', contractId)
  }
  return client
    .post<ReviewDetail>('/reviews', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    .then((res) => res.data)
}

export function deleteReview(id: string): Promise<void> {
  return del<void>(`/reviews/${id}`)
}

export function restoreReview(id: string): Promise<ReviewDetail> {
  return post<ReviewDetail>(`/reviews/${id}/restore`)
}

export function exportReview(id: string, format: 'html' = 'html'): Promise<Blob> {
  return client
    .get(`/reviews/${id}/export`, {
      params: { format },
      responseType: 'blob',
    })
    .then((res) => res.data)
}

export function submitDecision(id: string, data: ReviewDecisionRequest): Promise<ReviewDetail> {
  return patch<ReviewDetail>(`/reviews/${id}/decision`, data)
}
