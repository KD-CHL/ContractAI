<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">合同对比</h1>
      <n-button v-if="comparisonResult" quaternary size="small" @click="resetSelection">
        <template #icon><n-icon><ArrowBackIcon /></n-icon></template>
        重新选择
      </n-button>
    </div>

    <!-- Step 1: Selection -->
    <template v-if="!comparisonResult">
      <div class="selection-area">
        <n-grid :cols="2" :x-gap="16">
          <n-gi>
            <n-card title="合同 A" :bordered="false" class="selection-card">
              <n-select
                v-model:value="reviewAId"
                :options="reviewOptions"
                filterable
                placeholder="选择第一份合同审阅记录"
                :loading="loadingReviews"
              />
            </n-card>
          </n-gi>
          <n-gi>
            <n-card title="合同 B" :bordered="false" class="selection-card">
              <n-select
                v-model:value="reviewBId"
                :options="reviewOptions"
                filterable
                placeholder="选择第二份合同审阅记录"
                :loading="loadingReviews"
              />
            </n-card>
          </n-gi>
        </n-grid>

        <div class="compare-action">
          <div class="connect-arrow">
            <n-icon size="28" color="var(--primary-color, #18a058)"><SwapIcon /></n-icon>
          </div>
          <n-button
            type="primary"
            size="large"
            :disabled="!reviewAId || !reviewBId || reviewAId === reviewBId"
            :loading="comparing"
            @click="startCompare"
          >
            开始对比
          </n-button>
          <p v-if="reviewAId && reviewBId && reviewAId === reviewBId" class="hint-text">
            请选择两份不同的合同
          </p>
        </div>
      </div>
    </template>

    <!-- Loading state -->
    <template v-if="comparing">
      <n-card :bordered="false" class="content-card">
        <div class="loading-area">
          <n-progress type="line" :percentage="100" :show-indicator="false" status="info" :rail-height="4" processing />
          <p class="loading-text">正在对比分析...</p>
        </div>
      </n-card>
    </template>

    <!-- Step 2: Results -->
    <template v-if="comparisonResult && !comparing">
      <!-- Summary cards -->
      <n-grid :cols="4" :x-gap="14" :y-gap="14" class="summary-grid">
        <n-gi>
          <n-card :bordered="false" class="metric-card metric-card--added">
            <n-statistic label="新增条款" :value="comparisonResult.summary.added" />
          </n-card>
        </n-gi>
        <n-gi>
          <n-card :bordered="false" class="metric-card metric-card--removed">
            <n-statistic label="删除条款" :value="comparisonResult.summary.removed" />
          </n-card>
        </n-gi>
        <n-gi>
          <n-card :bordered="false" class="metric-card metric-card--modified">
            <n-statistic label="修改条款" :value="comparisonResult.summary.modified" />
          </n-card>
        </n-gi>
        <n-gi>
          <n-card :bordered="false" class="metric-card metric-card--unchanged">
            <n-statistic label="未变化" :value="comparisonResult.summary.unchanged" />
          </n-card>
        </n-gi>
      </n-grid>

      <!-- Risk Delta panel -->
      <n-card title="风险变化" :bordered="false" class="content-card risk-delta-card">
        <n-grid :cols="3" :x-gap="16">
          <n-gi>
            <div class="risk-section">
              <h4 class="risk-section-title risk-section-title--new">
                新增风险
                <n-tag size="small" type="error" round>{{ comparisonResult.risk_delta.new_risks.length }}</n-tag>
              </h4>
              <div v-if="comparisonResult.risk_delta.new_risks.length === 0" class="risk-empty">
                无新增风险
              </div>
              <div v-else class="risk-list">
                <div
                  v-for="(risk, idx) in comparisonResult.risk_delta.new_risks"
                  :key="'new-' + idx"
                  class="risk-item risk-item--new"
                >
                  <span class="risk-item-title">{{ risk.title }}</span>
                  <n-tag size="tiny" :type="riskTagType(risk.risk_level)">{{ risk.risk_level }}</n-tag>
                  <span class="risk-item-source">{{ risk.source }}</span>
                </div>
              </div>
            </div>
          </n-gi>
          <n-gi>
            <div class="risk-section">
              <h4 class="risk-section-title risk-section-title--resolved">
                消除风险
                <n-tag size="small" type="success" round>{{ comparisonResult.risk_delta.resolved_risks.length }}</n-tag>
              </h4>
              <div v-if="comparisonResult.risk_delta.resolved_risks.length === 0" class="risk-empty">
                无消除风险
              </div>
              <div v-else class="risk-list">
                <div
                  v-for="(risk, idx) in comparisonResult.risk_delta.resolved_risks"
                  :key="'resolved-' + idx"
                  class="risk-item risk-item--resolved"
                >
                  <span class="risk-item-title">{{ risk.title }}</span>
                  <n-tag size="tiny" :type="riskTagType(risk.risk_level)">{{ risk.risk_level }}</n-tag>
                  <span class="risk-item-source">{{ risk.source }}</span>
                </div>
              </div>
            </div>
          </n-gi>
          <n-gi>
            <div class="risk-section">
              <h4 class="risk-section-title risk-section-title--unchanged">未变化</h4>
              <div class="risk-unchanged-count">
                <n-statistic :value="comparisonResult.risk_delta.unchanged_count" />
                <span class="risk-unchanged-label">项风险保持不变</span>
              </div>
            </div>
          </n-gi>
        </n-grid>
      </n-card>

      <!-- Side-by-side clause diff -->
      <n-card title="条款对比" :bordered="false" class="content-card">
        <n-grid :cols="2" :x-gap="16">
          <!-- Column A -->
          <n-gi>
            <div class="diff-column">
              <h4 class="diff-column-title">合同 A（{{ comparisonResult.summary.total_clauses_a }} 条）</h4>
              <div class="diff-clauses">
                <div
                  v-for="clause in comparisonResult.clauses_a"
                  :key="'a-' + clause.index"
                  class="diff-clause"
                  :class="'diff-clause--' + clause.status"
                >
                  <span class="diff-clause-line">{{ clause.index + 1 }}</span>
                  <div class="diff-clause-body">
                    <p class="diff-clause-text">{{ clause.text }}</p>
                    <span v-if="clause.status === 'modified'" class="diff-clause-badge diff-clause-badge--modified">
                      修改
                    </span>
                    <span v-else-if="clause.status === 'removed'" class="diff-clause-badge diff-clause-badge--removed">
                      删除
                    </span>
                  </div>
                </div>
                <div v-if="comparisonResult.clauses_a.length === 0" class="diff-empty">
                  无条款内容
                </div>
              </div>
            </div>
          </n-gi>
          <!-- Column B -->
          <n-gi>
            <div class="diff-column">
              <h4 class="diff-column-title">合同 B（{{ comparisonResult.summary.total_clauses_b }} 条）</h4>
              <div class="diff-clauses">
                <div
                  v-for="clause in comparisonResult.clauses_b"
                  :key="'b-' + clause.index"
                  class="diff-clause"
                  :class="'diff-clause--' + clause.status"
                >
                  <span class="diff-clause-line">{{ clause.index + 1 }}</span>
                  <div class="diff-clause-body">
                    <p class="diff-clause-text">{{ clause.text }}</p>
                    <span v-if="clause.status === 'modified'" class="diff-clause-badge diff-clause-badge--modified">
                      修改
                    </span>
                    <span v-else-if="clause.status === 'added'" class="diff-clause-badge diff-clause-badge--added">
                      新增
                    </span>
                  </div>
                </div>
                <div v-if="comparisonResult.clauses_b.length === 0" class="diff-empty">
                  无条款内容
                </div>
              </div>
            </div>
          </n-gi>
        </n-grid>

        <!-- Similarity info for modified pairs -->
        <template v-if="modifiedPairs.length > 0">
          <n-divider />
          <h4 class="similarity-title">修改相似度</h4>
          <div class="similarity-list">
            <div v-for="pair in modifiedPairs" :key="'sim-' + pair.index_a + '-' + pair.index_b" class="similarity-item">
              <span>条款 A#{{ (pair.index_a ?? 0) + 1 }} ↔ B#{{ (pair.index_b ?? 0) + 1 }}</span>
              <n-progress
                type="line"
                :percentage="Math.round(pair.similarity * 100)"
                :status="pair.similarity > 0.7 ? 'success' : pair.similarity > 0.4 ? 'warning' : 'error'"
                :rail-height="6"
                style="flex: 1; margin: 0 12px;"
              />
              <span class="similarity-value">{{ Math.round(pair.similarity * 100) }}%</span>
            </div>
          </div>
        </template>
      </n-card>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, h, onMounted, ref } from 'vue'
import {
  NButton,
  NCard,
  NDivider,
  NGi,
  NGrid,
  NIcon,
  NProgress,
  NSelect,
  NStatistic,
  NTag,
  useMessage,
} from 'naive-ui'
import { get, post } from '@/api/client'

// ─── Icons (inline render functions to avoid extra deps) ─────────────────────

const ArrowBackIcon = {
  render() {
    return h('svg', { xmlns: 'http://www.w3.org/2000/svg', viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': '2', 'stroke-linecap': 'round', 'stroke-linejoin': 'round', width: '1em', height: '1em' }, [
      h('path', { d: 'M19 12H5' }),
      h('path', { d: 'M12 19l-7-7 7-7' }),
    ])
  },
}

const SwapIcon = {
  render() {
    return h('svg', { xmlns: 'http://www.w3.org/2000/svg', viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': '2', 'stroke-linecap': 'round', 'stroke-linejoin': 'round', width: '1em', height: '1em' }, [
      h('path', { d: 'M8 3L4 7l4 4' }),
      h('path', { d: 'M4 7h16' }),
      h('path', { d: 'M16 21l4-4-4-4' }),
      h('path', { d: 'M20 17H4' }),
    ])
  },
}

// ─── Types ───────────────────────────────────────────────────────────────────

interface ClauseEntry {
  index: number
  text: string
  status: 'unchanged' | 'modified' | 'removed' | 'added'
}

interface DiffPair {
  index_a: number | null
  index_b: number | null
  similarity: number
  status: string
}

interface RiskDeltaItem {
  title: string
  risk_level: string
  source: string
}

interface RiskDelta {
  new_risks: RiskDeltaItem[]
  resolved_risks: RiskDeltaItem[]
  unchanged_count: number
}

interface CompareSummary {
  total_clauses_a: number
  total_clauses_b: number
  added: number
  removed: number
  modified: number
  unchanged: number
}

interface CompareResponse {
  clauses_a: ClauseEntry[]
  clauses_b: ClauseEntry[]
  diff_pairs: DiffPair[]
  risk_delta: RiskDelta
  summary: CompareSummary
}

interface ReviewOption {
  label: string
  value: string
}

// ─── State ───────────────────────────────────────────────────────────────────

const message = useMessage()

const reviewAId = ref<string | null>(null)
const reviewBId = ref<string | null>(null)
const reviewOptions = ref<ReviewOption[]>([])
const loadingReviews = ref(false)
const comparing = ref(false)
const comparisonResult = ref<CompareResponse | null>(null)

const modifiedPairs = computed(() =>
  (comparisonResult.value?.diff_pairs ?? []).filter((p) => p.status === 'modified'),
)

// ─── Methods ─────────────────────────────────────────────────────────────────

function riskTagType(level: string): 'error' | 'warning' | 'info' | 'success' {
  switch (level) {
    case 'critical':
    case 'high':
      return 'error'
    case 'medium':
      return 'warning'
    case 'low':
      return 'info'
    default:
      return 'success'
  }
}

async function loadReviews() {
  loadingReviews.value = true
  try {
    const res = await get<{ items: Array<{ review_id: string; document_name: string; status: string; created_at: string }> }>('/reviews', {
      params: { page_size: 100 },
    })
    reviewOptions.value = (res.items ?? []).map((item) => ({
      label: `${item.document_name || item.review_id} (${item.status})`,
      value: item.review_id,
    }))
  } catch (err: any) {
    message.error(err?.detail || '加载审阅列表失败')
  } finally {
    loadingReviews.value = false
  }
}

async function startCompare() {
  if (!reviewAId.value || !reviewBId.value) return
  if (reviewAId.value === reviewBId.value) {
    message.warning('请选择两份不同的合同')
    return
  }

  comparing.value = true
  comparisonResult.value = null
  try {
    const res = await post<CompareResponse>('/compare', {
      review_a_id: reviewAId.value,
      review_b_id: reviewBId.value,
    })
    comparisonResult.value = res
  } catch (err: any) {
    message.error(err?.detail || '对比分析失败')
  } finally {
    comparing.value = false
  }
}

function resetSelection() {
  comparisonResult.value = null
  reviewAId.value = null
  reviewBId.value = null
}

// ─── Lifecycle ───────────────────────────────────────────────────────────────

onMounted(() => {
  loadReviews()
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
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
}

.page-title {
  font-size: 22px;
  font-weight: 700;
  margin: 0;
  color: var(--text-primary);
}

/* ─── Selection ─────────────────────────────────────────────────────────── */

.selection-area {
  margin-top: 12px;
}

.selection-card {
  border-radius: var(--radius-md, 10px);
  box-shadow: var(--card-shadow);
}

.compare-action {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  margin-top: 24px;
}

.connect-arrow {
  display: flex;
  align-items: center;
  justify-content: center;
}

.hint-text {
  font-size: 13px;
  color: var(--text-tertiary, #999);
  margin: 0;
}

/* ─── Loading ───────────────────────────────────────────────────────────── */

.loading-area {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
  padding: 48px 0;
}

.loading-text {
  font-size: 15px;
  color: var(--text-secondary, #666);
  margin: 0;
}

/* ─── Summary cards ─────────────────────────────────────────────────────── */

.summary-grid {
  margin-bottom: 16px;
}

.metric-card {
  border-radius: var(--radius-md, 10px);
  box-shadow: var(--card-shadow);
}

.metric-card--added {
  border-left: 3px solid #18a058;
}

.metric-card--removed {
  border-left: 3px solid #d03050;
}

.metric-card--modified {
  border-left: 3px solid #f0a020;
}

.metric-card--unchanged {
  border-left: 3px solid #909399;
}

/* ─── Content cards ─────────────────────────────────────────────────────── */

.content-card {
  border-radius: var(--radius-md, 10px);
  box-shadow: var(--card-shadow);
  margin-bottom: 16px;
}

/* ─── Risk delta ────────────────────────────────────────────────────────── */

.risk-delta-card {
  margin-bottom: 16px;
}

.risk-section {
  min-height: 120px;
}

.risk-section-title {
  font-size: 14px;
  font-weight: 600;
  margin: 0 0 12px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.risk-section-title--new {
  color: #d03050;
}

.risk-section-title--resolved {
  color: #18a058;
}

.risk-section-title--unchanged {
  color: var(--text-secondary, #666);
}

.risk-empty {
  font-size: 13px;
  color: var(--text-tertiary, #999);
  padding: 8px 0;
}

.risk-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.risk-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 10px;
  border-radius: 6px;
  font-size: 13px;
}

.risk-item--new {
  background: rgba(208, 48, 80, 0.06);
  border: 1px solid rgba(208, 48, 80, 0.15);
}

.risk-item--resolved {
  background: rgba(24, 160, 88, 0.06);
  border: 1px solid rgba(24, 160, 88, 0.15);
}

.risk-item-title {
  flex: 1;
  font-weight: 500;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.risk-item-source {
  font-size: 11px;
  color: var(--text-tertiary, #999);
}

.risk-unchanged-count {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 16px 0;
}

.risk-unchanged-label {
  font-size: 12px;
  color: var(--text-tertiary, #999);
  margin-top: 4px;
}

/* ─── Clause diff ───────────────────────────────────────────────────────── */

.diff-column {
  min-width: 0;
}

.diff-column-title {
  font-size: 14px;
  font-weight: 600;
  margin: 0 0 12px;
  color: var(--text-secondary, #666);
}

.diff-clauses {
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-height: 600px;
  overflow-y: auto;
  padding-right: 4px;
}

.diff-clause {
  display: flex;
  gap: 10px;
  padding: 10px 12px;
  border-radius: 6px;
  border-left: 3px solid #e0e0e6;
  background: var(--card-color, #fff);
}

.diff-clause--added {
  border-left-color: #18a058;
  background: rgba(24, 160, 88, 0.05);
}

.diff-clause--removed {
  border-left-color: #d03050;
  background: rgba(208, 48, 80, 0.05);
}

.diff-clause--modified {
  border-left-color: #f0a020;
  background: rgba(240, 160, 32, 0.05);
}

.diff-clause--unchanged {
  border-left-color: #e0e0e6;
}

.diff-clause-line {
  flex-shrink: 0;
  width: 24px;
  font-size: 11px;
  color: var(--text-tertiary, #999);
  text-align: right;
  padding-top: 2px;
  user-select: none;
}

.diff-clause-body {
  flex: 1;
  min-width: 0;
}

.diff-clause-text {
  margin: 0;
  font-size: 13px;
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-word;
  color: var(--text-primary);
}

.diff-clause-badge {
  display: inline-block;
  margin-top: 4px;
  font-size: 11px;
  padding: 1px 6px;
  border-radius: 3px;
  font-weight: 500;
}

.diff-clause-badge--added {
  color: #18a058;
  background: rgba(24, 160, 88, 0.1);
}

.diff-clause-badge--removed {
  color: #d03050;
  background: rgba(208, 48, 80, 0.1);
}

.diff-clause-badge--modified {
  color: #f0a020;
  background: rgba(240, 160, 32, 0.1);
}

.diff-empty {
  font-size: 13px;
  color: var(--text-tertiary, #999);
  padding: 24px 0;
  text-align: center;
}

/* ─── Similarity ────────────────────────────────────────────────────────── */

.similarity-title {
  font-size: 14px;
  font-weight: 600;
  margin: 0 0 12px;
  color: var(--text-secondary, #666);
}

.similarity-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.similarity-item {
  display: flex;
  align-items: center;
  font-size: 13px;
  color: var(--text-secondary, #666);
}

.similarity-value {
  flex-shrink: 0;
  width: 40px;
  text-align: right;
  font-weight: 600;
  font-size: 13px;
}
</style>
