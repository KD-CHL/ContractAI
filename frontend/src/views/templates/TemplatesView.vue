<template>
  <div class="page-container">
    <!-- Page Header -->
    <div class="page-header">
      <div class="header-left">
        <h1 class="page-title">模板库</h1>
        <n-badge v-if="total > 0" :value="total" :max="999" type="info" class="count-badge" />
      </div>
      <n-button type="primary" @click="openCreate">
        <template #icon><span>＋</span></template>
        新建模板
      </n-button>
    </div>

    <!-- Filter Bar -->
    <div class="toolbar">
      <div class="toolbar-left">
        <n-input
          v-model:value="searchText"
          placeholder="搜索模板名称或内容..."
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
          class="category-select"
          @update:value="handleFilterChange"
        />
      </div>
    </div>

    <!-- Content -->
    <n-card :bordered="false" class="content-card">
      <!-- Loading Skeleton -->
      <div v-if="loading" class="skeleton-grid">
        <n-card v-for="n in 6" :key="n" :bordered="true" size="small" class="template-card">
          <n-skeleton height="20px" :sharp="false" style="width: 60%; margin-bottom: 12px" />
          <n-skeleton text :repeat="2" style="margin-bottom: 12px" />
          <n-skeleton height="22px" :sharp="false" style="width: 40%" />
        </n-card>
      </div>

      <!-- Empty State -->
      <n-empty
        v-else-if="templates.length === 0"
        description="暂无模板，点击新建开始创建"
        class="empty-state"
      >
        <template #icon>
          <span style="font-size: 48px">📄</span>
        </template>
        <template #extra>
          <n-button type="primary" size="small" @click="openCreate">新建模板</n-button>
        </template>
      </n-empty>

      <!-- Template Grid -->
      <template v-else>
        <n-grid :x-gap="16" :y-gap="16" cols="1 600:2 1024:3" responsive="screen">
          <n-gi v-for="item in templates" :key="item.id">
            <n-card
              :bordered="true"
              size="small"
              hoverable
              class="template-card"
              @click="openEdit(item)"
            >
              <template #header>
                <div class="card-title">{{ item.name }}</div>
              </template>
              <template #header-extra>
                <n-popconfirm @positive-click="handleDelete(item)">
                  <template #trigger>
                    <n-button
                      text
                      type="error"
                      size="small"
                      @click.stop
                    >删除</n-button>
                  </template>
                  确定要删除模板「{{ item.name }}」吗？
                </n-popconfirm>
              </template>
              <div class="card-desc">{{ item.description || '暂无描述' }}</div>
              <div class="card-footer">
                <n-tag
                  v-if="item.category"
                  size="small"
                  type="info"
                  :bordered="false"
                  round
                >{{ item.category }}</n-tag>
                <span v-else class="card-category-empty">未分类</span>
                <span class="card-time">{{ formatRelativeTime(item.created_at) }}</span>
              </div>
            </n-card>
          </n-gi>
        </n-grid>

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
      :title="isEditing ? '编辑模板' : '新建模板'"
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
        <n-form-item label="模板名称" path="name">
          <n-input v-model:value="formValue.name" placeholder="请输入模板名称" maxlength="200" show-count />
        </n-form-item>
        <n-form-item label="分类" path="category">
          <n-select
            v-model:value="formValue.category"
            :options="categoryOptions"
            placeholder="选择分类"
            clearable
          />
        </n-form-item>
        <n-form-item label="描述" path="description">
          <n-input
            v-model:value="formValue.description"
            type="textarea"
            placeholder="简要描述模板用途（可选）"
            :autosize="{ minRows: 2, maxRows: 4 }"
          />
        </n-form-item>
        <n-form-item label="模板内容" path="content_text">
          <n-input
            v-model:value="formValue.content_text"
            type="textarea"
            placeholder="粘贴或编写模板正文..."
            :rows="12"
            class="monospace-input"
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
  NEmpty,
  NForm,
  NFormItem,
  NGi,
  NGrid,
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
import type { FormInst, FormRules } from 'naive-ui'
import {
  createTemplate,
  deleteTemplate,
  listTemplates,
  updateTemplate,
  type ContractTemplate,
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
const templates = ref<ContractTemplate[]>([])
const total = ref(0)
const currentPage = ref(1)
const pageSize = 12
const searchText = ref('')
const categoryFilter = ref<string | null>(null)

let searchTimer: ReturnType<typeof setTimeout> | null = null

const categoryOptions = [
  { label: '合同', value: '合同' },
  { label: '协议', value: '协议' },
  { label: '备忘录', value: '备忘录' },
  { label: '其他', value: '其他' },
]

// ─── Modal State ─────────────────────────────────────────────────────────────

const modalVisible = ref(false)
const saving = ref(false)
const isEditing = ref(false)
const editingId = ref<string | null>(null)
const formRef = ref<FormInst | null>(null)

const formValue = reactive({
  name: '',
  category: null as string | null,
  description: '',
  content_text: '',
})

const rules: FormRules = {
  name: [{ required: true, message: '请输入模板名称', trigger: ['blur', 'input'] }],
}

// ─── Computed ────────────────────────────────────────────────────────────────

const pageCount = computed(() => Math.max(1, Math.ceil(total.value / pageSize)))

// ─── Helpers ─────────────────────────────────────────────────────────────────

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

function resetForm() {
  formValue.name = ''
  formValue.category = null
  formValue.description = ''
  formValue.content_text = ''
}

// ─── Data Fetching ───────────────────────────────────────────────────────────

async function fetchTemplates() {
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
    const data = await listTemplates(params)
    templates.value = data.items ?? []
    total.value = data.total ?? 0
  } catch {
    message.error('获取模板列表失败')
    templates.value = []
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
    fetchTemplates()
  }, 400)
}

function handleFilterChange() {
  currentPage.value = 1
  fetchTemplates()
}

function handlePageChange(page: number) {
  currentPage.value = page
  fetchTemplates()
}

function openCreate() {
  isEditing.value = false
  editingId.value = null
  resetForm()
  modalVisible.value = true
}

function openEdit(item: ContractTemplate) {
  isEditing.value = true
  editingId.value = item.id
  formValue.name = item.name
  formValue.category = item.category || null
  formValue.description = item.description
  formValue.content_text = item.content_text
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
      name: formValue.name.trim(),
      category: formValue.category ?? '',
      description: formValue.description,
      content_text: formValue.content_text,
    }
    if (isEditing.value && editingId.value) {
      await updateTemplate(editingId.value, payload)
      message.success('模板已更新')
    } else {
      await createTemplate(payload)
      message.success('模板已创建')
    }
    modalVisible.value = false
    fetchTemplates()
  } catch {
    message.error(isEditing.value ? '更新失败，请重试' : '创建失败，请重试')
  } finally {
    saving.value = false
  }
}

async function handleDelete(item: ContractTemplate) {
  try {
    await deleteTemplate(item.id)
    message.success('已删除')
    if (templates.value.length === 1 && currentPage.value > 1) {
      currentPage.value -= 1
    }
    fetchTemplates()
  } catch {
    message.error('删除失败，请重试')
  }
}

// ─── Lifecycle ───────────────────────────────────────────────────────────────

onMounted(() => {
  fetchTemplates()
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

.category-select {
  width: 160px;
}

/* Content Card */
.content-card {
  border-radius: var(--radius-md, 10px);
  box-shadow: var(--card-shadow, 0 2px 12px rgba(0, 0, 0, 0.06));
}

.skeleton-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
}

.empty-state {
  padding: 60px 0;
}

/* Template Card */
.template-card {
  cursor: pointer;
  border-radius: var(--radius-md, 10px);
  transition: box-shadow 0.2s ease, transform 0.2s ease;
  height: 100%;
}

.template-card:hover {
  box-shadow: 0 6px 20px rgba(0, 0, 0, 0.1);
}

.card-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-primary, #1a1a2e);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.card-desc {
  font-size: 13px;
  color: var(--text-secondary, #6b7280);
  line-height: 1.5;
  min-height: 40px;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.card-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 14px;
}

.card-category-empty {
  font-size: 12px;
  color: var(--text-secondary, #999);
}

.card-time {
  font-size: 12px;
  color: var(--text-secondary, #999);
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
@media (max-width: 1024px) {
  .skeleton-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

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

  .category-select {
    width: 100%;
  }

  .skeleton-grid {
    grid-template-columns: 1fr;
  }
}
</style>
