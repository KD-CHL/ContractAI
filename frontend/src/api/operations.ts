import { get, patch } from './client'
import type {
  OperationsSummary,
  PaginatedResponse,
  WorkItem,
  WorkItemEvent,
  WorkItemListParams,
  WorkItemUpdate,
} from '@/types/api'

export function getOperationsSummary(): Promise<OperationsSummary> {
  return get<OperationsSummary>('/operations/summary')
}

export function listWorkItems(params?: WorkItemListParams): Promise<PaginatedResponse<WorkItem>> {
  return get<PaginatedResponse<WorkItem>>('/work-items', { params })
}

export function getWorkItem(id: string): Promise<WorkItem> {
  return get<WorkItem>(`/work-items/${id}`)
}

export function updateWorkItem(id: string, data: WorkItemUpdate): Promise<WorkItem> {
  return patch<WorkItem>(`/work-items/${id}`, data)
}

export function getWorkItemEvents(id: string): Promise<{ events: WorkItemEvent[] }> {
  return get<{ events: WorkItemEvent[] }>(`/work-items/${id}/events`)
}
