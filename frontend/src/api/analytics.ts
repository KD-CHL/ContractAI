import { get } from './client'

// ─── Analytics response types ────────────────────────────────────────────────

export interface RiskTrendPoint {
  date: string
  high: number
  medium: number
  low: number
}

export interface RiskTrendsResponse {
  trends: RiskTrendPoint[]
  period: string
}

export interface EfficiencyMetrics {
  avg_review_time_minutes: number
  reviews_per_day: number
  completion_rate: number
  period: string
}

export interface WorkloadEntry {
  user_id: string
  display_name: string
  open_count: number
  completed_count: number
  overdue_count: number
}

export interface WorkloadResponse {
  workload: WorkloadEntry[]
}

export interface RiskCategoryEntry {
  category: string
  count: number
  percentage: number
}

export interface RiskCategoriesResponse {
  categories: RiskCategoryEntry[]
}

export interface AnalyticsOverview {
  total_reviews: number
  total_risks_found: number
  avg_risk_score: number
  top_risk_category: string
  review_trend_pct: number
  risk_trend_pct: number
}

// ─── API functions ───────────────────────────────────────────────────────────

export function getRiskTrends(period: string = '30d'): Promise<RiskTrendsResponse> {
  return get<RiskTrendsResponse>('/analytics/risk-trends', { params: { period } })
}

export function getEfficiency(period: string = '30d'): Promise<EfficiencyMetrics> {
  return get<EfficiencyMetrics>('/analytics/efficiency', { params: { period } })
}

export function getWorkload(): Promise<WorkloadResponse> {
  return get<WorkloadResponse>('/analytics/workload')
}

export function getRiskCategories(period: string = '30d'): Promise<RiskCategoriesResponse> {
  return get<RiskCategoriesResponse>('/analytics/risk-categories', { params: { period } })
}

export function getOverview(): Promise<AnalyticsOverview> {
  return get<AnalyticsOverview>('/analytics/overview')
}
