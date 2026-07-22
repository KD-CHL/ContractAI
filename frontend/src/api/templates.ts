import { del, get, patch, post } from './client'
import type { PaginatedResponse } from '@/types/api'

// ─── Types ───────────────────────────────────────────────────────────────────

export interface ContractTemplate {
  id: string
  org_id: string
  name: string
  description: string
  category: string
  content_text: string
  created_by_user_id: string | null
  created_at: string
  updated_at: string
}

export interface TemplateCreate {
  name: string
  description?: string
  category?: string
  content_text?: string
}

export interface TemplateUpdate {
  name?: string
  description?: string
  category?: string
  content_text?: string
}

export interface TemplateListParams {
  category?: string
  search?: string
  page?: number
  page_size?: number
}

export interface Clause {
  id: string
  org_id: string
  title: string
  content_text: string
  category: string
  risk_level: string | null
  risk_annotation: string
  created_by_user_id: string | null
  created_at: string
  updated_at: string
}

export interface ClauseCreate {
  title: string
  content_text: string
  category?: string
  risk_level?: string | null
  risk_annotation?: string
}

export interface ClauseUpdate {
  title?: string
  content_text?: string
  category?: string
  risk_level?: string | null
  risk_annotation?: string
}

export interface ClauseListParams {
  category?: string
  risk_level?: string
  search?: string
  page?: number
  page_size?: number
}

// ─── Template API ────────────────────────────────────────────────────────────

export function listTemplates(
  params?: TemplateListParams,
): Promise<PaginatedResponse<ContractTemplate>> {
  return get<PaginatedResponse<ContractTemplate>>('/templates', { params })
}

export function getTemplate(id: string): Promise<ContractTemplate> {
  return get<ContractTemplate>(`/templates/${id}`)
}

export function createTemplate(data: TemplateCreate): Promise<ContractTemplate> {
  return post<ContractTemplate>('/templates', data)
}

export function updateTemplate(id: string, data: TemplateUpdate): Promise<ContractTemplate> {
  return patch<ContractTemplate>(`/templates/${id}`, data)
}

export function deleteTemplate(id: string): Promise<void> {
  return del<void>(`/templates/${id}`)
}

// ─── Clause API ──────────────────────────────────────────────────────────────

export function listClauses(params?: ClauseListParams): Promise<PaginatedResponse<Clause>> {
  return get<PaginatedResponse<Clause>>('/clauses', { params })
}

export function getClause(id: string): Promise<Clause> {
  return get<Clause>(`/clauses/${id}`)
}

export function createClause(data: ClauseCreate): Promise<Clause> {
  return post<Clause>('/clauses', data)
}

export function updateClause(id: string, data: ClauseUpdate): Promise<Clause> {
  return patch<Clause>(`/clauses/${id}`, data)
}

export function deleteClause(id: string): Promise<void> {
  return del<void>(`/clauses/${id}`)
}
