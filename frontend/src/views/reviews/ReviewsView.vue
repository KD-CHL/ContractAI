<template>
  <div class="page-container">
    <!-- Page Header -->
    <div class="page-header">
      <div class="header-left">
        <h1 class="page-title">审阅记录</h1>
        <n-badge
          v-if="total > 0"
          :value="total"
          :max="999"
          type="info"
          class="count-badge"
        />
      </div>
      <n-button type="primary" @click="router.push('/reviews/new')">
        <template #icon><span>✨</span></template>
        新建审阅
      </n-button>
    </div>

    <!-- Toolbar -->
    <div class="toolbar">
      <div class="toolbar-left">
        <n-input
          v-model:value="searchText"
          placeholder="搜索合同名称或编号..."
          clearable
          class="search-input"
          @update:value="handleSearchDebounced"
          @clear="handleSearchDebounced"
        >
          <template #prefix>
            <n-icon :component="SearchIcon" />
          </template>
        </n-input>
        <n-select
          v-model:value="statusFilter"
          :options="statusOptions"
          placeholder="状态筛选"
          clearable
          class="status-select"
          @update:value="handleFilterChange"
        />
      </div>
      <div class="toolbar-right">
        <span class="switch-label">包含已删除</span>
        <n-switch
          v-model:value="includeDeleted"
          @update:value="handleFilterChange"
        />
      </div>
    </div>

    <!-- Content -->
    <n-card :bordered="false" class="content-card">
      <!-- Loading Skeleton -->
      <div v-if="loading" class="skeleton-wrapper">
        <n-skeleton height="48px" :sharp="false" style="margin-bottom: 12px" />
        <n-skeleton height="48px" :sharp="false" style="margin-bottom: 12px" />
        <n-skeleton height="48px" :sharp="false" style="margin-bottom: 12px" />
        <n-skeleton height="48px" :sharp="false" style="margin-bottom: 12px" />
        <n-skeleton height="48px" :sharp="false" />
      </div>

      <!-- Empty State -->
      <n-empty
        v-else-if="reviews.length === 0"
        description="暂无审阅记录"
        class="empty-state"
      >
        <template #icon>
          <span style="font-size: 48px">📋</span>
        </template>
        <template #extra>
          <n-button type="primary" size="small" @click="router.push('/reviews/new')">
            开始第一次审阅
          </n-button>
        </template>
      </n-empty>

      <!-- Data Table -->
      <template v-else>
        <n-data-table
          :columns="columns"
          :data="reviews"
          :row-key="(row: ReviewSummary) => row.id"
          :row-props="rowProps"
          :row-class-name="rowClassName"
          :bordered="false"
          :single-line="false"
          striped
          class="review-table"
        />

        <!-- Pagination -->
        <div class="pagination-wrapper">
          <n-pagination
            v-model:page="currentPage"
            :page-count="pageCount"
            :page-slot="7"
            show-quick-jumper
            @update:page="handlePageChange"
          />
        </div>
      </template>
    </n-card>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, h } from 'vue'
import { useRouter } from 'vue-router'
import {
  NCard,
  NButton,
  NEmpty,
  NSkeleton,
  NInput,
  NSelect,
  NSwitch,
  NBadge,
  NDataTable,
  NPagination,
  NTag,
  NPopconfirm,
  NIcon,
  NTooltip,
  useMessage,
} from 'naive-ui'
import type { DataTableColumns } from 'naive-ui'
import { get, del, patch } from '@/api/client'
import type { ReviewSummary, PaginatedResponse, RiskLevel } from '@/types/api'

// ─── Icons (inline SVG components) ──────────────────────────────────────────

const SearchIcon = {
  render() {
    return h(
      'svg',
      {
        xmlns: 'http://www.w3.org/2000/svg',
        viewBox: '0 0 24 24',
        width: '1em',
        height: '1em',
        fill: 'none',
        stroke: 'currentColor',
        'stroke-width': '2',
        'stroke-linecap': 'round',
        'stroke-linejoin': 'round',
      },
      [
        h('circle', { cx: '11', cy: '11', r: '8' }),
        h('line', { x1: '21', y1: '21', x2: '16.65', y2: '16.65' }),
      ],
    )
  },
}

// ─── Router & Message ────────────────────────────────────────────────────────

const router = useRouter()
const message = useMessage()

// ─── State ───────────────────────────────────────────────────────────────────

const loading = ref(true)
const reviews = ref<ReviewSummary[]>([])
const total = ref(0)
const currentPage = ref(1)
const pageSize = 20
const searchText = ref('')
const statusFilter = ref<string | null>(null)
const includeDeleted = ref(false)

let searchTimer: ReturnType<typeof setTimeout> | null = null

// ─── Computed ────────────────────────────────────────────────────────────────

const pageCount = computed(() => Math.max(1, Math.ceil(total.value / pageSize)))

const statusOptions = [
  { label: '草稿', value: 'pending' },
  { label: '审阅中', value: 'completed' },
  { label: '已批准', value: 'approved' },
  { label: '已拒绝', value: 'rejected' },
]

// ─── Table Columns ───────────────────────────────────────────────────────────

const columns = computed<DataTableColumns<ReviewSummary>>(() => [
  {
    title: '合同名称',
    key: 'document_name',
    ellipsis: { tooltip: true },
    minWidth: 180,
    render(row) {
      const name = row.file_name || row.contract_id || '未命名合同'
      return h('span', { class: 'contract-name' }, name)
    },
  },
  {
    title: '风险等级',
    key: 'risk_level',
    width: 100,
    align: 'center',
    render(row) {
      if (!row.risk_level) {
        return h(NTag, { size: 'small', type: 'default', bordered: false }, { default: () => '未评定' })
      }
      const config = getRiskConfig(row.risk_level)
      return h(NTag, { size: 'small', type: config.type, bordered: false, round: true }, { default: () => config.label })
    },
  },
  {
    title: '状态',
    key: 'status',
    width: 100,
    align: 'center',
    render(row) {
      const config = getStatusConfig(row.status)
      return h(NTag, { size: 'small', type: config.type, bordered: false }, { default: () => config.label })
    },
  },
  {
    title: '发现数',
    key: 'findings_count',
    width: 90,
    align: 'center',
    render(row) {
      const count = (row.high_risk_count || 0) + (row.medium_risk_count || 0) + (row.low_risk_count || 0)
      if (count === 0) {
        return h('span', { style: 'color: var(--text-secondary, #999)' }, '—')
      }
      return h('span', { class: 'findings-count' }, [
        row.high_risk_count > 0
          ? h('span', { class: 'finding-high' }, `${row.high_risk_count}高 `)
          : null,
        row.medium_risk_count > 0
          ? h('span', { class: 'finding-medium' }, `${row.medium_risk_count}中 `)
          : null,
        row.low_risk_count > 0
          ? h('span', { class: 'finding-low' }, `${row.low_risk_count}低`)
          : null,
      ])
    },
  },
  {
    title: '创建时间',
    key: 'created_at',
    width: 120,
    render(row) {
      return h('span', { class: 'time-text' }, formatRelativeTime(row.created_at))
    },
  },
  {
    title: '操作',
    key: 'actions',
    width: 140,
    align: 'center',
    render(row) {
      const buttons: ReturnType<typeof h>[] = []

      // View button
      buttons.push(
        h(
          NTooltip,
          null,
          {
            trigger: () =>
              h(
                NButton,
                {
                  text: true,
                  type: 'primary',
                  size: 'small',
                  onClick: (e: Event) => {
                    e.stopPropagation()
                    router.push(`/reviews/${row.id}`)
                  },
                },
                { default: () => '查看' },
              ),
            default: () => '查看详情',
          },
        ),
      )

      if (row.is_deleted) {
        // Restore button for deleted items
        buttons.push(
          h(
            NButton,
            {
              text: true,
              type: 'warning',
              size: 'small',
              style: 'margin-left: 12px',
              onClick: (e: Event) => {
                e.stopPropagation()
                handleRestore(row)
              },
            },
            { default: () => '恢复' },
          ),
        )
      } else {
        // Delete button with popconfirm
        buttons.push(
          h(
            NPopconfirm,
            {
              onPositiveClick: () => handleDelete(row),
            },
            {
              trigger: () =>
                h(
                  NButton,
                  {
                    text: true,
                    type: 'error',
                    size: 'small',
                    style: 'margin-left: 12px',
                    onClick: (e: Event) => e.stopPropagation(),
                  },
                  { default: () => '删除' },
                ),
              default: () => '确定要删除该审阅记录吗？删除后可在"包含已删除"中恢复。',
            },
          ),
        )
      }

      return h('div', { class: 'action-buttons' }, buttons)
    },
  },
])

// ─── Row Props (click to navigate) ──────────────────────────────────────────

function rowProps(row: ReviewSummary) {
  return {
    onClick: () => {
      router.push(`/reviews/${row.id}`)
    },
  }
}

// ─── Helpers ─────────────────────────────────────────────────────────────────

function getRiskConfig(level: RiskLevel): { type: 'error' | 'warning' | 'info' | 'success'; label: string } {
  const map: Record<RiskLevel, { type: 'error' | 'warning' | 'info' | 'success'; label: string }> = {
    high: { type: 'error', label: '高风险' },
    medium: { type: 'warning', label: '中风险' },
    low: { type: 'info', label: '低风险' },
  }
  return map[level] || { type: 'info', label: '未知' }
}

function getStatusConfig(status: string): { type: 'default' | 'info' | 'success' | 'error' | 'warning'; label: string } {
  const map: Record<string, { type: 'default' | 'info' | 'success' | 'error' | 'warning'; label: string }> = {
    pending: { type: 'info', label: '草稿' },
    completed: { type: 'success', label: '审阅中' },
    approved: { type: 'success', label: '已批准' },
    rejected: { type: 'error', label: '已拒绝' },
    failed: { type: 'error', label: '失败' },
  }
  return map[status] || { type: 'default', label: status }
}

function formatRelativeTime(dateStr: string): string {
  if (!dateStr) return ''
  const date = new Date(dateStr)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffMin = Math.floor(diffMs / 60000)
  const diffHour = Math.floor(diffMs / 3600000)
  const diffDay = Math.floor(diffMs / 86400000)

  if (diffMin < 1) return '刚刚'
  if (diffMin < 60) return `${diffMin} 分钟前`
  if (diffHour < 24) return `${diffHour} 小时前`
  if (diffDay < 7) return `${diffDay} 天前`
  if (diffDay < 30) return `${Math.floor(diffDay / 7)} 周前`
  return date.toLocaleDateString('zh-CN', { year: 'numeric', month: 'short', day: 'numeric' })
}

function rowClassName(row: ReviewSummary): string {
  return row.is_deleted ? 'row-deleted' : 'row-clickable'
}

// ─── Data Fetching ───────────────────────────────────────────────────────────

async function fetchReviews() {
  loading.value = true
  try {
    const params: Record<string, unknown> = {
      page: currentPage.value,
      page_size: pageSize,
    }
    if (searchText.value.trim()) {
      params.search = searchText.value.trim()
    }
    if (statusFilter.value) {
      params.status = statusFilter.value
    }
    if (includeDeleted.value) {
      params.include_deleted = true
    }

    const data = await get<PaginatedResponse<ReviewSummary>>('/reviews', { params })
    reviews.value = data.items ?? []
    total.value = data.total ?? 0
  } catch {
    message.error('获取审阅记录失败')
    reviews.value = []
    total.value = 0
  } finally {
    loading.value = false
  }
}

// ─── Event Handlers ──────────────────────────────────────────────────────────

function handleSearchDebounced() {
  if (searchTimer) clearTimeout(searchTimer)
  searchTimer = setTimeout(() => {
    currentPage.value = 1
    fetchReviews()
  }, 400)
}

function handleFilterChange() {
  currentPage.value = 1
  fetchReviews()
}

function handlePageChange(page: number) {
  currentPage.value = page
  fetchReviews()
}

async function handleDelete(row: ReviewSummary) {
  try {
    await del(`/reviews/${row.id}`)
    message.success('已删除')
    fetchReviews()
  } catch {
    message.error('删除失败，请重试')
  }
}

async function handleRestore(row: ReviewSummary) {
  try {
    await patch(`/reviews/${row.id}/restore`)
    message.success('已恢复')
    fetchReviews()
  } catch {
    message.error('恢复失败，请重试')
  }
}

// ─── Lifecycle ───────────────────────────────────────────────────────────────

onMounted(() => {
  fetchReviews()
})
</script>

<style scoped>
.page-container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 4px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 10px;
}

.page-title {
  font-size: 22px;
  font-weight: 700;
  margin: 0;
  color: var(--text-primary, #1a1a2e);
}

.count-badge {
  transform: translateY(-2px);
}

/* Toolbar */
.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  gap: 12px;
  flex-wrap: wrap;
}

.toolbar-left {
  display: flex;
  align-items: center;
  gap: 12px;
  flex: 1;
  min-width: 280px;
}

.search-input {
  max-width: 320px;
  flex: 1;
}

.status-select {
  width: 140px;
}

.toolbar-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.switch-label {
  font-size: 13px;
  color: var(--text-secondary, #6b7280);
  white-space: nowrap;
}

/* Content Card */
.content-card {
  border-radius: var(--radius-md, 10px);
  box-shadow: var(--card-shadow, 0 2px 12px rgba(0, 0, 0, 0.06));
}

.skeleton-wrapper {
  padding: 12px 0;
}

.empty-state {
  padding: 60px 0;
}

/* Table */
.review-table {
  --n-td-padding: 14px 16px;
}

:deep(.row-clickable) {
  cursor: pointer;
  transition: background-color 0.2s ease;
}

:deep(.row-clickable:hover td) {
  background-color: var(--n-td-color-hover, rgba(0, 0, 0, 0.02)) !important;
}

:deep(.row-deleted) {
  opacity: 0.55;
}

:deep(.row-deleted td) {
  text-decoration: line-through;
  text-decoration-color: var(--text-secondary, #999);
}

.contract-name {
  font-weight: 500;
  color: var(--text-primary, #1a1a2e);
}

.findings-count {
  font-size: 12px;
  font-weight: 500;
}

.finding-high {
  color: #d03050;
}

.finding-medium {
  color: #f0a020;
}

.finding-low {
  color: #2080f0;
}

.time-text {
  font-size: 13px;
  color: var(--text-secondary, #6b7280);
}

.action-buttons {
  display: flex;
  align-items: center;
  justify-content: center;
}

/* Pagination */
.pagination-wrapper {
  display: flex;
  justify-content: center;
  margin-top: 20px;
  padding-top: 16px;
  border-top: 1px solid var(--border-color, #efeff5);
}

/* Responsive */
@media (max-width: 768px) {
  .toolbar {
    flex-direction: column;
    align-items: stretch;
  }

  .toolbar-left {
    flex-direction: column;
    align-items: stretch;
  }

  .search-input {
    max-width: 100%;
  }

  .status-select {
    width: 100%;
  }

  .toolbar-right {
    justify-content: flex-end;
  }
}
</style>
