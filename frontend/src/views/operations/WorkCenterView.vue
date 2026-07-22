<template>
  <div class="page-container">
    <!-- Page Header -->
    <div class="page-header">
      <h1 class="page-title">处置中心</h1>
      <div class="summary-badges">
        <n-badge :value="summary.open" :max="999" type="warning">
          <n-tag size="small" :bordered="false">待处理</n-tag>
        </n-badge>
        <n-badge :value="summary.in_progress" :max="999" type="info">
          <n-tag size="small" :bordered="false">进行中</n-tag>
        </n-badge>
        <n-badge :value="summary.overdue" :max="999" type="error">
          <n-tag size="small" :bordered="false">逾期</n-tag>
        </n-badge>
      </div>
    </div>

    <!-- Filter Bar -->
    <n-card :bordered="false" class="filter-card" size="small">
      <n-space align="center" :wrap="true">
        <n-select
          v-model:value="filters.kind"
          :options="kindOptions"
          placeholder="类型"
          clearable
          style="width: 140px"
          @update:value="handleFilterChange"
        />
        <n-select
          v-model:value="filters.status"
          :options="statusOptions"
          placeholder="状态"
          clearable
          style="width: 140px"
          @update:value="handleFilterChange"
        />
        <n-select
          v-model:value="filters.assignee"
          :options="assigneeFilterOptions"
          placeholder="负责人"
          clearable
          style="width: 140px"
          @update:value="handleFilterChange"
        />
        <n-space align="center" :size="4">
          <span class="switch-label">仅逾期</span>
          <n-switch v-model:value="filters.overdue" @update:value="handleFilterChange" />
        </n-space>
      </n-space>
    </n-card>

    <!-- Data Table -->
    <n-card :bordered="false" class="content-card">
      <n-data-table
        :columns="columns"
        :data="items"
        :loading="loading"
        :pagination="pagination"
        :row-props="rowProps"
        :row-key="(row: WorkItem) => row.id"
        remote
        striped
        @update:page="handlePageChange"
      />
      <template #header-extra>
        <n-button quaternary size="small" @click="refreshData">
          刷新
        </n-button>
      </template>
    </n-card>

    <!-- Detail Drawer -->
    <n-drawer v-model:show="drawerVisible" :width="480" placement="right">
      <n-drawer-content :title="selectedItem?.title || '工单详情'" closable>
        <template v-if="selectedItem">
          <!-- Description -->
          <n-space vertical :size="16">
            <div>
              <n-text depth="3" style="font-size: 12px">描述</n-text>
              <n-p style="margin: 4px 0 0">
                {{ selectedItem.description || '暂无描述' }}
              </n-p>
            </div>

            <n-divider style="margin: 8px 0" />

            <!-- Meta info -->
            <n-descriptions :column="2" label-placement="left" size="small" bordered>
              <n-descriptions-item label="类型">
                <n-tag :type="selectedItem.kind === 'finding' ? 'error' : 'info'" size="small">
                  {{ kindLabel(selectedItem.kind) }}
                </n-tag>
              </n-descriptions-item>
              <n-descriptions-item label="风险等级">
                <n-tag :type="riskTagType(selectedItem.risk_level)" size="small">
                  {{ riskLabel(selectedItem.risk_level) }}
                </n-tag>
              </n-descriptions-item>
              <n-descriptions-item label="当前状态">
                <n-tag :type="statusTagType(selectedItem.status)" size="small">
                  {{ statusLabel(selectedItem.status) }}
                </n-tag>
              </n-descriptions-item>
              <n-descriptions-item label="负责人">
                {{ selectedItem.assignee_name || '未分配' }}
              </n-descriptions-item>
              <n-descriptions-item label="截止日期" :span="2">
                <n-text :type="isOverdue(selectedItem) ? 'error' : undefined">
                  {{ selectedItem.due_at ? formatDate(selectedItem.due_at) : '未设置' }}
                  <template v-if="isOverdue(selectedItem)"> (已逾期)</template>
                </n-text>
              </n-descriptions-item>
            </n-descriptions>

            <n-divider style="margin: 8px 0" />

            <!-- Status Transitions -->
            <div v-if="allowedTransitions.length > 0">
              <n-text depth="3" style="font-size: 12px; display: block; margin-bottom: 8px">
                状态流转
              </n-text>
              <n-space :size="8" :wrap="true">
                <n-button
                  v-for="t in allowedTransitions"
                  :key="t"
                  size="small"
                  :type="transitionButtonType(t)"
                  secondary
                  @click="pendingStatus = t"
                >
                  {{ statusLabel(t) }}
                </n-button>
              </n-space>
              <n-alert
                v-if="pendingStatus"
                type="info"
                style="margin-top: 8px"
                closable
                @close="pendingStatus = null"
              >
                将状态变更为「{{ statusLabel(pendingStatus) }}」
              </n-alert>
            </div>

            <!-- Assignee -->
            <div>
              <n-text depth="3" style="font-size: 12px; display: block; margin-bottom: 8px">
                负责人
              </n-text>
              <n-select
                v-model:value="editAssignee"
                :options="memberOptions"
                placeholder="选择负责人"
                clearable
                filterable
              />
            </div>

            <!-- Due Date -->
            <div>
              <n-text depth="3" style="font-size: 12px; display: block; margin-bottom: 8px">
                截止日期
              </n-text>
              <n-date-picker
                v-model:value="editDueAt"
                type="date"
                clearable
                style="width: 100%"
              />
            </div>

            <!-- Note -->
            <div>
              <n-text depth="3" style="font-size: 12px; display: block; margin-bottom: 8px">
                备注
                <n-text v-if="noteRequired" type="error" style="font-size: 12px">
                  * 必填
                </n-text>
              </n-text>
              <n-input
                v-model:value="editNote"
                type="textarea"
                placeholder="输入处理备注..."
                :rows="3"
                :status="noteRequired && !editNote.trim() ? 'error' : undefined"
              />
            </div>

            <!-- Conflict Alert -->
            <n-alert v-if="conflictError" type="error" closable @close="conflictError = false">
              数据冲突：该工单已被其他人修改，请关闭后重新打开查看最新状态。
            </n-alert>

            <!-- Save Button -->
            <n-button
              type="primary"
              block
              :loading="saving"
              :disabled="!hasChanges"
              @click="handleSave"
            >
              保存修改
            </n-button>

            <n-divider style="margin: 8px 0" />

            <!-- Event Timeline -->
            <div>
              <n-text depth="3" style="font-size: 12px; display: block; margin-bottom: 12px">
                事件时间线
              </n-text>
              <n-spin :show="eventsLoading">
                <n-empty v-if="events.length === 0 && !eventsLoading" description="暂无事件记录" size="small" />
                <n-timeline v-else>
                  <n-timeline-item
                    v-for="ev in events"
                    :key="ev.id"
                    :type="eventTimelineType(ev.event_type)"
                    :title="ev.event_type"
                    :content="ev.detail || ''"
                    :time="formatDateTime(ev.created_at)"
                  >
                    <template #header>
                      <n-space :size="4" align="center">
                        <span>{{ ev.event_type }}</span>
                        <n-text v-if="ev.actor_name" depth="3" style="font-size: 12px">
                          ({{ ev.actor_name }})
                        </n-text>
                      </n-space>
                    </template>
                  </n-timeline-item>
                </n-timeline>
              </n-spin>
            </div>
          </n-space>
        </template>
        <template v-else>
          <n-empty description="请选择一个工单查看详情" />
        </template>
      </n-drawer-content>
    </n-drawer>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, h } from 'vue'
import {
  NBadge,
  NTag,
  NCard,
  NSpace,
  NSelect,
  NSwitch,
  NDataTable,
  NDrawer,
  NDrawerContent,
  NText,
  NP,
  NDivider,
  NDescriptions,
  NDescriptionsItem,
  NButton,
  NAlert,
  NInput,
  NDatePicker,
  NTimeline,
  NTimelineItem,
  NSpin,
  NEmpty,
  useMessage,
  type DataTableColumns,
} from 'naive-ui'
import { get, patch } from '@/api/client'
import { useAuthStore } from '@/stores/auth'
import type {
  WorkItem,
  WorkItemKind,
  WorkItemStatus,
  WorkItemEvent,
  OperationsSummary,
  PaginatedResponse,
  User,
  RiskLevel,
} from '@/types/api'

const message = useMessage()
const authStore = useAuthStore()

// ─── Summary ─────────────────────────────────────────────────────────────────

const summary = reactive<OperationsSummary>({
  total: 0,
  open: 0,
  in_progress: 0,
  overdue: 0,
  pending_approval: 0,
  completed_this_week: 0,
})

// ─── Filters ─────────────────────────────────────────────────────────────────

const filters = reactive<{
  kind: WorkItemKind | null
  status: WorkItemStatus | null
  assignee: string | null
  overdue: boolean
}>({
  kind: null,
  status: null,
  assignee: null,
  overdue: false,
})

const kindOptions = [
  { label: '风险发现', value: 'finding' },
  { label: '义务条款', value: 'obligation' },
]

const statusOptions = [
  { label: '待处理', value: 'pending' },
  { label: '进行中', value: 'in_progress' },
  { label: '已解决', value: 'resolved' },
  { label: '已接受', value: 'accepted' },
  { label: '已完成', value: 'completed' },
  { label: '已豁免', value: 'waived' },
]

const assigneeFilterOptions = [
  { label: '我的', value: 'me' },
  { label: '未分配', value: 'unassigned' },
]

// ─── Table ───────────────────────────────────────────────────────────────────

const loading = ref(false)
const items = ref<WorkItem[]>([])
const pagination = reactive({
  page: 1,
  pageSize: 15,
  itemCount: 0,
  showSizePicker: false,
})

const columns: DataTableColumns<WorkItem> = [
  {
    title: '标题',
    key: 'title',
    ellipsis: { tooltip: true },
    width: 220,
  },
  {
    title: '类型',
    key: 'kind',
    width: 100,
    render(row) {
      return h(
        NTag,
        { size: 'small', type: row.kind === 'finding' ? 'error' : 'info', bordered: false },
        { default: () => kindLabel(row.kind) },
      )
    },
  },
  {
    title: '风险等级',
    key: 'risk_level',
    width: 90,
    render(row) {
      return h(
        NTag,
        { size: 'small', type: riskTagType(row.risk_level), bordered: false },
        { default: () => riskLabel(row.risk_level) },
      )
    },
  },
  {
    title: '状态',
    key: 'status',
    width: 90,
    render(row) {
      return h(
        NTag,
        { size: 'small', type: statusTagType(row.status) },
        { default: () => statusLabel(row.status) },
      )
    },
  },
  {
    title: '负责人',
    key: 'assignee_name',
    width: 100,
    render(row) {
      return row.assignee_name || '未分配'
    },
  },
  {
    title: '截止日期',
    key: 'due_at',
    width: 120,
    render(row) {
      if (!row.due_at) return '-'
      const overdue = isOverdue(row)
      return h(
        NText,
        { type: overdue ? 'error' : undefined, style: overdue ? 'font-weight: 600' : '' },
        { default: () => formatDate(row.due_at!) + (overdue ? ' (逾期)' : '') },
      )
    },
  },
  {
    title: '操作',
    key: 'actions',
    width: 80,
    render(row) {
      return h(
        NButton,
        { size: 'tiny', quaternary: true, type: 'primary', onClick: (e: Event) => { e.stopPropagation(); openDrawer(row) } },
        { default: () => '详情' },
      )
    },
  },
]

function rowProps(row: WorkItem) {
  return {
    style: 'cursor: pointer',
    onClick: () => openDrawer(row),
  }
}

// ─── Drawer ──────────────────────────────────────────────────────────────────

const drawerVisible = ref(false)
const selectedItem = ref<WorkItem | null>(null)
const events = ref<WorkItemEvent[]>([])
const eventsLoading = ref(false)
const saving = ref(false)
const conflictError = ref(false)

// Edit state
const pendingStatus = ref<WorkItemStatus | null>(null)
const editAssignee = ref<string | null>(null)
const editDueAt = ref<number | null>(null)
const editNote = ref('')

// Members for assignee select
const members = ref<User[]>([])
const memberOptions = computed(() =>
  members.value.map((m) => ({ label: m.display_name, value: m.id })),
)

// Status transition map
const transitionMap: Record<WorkItemStatus, WorkItemStatus[]> = {
  pending: ['in_progress', 'resolved', 'accepted', 'waived'],
  in_progress: ['resolved', 'accepted', 'waived', 'completed'],
  resolved: ['completed'],
  accepted: ['completed'],
  completed: [],
  waived: [],
}

const allowedTransitions = computed<WorkItemStatus[]>(() => {
  if (!selectedItem.value) return []
  return transitionMap[selectedItem.value.status] || []
})

const noteRequired = computed(() => {
  return pendingStatus.value === 'resolved' || pendingStatus.value === 'accepted' || pendingStatus.value === 'waived'
})

const hasChanges = computed(() => {
  if (pendingStatus.value) return true
  if (editAssignee.value !== (selectedItem.value?.assignee_user_id || null)) return true
  if (editDueAt.value !== null) return true
  return false
})

// ─── Data Fetching ───────────────────────────────────────────────────────────

async function fetchSummary() {
  try {
    const data = await get<OperationsSummary>('/operations/summary')
    Object.assign(summary, data)
  } catch {
    // Silent fail for summary badges
  }
}

async function fetchItems() {
  loading.value = true
  try {
    const params: Record<string, unknown> = {
      page: pagination.page,
      page_size: pagination.pageSize,
    }
    if (filters.kind) params.kind = filters.kind
    if (filters.status) params.status = filters.status
    if (filters.assignee) params.assignee = filters.assignee
    if (filters.overdue) params.overdue = true

    const data = await get<PaginatedResponse<WorkItem>>('/work-items', { params })
    items.value = data.items
    pagination.itemCount = data.total
  } catch {
    message.error('获取工单列表失败')
  } finally {
    loading.value = false
  }
}

async function fetchMembers() {
  try {
    const data = await get<PaginatedResponse<User>>('/users', { params: { page_size: 200 } })
    members.value = data.items
  } catch {
    // Fallback: empty members list
  }
}

async function fetchEvents(id: string) {
  eventsLoading.value = true
  try {
    const data = await get<{ events: WorkItemEvent[] }>(`/work-items/${id}/events`)
    events.value = data.events || []
  } catch {
    events.value = []
  } finally {
    eventsLoading.value = false
  }
}

function refreshData() {
  fetchSummary()
  fetchItems()
}

// ─── Event Handlers ──────────────────────────────────────────────────────────

function handleFilterChange() {
  pagination.page = 1
  fetchItems()
}

function handlePageChange(page: number) {
  pagination.page = page
  fetchItems()
}

function openDrawer(item: WorkItem) {
  selectedItem.value = item
  pendingStatus.value = null
  editAssignee.value = item.assignee_user_id || null
  editDueAt.value = item.due_at ? new Date(item.due_at).getTime() : null
  editNote.value = ''
  conflictError.value = false
  drawerVisible.value = true
  fetchEvents(item.id)
}

async function handleSave() {
  if (!selectedItem.value) return

  // Validate note requirement
  if (noteRequired.value && !editNote.value.trim()) {
    message.warning('该状态变更需要填写备注说明')
    return
  }

  saving.value = true
  conflictError.value = false

  try {
    const payload: Record<string, unknown> = {
      expected_version: selectedItem.value.version,
    }

    if (pendingStatus.value) {
      payload.status = pendingStatus.value
    }
    if (editAssignee.value !== (selectedItem.value.assignee_user_id || null)) {
      payload.assignee_user_id = editAssignee.value || undefined
    }
    if (editDueAt.value !== null) {
      payload.due_at = new Date(editDueAt.value).toISOString()
    }
    if (editNote.value.trim()) {
      payload.note = editNote.value.trim()
    }

    const updated = await patch<WorkItem>(`/work-items/${selectedItem.value.id}`, payload)
    selectedItem.value = updated

    // Update in list
    const idx = items.value.findIndex((i) => i.id === updated.id)
    if (idx !== -1) items.value[idx] = updated

    // Reset edit state
    pendingStatus.value = null
    editNote.value = ''
    editDueAt.value = updated.due_at ? new Date(updated.due_at).getTime() : null
    editAssignee.value = updated.assignee_user_id || null

    message.success('保存成功')
    fetchEvents(updated.id)
    fetchSummary()
  } catch (err: unknown) {
    const apiErr = err as { status_code?: number; detail?: string }
    if (apiErr.status_code === 409) {
      conflictError.value = true
      message.error('数据冲突，请刷新后重试')
    } else {
      message.error(apiErr.detail || '保存失败，请重试')
    }
  } finally {
    saving.value = false
  }
}

// ─── Helpers ─────────────────────────────────────────────────────────────────

function kindLabel(kind: WorkItemKind): string {
  const map: Record<WorkItemKind, string> = { finding: '风险发现', obligation: '义务条款' }
  return map[kind] || kind
}

function statusLabel(status: WorkItemStatus): string {
  const map: Record<WorkItemStatus, string> = {
    pending: '待处理',
    in_progress: '进行中',
    resolved: '已解决',
    accepted: '已接受',
    completed: '已完成',
    waived: '已豁免',
  }
  return map[status] || status
}

function statusTagType(status: WorkItemStatus): 'default' | 'info' | 'success' | 'warning' | 'error' {
  const map: Record<WorkItemStatus, 'default' | 'info' | 'success' | 'warning' | 'error'> = {
    pending: 'warning',
    in_progress: 'info',
    resolved: 'success',
    accepted: 'success',
    completed: 'default',
    waived: 'default',
  }
  return map[status] || 'default'
}

function riskLabel(level?: RiskLevel): string {
  if (!level) return '-'
  const map: Record<RiskLevel, string> = { high: '高', medium: '中', low: '低' }
  return map[level] || level
}

function riskTagType(level?: RiskLevel): 'default' | 'info' | 'success' | 'warning' | 'error' {
  if (!level) return 'default'
  const map: Record<RiskLevel, 'default' | 'info' | 'success' | 'warning' | 'error'> = {
    high: 'error',
    medium: 'warning',
    low: 'success',
  }
  return map[level] || 'default'
}

function transitionButtonType(status: WorkItemStatus): 'default' | 'info' | 'success' | 'warning' | 'error' {
  const map: Record<string, 'default' | 'info' | 'success' | 'warning' | 'error'> = {
    in_progress: 'info',
    resolved: 'success',
    accepted: 'success',
    completed: 'default',
    waived: 'warning',
  }
  return map[status] || 'default'
}

function isOverdue(item: WorkItem): boolean {
  if (item.is_overdue) return true
  if (!item.due_at) return false
  const terminalStatuses: WorkItemStatus[] = ['completed', 'waived', 'resolved', 'accepted']
  if (terminalStatuses.includes(item.status)) return false
  return new Date(item.due_at) < new Date()
}

function formatDate(dateStr: string): string {
  const d = new Date(dateStr)
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

function formatDateTime(dateStr: string): string {
  const d = new Date(dateStr)
  return `${formatDate(dateStr)} ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
}

function eventTimelineType(eventType: string): 'default' | 'info' | 'success' | 'warning' | 'error' {
  if (eventType.includes('创建') || eventType.includes('created')) return 'info'
  if (eventType.includes('完成') || eventType.includes('completed') || eventType.includes('resolved')) return 'success'
  if (eventType.includes('逾期') || eventType.includes('overdue')) return 'error'
  if (eventType.includes('分配') || eventType.includes('assigned')) return 'warning'
  return 'default'
}

// ─── Init ────────────────────────────────────────────────────────────────────

onMounted(() => {
  fetchSummary()
  fetchItems()
  fetchMembers()
})
</script>

<style scoped>
.page-container {
  max-width: 1200px;
  margin: 0 auto;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.page-title {
  font-size: 22px;
  font-weight: 700;
  margin: 0;
  color: var(--text-primary);
}

.summary-badges {
  display: flex;
  gap: 20px;
  align-items: center;
}

.filter-card {
  margin-bottom: 12px;
  border-radius: var(--radius-md, 10px);
}

.content-card {
  border-radius: var(--radius-md, 10px);
  box-shadow: var(--card-shadow);
}

.switch-label {
  font-size: 13px;
  color: var(--text-secondary, #666);
}
</style>
