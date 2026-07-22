// ─── Auth ────────────────────────────────────────────────────────────────────

export interface User {
  id: string
  email: string
  display_name: string
  role: 'owner' | 'admin' | 'member'
  org_id: string
  org_name: string
  status?: 'active' | 'disabled'
  created_at?: string
}

export interface AuthStatus {
  bootstrap_required: boolean
  authenticated: boolean
  user?: User
}

export interface LoginRequest {
  email: string
  password: string
}

export interface RegisterRequest {
  org_name: string
  display_name: string
  email: string
  password: string
}

export interface AuthResponse {
  access_token: string
  refresh_token: string
  user: User
}

export interface RefreshRequest {
  refresh_token: string
}

export interface ChangePasswordRequest {
  current_password: string
  new_password: string
}

// ─── Reviews ─────────────────────────────────────────────────────────────────

export type RiskLevel = 'high' | 'medium' | 'low'
export type ReviewStatus = 'pending' | 'completed' | 'failed' | 'approved' | 'rejected'

export interface Evidence {
  text: string
  location?: string
  page?: number
  clause_ref?: string
}

export interface RiskFinding {
  id: string
  title: string
  description: string
  risk_level: RiskLevel
  category: string
  evidence: Evidence[]
  recommendation?: string
  clause_ref?: string
}

export interface Obligation {
  id: string
  party: string
  description: string
  deadline?: string
  conditions?: string[]
  penalty?: string
}

export interface QualityMetrics {
  completeness_score: number
  clarity_score: number
  consistency_score: number
  overall_score: number
  issues: string[]
}

export interface ReviewReport {
  summary: string
  risk_findings: RiskFinding[]
  obligations: Obligation[]
  quality_metrics: QualityMetrics
  key_terms?: Record<string, string>
  recommendations?: string[]
  generated_at?: string
}

export interface ReviewSummary {
  id: string
  contract_id?: string
  file_name?: string
  status: ReviewStatus
  risk_level?: RiskLevel
  high_risk_count: number
  medium_risk_count: number
  low_risk_count: number
  created_at: string
  updated_at: string
  created_by?: string
  is_deleted?: boolean
}

export interface ReviewDetail extends ReviewSummary {
  report?: ReviewReport
  decision?: ReviewDecision
  version: number
}

export interface ReviewDecision {
  action: 'approve' | 'reject' | 'request_changes'
  note?: string
  decided_by: string
  decided_at: string
}

export interface ReviewTextRequest {
  text: string
  contract_id?: string
}

export interface ReviewListParams {
  page?: number
  page_size?: number
  search?: string
  status?: string
  include_deleted?: boolean
}

export interface ReviewDecisionRequest {
  action: 'approve' | 'reject' | 'request_changes'
  note?: string
  expected_version: number
}

// ─── Work Items / Operations ─────────────────────────────────────────────────

export type WorkItemKind = 'finding' | 'obligation'
export type WorkItemStatus = 'pending' | 'in_progress' | 'resolved' | 'accepted' | 'completed' | 'waived'

export interface WorkItem {
  id: string
  kind: WorkItemKind
  title: string
  description?: string
  risk_level?: RiskLevel
  status: WorkItemStatus
  assignee_user_id?: string
  assignee_name?: string
  review_id?: string
  due_at?: string
  created_at: string
  updated_at: string
  version: number
  is_overdue?: boolean
}

export interface WorkItemEvent {
  id: string
  work_item_id: string
  event_type: string
  actor_id?: string
  actor_name?: string
  detail?: string
  created_at: string
}

export interface WorkItemUpdate {
  status?: WorkItemStatus
  assignee_user_id?: string
  due_at?: string
  note?: string
  expected_version: number
}

export interface WorkItemListParams {
  page?: number
  page_size?: number
  kind?: WorkItemKind
  status?: WorkItemStatus
  assignee?: string
  overdue?: boolean
}

// ─── Dashboard & Operations Summary ─────────────────────────────────────────

export interface DashboardSummary {
  review_count: number
  high_risk_count: number
  open_work_items: number
  overdue_count: number
  recent_reviews: ReviewSummary[]
}

export interface OperationsSummary {
  total: number
  open: number
  in_progress: number
  overdue: number
  pending_approval: number
  completed_this_week: number
}

// ─── Users / Members ─────────────────────────────────────────────────────────

export interface MemberCreate {
  display_name: string
  email: string
  password: string
  role: 'admin' | 'member'
}

export interface MemberUpdate {
  role?: 'admin' | 'member'
  status?: 'active' | 'disabled'
  display_name?: string
}

// ─── Audit ───────────────────────────────────────────────────────────────────

export interface AuditLog {
  id: string
  actor_id?: string
  actor_name?: string
  action: string
  resource_type: string
  resource_id?: string
  result?: 'success' | 'failure'
  detail?: string
  ip_address?: string
  created_at: string
}

// ─── Generic ─────────────────────────────────────────────────────────────────

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  page_size: number
}

export interface ApiError {
  detail: string
  status_code?: number
}
