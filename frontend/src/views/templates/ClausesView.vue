<template>
  <div class="page-container">
    <!-- Page Header -->
    <div class="page-header">
      <div class="header-left">
        <h1 class="page-title">条款库</h1>
        <n-badge v-if="total > 0" :value="total" :max="999" type="info" class="count-badge" />
      </div>
      <n-button type="primary" @click="openCreate">
        <template #icon><span>＋</span></template>
        新建条款
      </n-button>
    </div>

    <!-- Filter Bar -->
    <div class="toolbar">
      <div class="toolbar-left">
        <n-input
          v-model:value="searchText"
          placeholder="搜索条款标题或内容..."
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
          v-model:value="categoryFilter"
          :options="categoryOptions"
          placeholder="分类筛选"
          clearable
          class="filter-select"
          @update:value="handleFilterChange"
        />
        <n-select
          v-model:value="riskFilter"
          :options="riskOptions"
          placeholder="风险等级"
          clearable
          class="filter-select"
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
        v-else-if="clauses.length === 0"
        description="暂无条款，点击新建开始创建"
        class="empty-state"
      >
        <template #icon>
          <span style="font-size: 48px">📑</span>
        </template>
        <template #extra>
          <n-button type="primary" size="small" @click="openCreate">新建条款</n-button>
        </template>
      </n-empty>

      <!-- Data Table -->
      <template v-else>
        <n-data-table
          :columns="columns"
          :data="clauses"
          :row-key="(row: Clause) => row.id"
          :bordered="false"
          :single-line="false"
          striped
          class="clause-table"
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

    <!-- Create / Edit Modal -->
    <n-modal
      v-model:show="modalVisible"
      preset="card"
      :title="isEditing ? '编辑条款' : '新建条款'"
      style="width: 720px; max-width: 92vw"
      :mask-closable="false"
    >
      <n-form
        ref="formRef"
        :model="formValue"
        :rules="rules"
        label-placement="top"
        require-mark-placement="right-hanging"
      >
        <n-form-item label="条款标题" path="title">
          <n-input v-model:value="formValue.title" placeholder="请输入条款标题" maxlength="200" show-count />
        </n-form-item>
        <n-form-item label="条款内容" path="content_text">
          <n-input
            v-model:value="formValue.content_text"
            type="textarea"
            placeholder="请输入条款正文"
            :rows="8"
            class="monospace-input"
          />
        </n-form-item>
        <n-form-item label="分类" path="category">
          <n-select
            v-model:value="formValue.category"
            :options="categoryOptions"
            placeholder="选择分类"
            clearable
          />
        </n-form-item>
        <n-form-item label="风险等级" path="risk_level">
          <n-select
            v-model:value="formValue.risk_level"
            :options="riskOptions"
            placeholder="选择风险等级"
            clearable
          />
        </n-form-item>
        <n-form-item label="风险标注" path="risk_annotation">
          <n-input
            v-model:value="formValue.risk_annotation"
            type="textarea"
            placeholder="说明该条款的风险点与注意事项（可选）"
            :autosize="{ minRows: 2, maxRows: 4 }"
          />
        </n-form-item>
      </n-form>
      <template #footer>
        <div class="modal-footer">
          <n-button @click="modalVisible = false">取消</n-button>
          <n-button type="primary" :loading="saving" @click="handleSave">保存</n-button>
        </div>
      </template>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { computed, h, onMounted, reactive, ref } from 'vue'
import {
  NBadge,
  NButton,
  NCard,
  NDataTable,
  NEmpty,
  NForm,
  NFormItem,
  NIcon,
  NInput,
  NModal,
  NPagination,
  NPopconfirm,
  NSelect,
  NSkeleton,
  NTag,
  useMessage,
} from 'naive-ui'
import type { DataTableColumns, FormInst, FormRules } from 'naive-ui'
import {
  createClause,
  deleteClause,
  listClauses,
  updateClause,
  type Clause,
} from '@/api/templates'

// ─── Icons ───────────────────────────────────────────────────────────────────

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
      [h('circle', { cx: '11', cy: '11', r: '8' }), h('line', { x1: '21', y1: '21', x2: '16.65', y2: '16.65' })],
    )
  },
}

// ─── Message ─────────────────────────────────────────────────────────────────

const message = useMessage()

// ─── State ───────────────────────────────────────────────────────────────────

const loading = ref(true)
const clauses = ref<Clause[]>([])
const total = ref(0)
const currentPage = ref(1)
const pageSize = 20
const searchText = ref('')
const categoryFilter = ref<string | null>(null)
const riskFilter = ref<string | null>(null)

let searchTimer: ReturnType<typeof setTimeout> | null = null

const categoryOptions = [
  { label: '合同', value: '合同' },
  { label: '协议', value: '协议' },
  { label: '备忘录', value: '备忘录' },
  { label: '其他', value: '其他' },
]

const riskOptions = [
  { label: '严重', value: '严重' },
  { label: '高', value: '高' },
  { label: '中', value: '中' },
  { label: '低', value: '低' },
  { label: '信息', value: '信息' },
]

type TagType = 'default' | 'error' | 'warning' | 'info' | 'success'

function getRiskTagType(level: string | null): TagType {
  const map: Record<string, TagType> = {
    严重: 'error',
    高: 'warning',
    中: 'info',
    低: 'success',
    信息: 'default',
  }
  return level ? map[level] ?? 'default' : 'default'
}

// ─── Modal State ─────────────────────────────────────────────────────────────

const modalVisible = ref(false)
const saving = ref(false)
const isEditing = ref(false)
const editingId = ref<string | null>(null)
const formRef = ref<FormInst | null>(null)

const formValue = reactive({
  title: '',
  content_text: '',
  category: null as string | null,
  risk_level: null as string | null,
  risk_annotation: '',
})

const rules: FormRules = {
  title: [{ required: true, message: '请输入条款标题', trigger: ['blur', 'input'] }],
  content_text: [{ required: true, message: '请输入条款内容', trigger: ['blur', 'input'] }],
}

// ─── Computed ────────────────────────────────────────────────────────────────

const pageCount = computed(() => Math.max(1, Math.ceil(total.value / pageSize)))

// ─── Table Columns ───────────────────────────────────────────────────────────

const columns = computed<DataTableColumns<Clause>>(() => [
  {
    title: '标题',
    key: 'title',
    minWidth: 180,
    ellipsis: { tooltip: true },
    render(row) {
      return h('span', { class: 'clause-title' }, row.title)
    },
  },
  {
    title: '分类',
    key: 'category',
    width: 110,
    render(row) {
      if (!row.category) {
        return h('span', { class: 'muted-text' }, '未分类')
      }
      return h(NTag, { size: 'small', type: 'default', bordered: false }, { default: () => row.category })
    },
  },
  {
    title: '风险等级',
    key: 'risk_level',
    width: 110,
    align: 'center',
    render(row) {
      if (!row.risk_level) {
        return h('span', { class: 'muted-text' }, '—')
      }
      return h(
        NTag,
        { size: 'small', type: getRiskTagType(row.risk_level), bordered: false, round: true },
        { default: () => row.risk_level as string },
      )
    },
  },
  {
    title: '风险标注',
    key: 'risk_annotation',
    minWidth: 200,
    ellipsis: { tooltip: true },
    render(row) {
      if (!row.risk_annotation) {
        return h('span', { class: 'muted-text' }, '—')
      }
      return h('span', { class: 'annotation-text' }, row.risk_annotation)
    },
  },
  {
    title: '操作',
    key: 'actions',
    width: 180,
    align: 'center',
    render(row) {
      return h('div', { class: 'action-buttons' }, [
        h(
          NButton,
          {
            text: true,
            type: 'primary',
            size: 'small',
            onClick: (e: Event) => {
              e.stopPropagation()
              openEdit(row)
            },
          },
          { default: () => '编辑' },
        ),
        h(
          NButton,
          {
            text: true,
            type: 'info',
            size: 'small',
            style: 'margin-left: 12px',
            onClick: (e: Event) => {
              e.stopPropagation()
              handleCopy(row)
            },
          },
          { default: () => '复制' },
        ),
        h(
          NPopconfirm,
          { onPositiveClick: () => handleDelete(row) },
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
            default: () => `确定要删除条款「${row.title}」吗？此操作不可恢复。`,
          },
        ),
      ])
    },
  },
])

// ─── Data Fetching ───────────────────────────────────────────────────────────

async function fetchClauses() {
  loading.value = true
  try {
    const params: Record<string, unknown> = {
      page: currentPage.value,
      page_size: pageSize,
    }
    if (searchText.value.trim()) {
      params.search = searchText.value.trim()
    }
    if (categoryFilter.value) {
      params.category = categoryFilter.value
    }
    if (riskFilter.value) {
      params.risk_level = riskFilter.value
    }
    const data = await listClauses(params)
    clauses.value = data.items ?? []
    total.value = data.total ?? 0
  } catch {
    message.error('获取条款列表失败')
    clauses.value = []
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
    fetchClauses()
  }, 400)
}

function handleFilterChange() {
  currentPage.value = 1
  fetchClauses()
}

function handlePageChange(page: number) {
  currentPage.value = page
  fetchClauses()
}

function resetForm() {
  formValue.title = ''
  formValue.content_text = ''
  formValue.category = null
  formValue.risk_level = null
  formValue.risk_annotation = ''
}

function openCreate() {
  isEditing.value = false
  editingId.value = null
  resetForm()
  modalVisible.value = true
}

function openEdit(item: Clause) {
  isEditing.value = true
  editingId.value = item.id
  formValue.title = item.title
  formValue.content_text = item.content_text
  formValue.category = item.category || null
  formValue.risk_level = item.risk_level || null
  formValue.risk_annotation = item.risk_annotation
  modalVisible.value = true
}

async function handleSave() {
  try {
    await formRef.value?.validate()
  } catch {
    return
  }
  saving.value = true
  try {
    const payload = {
      title: formValue.title.trim(),
      content_text: formValue.content_text,
      category: formValue.category ?? '',
      risk_level: formValue.risk_level,
      risk_annotation: formValue.risk_annotation,
    }
    if (isEditing.value && editingId.value) {
      await updateClause(editingId.value, payload)
      message.success('条款已更新')
    } else {
      await createClause(payload)
      message.success('条款已创建')
    }
    modalVisible.value = false
    fetchClauses()
  } catch {
    message.error(isEditing.value ? '更新失败，请重试' : '创建失败，请重试')
  } finally {
    saving.value = false
  }
}

async function handleCopy(row: Clause) {
  try {
    await navigator.clipboard.writeText(row.content_text)
    message.success('条款内容已复制到剪贴板')
  } catch {
    message.error('复制失败，请手动复制')
  }
}

async function handleDelete(row: Clause) {
  try {
    await deleteClause(row.id)
    message.success('已删除')
    if (clauses.value.length === 1 && currentPage.value > 1) {
      currentPage.value -= 1
    }
    fetchClauses()
  } catch {
    message.error('删除失败，请重试')
  }
}

// ─── Lifecycle ───────────────────────────────────────────────────────────────

onMounted(() => {
  fetchClauses()
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

.filter-select {
  width: 150px;
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
.clause-table {
  --n-td-padding: 14px 16px;
}

.clause-title {
  font-weight: 500;
  color: var(--text-primary, #1a1a2e);
}

.annotation-text {
  font-size: 13px;
  color: var(--text-secondary, #6b7280);
}

.muted-text {
  font-size: 13px;
  color: var(--text-secondary, #999);
}

.action-buttons {
  display: flex;
  align-items: center;
  justify-content: center;
}

/* Modal */
.monospace-input :deep(textarea) {
  font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace;
  font-size: 13px;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
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

  .filter-select {
    width: 100%;
  }
}
</style>
