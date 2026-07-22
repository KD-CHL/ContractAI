<template>
  <div class="review-detail">
    <!-- Back button -->
    <n-button text @click="router.push('/reviews')" class="back-btn">
      ← 返回列表
    </n-button>

    <!-- Loading skeleton -->
    <template v-if="loading">
      <n-skeleton height="48px" width="60%" style="margin-bottom: 16px" />
      <n-skeleton height="36px" width="100%" style="margin-bottom: 12px" />
      <n-grid :cols="4" :x-gap="16" style="margin-bottom: 24px">
        <n-gi v-for="i in 4" :key="i"><n-skeleton height="100px" /></n-gi>
      </n-grid>
      <n-skeleton height="300px" />
    </template>

    <!-- 404 Not Found -->
    <n-result v-else-if="notFound" status="404" title="未找到审阅记录" description="该审阅不存在或已被永久删除">
      <template #footer>
        <n-button type="primary" @click="router.push('/reviews')">返回列表</n-button>
      </template>
    </n-result>

    <!-- Error alert -->
    <n-alert v-else-if="errorMsg" type="error" :title="errorMsg" closable style="margin-bottom: 16px">
      <n-button size="small" @click="fetchReview">重试</n-button>
    </n-alert>

    <!-- Main content -->
    <template v-else-if="review">
      <!-- Header: document name + status badges -->
      <div class="detail-header">
        <h1 class="detail-title">{{ review.file_name || '未命名合同' }}</h1>
        <div class="header-badges">
          <n-tag :type="decisionTagType" size="medium" round>
            {{ decisionStatusLabel }}
          </n-tag>
          <n-tag v-if="review.is_deleted" type="error" size="medium" round>
            已删除
          </n-tag>
        </div>
      </div>

      <!-- Action bar -->
      <div class="action-bar">
        <n-space>
          <n-button
            tag="a"
            :href="`/api/v1/reviews/${reviewId}/export?format=html`"
            target="_blank"
            secondary
          >
            导出HTML
          </n-button>
          <n-popconfirm
            v-if="canDeleteReview"
            @positive-click="handleToggleDelete"
            :positive-text="review.is_deleted ? '确认恢复' : '确认删除'"
            negative-text="取消"
          >
            <template #trigger>
              <n-button :type="review.is_deleted ? 'success' : 'error'" secondary>
                {{ review.is_deleted ? '恢复' : '删除' }}
              </n-button>
            </template>
            {{ review.is_deleted ? '确定要恢复该审阅记录吗？' : '确定要删除该审阅记录吗？删除后可恢复。' }}
          </n-popconfirm>
        </n-space>
      </div>

      <!-- Approval workflow section -->
      <n-card v-if="canApprove" size="small" class="section-card approval-card">
        <template #header>
          <span class="section-title">审批流程</span>
        </template>
        <div class="approval-content">
          <div class="approval-status">
            <span class="approval-label">当前状态：</span>
            <n-tag :type="decisionTagType" size="small">{{ decisionStatusLabel }}</n-tag>
            <span v-if="review.decision?.decided_by" class="approval-meta">
              （{{ review.decision.decided_by }} 于 {{ formatTime(review.decision.decided_at) }}）
            </span>
          </div>
          <n-space class="approval-actions">
            <!-- draft → 提交审阅 -->
            <n-button
              v-if="decisionStatus === 'draft'"
              type="primary"
              :loading="decisionLoading"
              @click="submitDecision('submit')"
            >
              提交审阅
            </n-button>
            <!-- in_review → 批准 / 拒绝 -->
            <template v-if="decisionStatus === 'in_review'">
              <n-button type="success" :loading="decisionLoading" @click="openNoteDialog('approve')">
                批准
              </n-button>
              <n-button type="error" :loading="decisionLoading" @click="openNoteDialog('reject')">
                拒绝
              </n-button>
            </template>
            <!-- rejected → 重新提交 -->
            <n-button
              v-if="decisionStatus === 'rejected'"
              type="warning"
              :loading="decisionLoading"
              @click="submitDecision('resubmit')"
            >
              重新提交
            </n-button>
            <!-- approved → 重新打开 (admin only) -->
            <n-button
              v-if="decisionStatus === 'approved' && isAdmin"
              secondary
              :loading="decisionLoading"
              @click="submitDecision('reopen')"
            >
              重新打开
            </n-button>
          </n-space>
        </div>
      </n-card>

      <!-- Summary cards -->
      <n-grid :cols="4" :x-gap="16" :y-gap="16" class="summary-grid">
        <n-gi>
          <n-card size="small" class="stat-card">
            <n-statistic label="风险发现数" :value="totalFindings" />
          </n-card>
        </n-gi>
        <n-gi>
          <n-card size="small" class="stat-card">
            <n-statistic label="高风险项">
              <template #default>
                <span :class="{ 'stat-danger': highRiskCount > 0 }">{{ highRiskCount }}</span>
              </template>
            </n-statistic>
          </n-card>
        </n-gi>
        <n-gi>
          <n-card size="small" class="stat-card">
            <n-statistic label="义务条款" :value="obligationsCount" />
          </n-card>
        </n-gi>
        <n-gi>
          <n-card size="small" class="stat-card">
            <n-statistic label="证据覆盖率">
              <template #default>
                <span>{{ evidenceCoverage }}%</span>
              </template>
            </n-statistic>
          </n-card>
        </n-gi>
      </n-grid>

      <!-- Findings section -->
      <n-card size="small" class="section-card" v-if="findings.length > 0">
        <template #header>
          <span class="section-title">风险发现</span>
        </template>
        <n-tabs v-model:value="activeFilter" type="line" animated>
          <n-tab-pane name="all" :tab="`全部 (${findings.length})`" />
          <n-tab-pane name="critical" :tab="`严重 (${countByLevel('critical')})`" />
          <n-tab-pane name="high" :tab="`高 (${countByLevel('high')})`" />
          <n-tab-pane name="medium" :tab="`中 (${countByLevel('medium')})`" />
          <n-tab-pane name="low" :tab="`低 (${countByLevel('low')})`" />
          <n-tab-pane name="info" :tab="`信息 (${countByLevel('info')})`" />
        </n-tabs>

        <div class="findings-list">
          <n-card
            v-for="finding in filteredFindings"
            :key="finding.id"
            size="small"
            class="finding-card"
            :segmented="{ content: true }"
          >
            <template #header>
              <div class="finding-header">
                <n-tag :color="{ color: riskColor(finding.risk_level).bg, textColor: riskColor(finding.risk_level).text }" size="small" round>
                  {{ riskLevelLabel(finding.risk_level) }}
                </n-tag>
                <span class="finding-title">{{ finding.title }}</span>
              </div>
            </template>
            <template #header-extra>
              <n-space size="small" align="center">
                <n-tag size="tiny" :bordered="false" type="info">{{ sourceLabel(finding.source) }}</n-tag>
                <n-tag v-if="finding.confidence != null" size="tiny" :bordered="false">
                  置信度 {{ Math.round(finding.confidence * 100) }}%
                </n-tag>
              </n-space>
            </template>

            <p class="finding-desc">{{ finding.description }}</p>

            <!-- Evidence quotes -->
            <div v-if="finding.evidence && finding.evidence.length > 0" class="finding-evidence">
              <n-blockquote v-for="(ev, idx) in finding.evidence" :key="idx" class="evidence-quote">
                {{ ev.text }}
                <template v-if="ev.clause_ref || ev.location">
                  <n-text depth="3" class="evidence-source">
                    —— {{ ev.clause_ref || ev.location }}{{ ev.page ? ` (第${ev.page}页)` : '' }}
                  </n-text>
                </template>
              </n-blockquote>
            </div>

            <!-- Recommendation -->
            <div v-if="finding.recommendation" class="finding-recommendation">
              <n-text strong>建议：</n-text>
              <n-text>{{ finding.recommendation }}</n-text>
            </div>

            <!-- Feedback buttons -->
            <div class="finding-feedback">
              <n-space size="small">
                <n-button
                  size="tiny"
                  :type="feedbackState[finding.id] === 'helpful' ? 'success' : 'default'"
                  secondary
                  @click="submitFeedback(finding.id, 'helpful')"
                >
                  👍 有帮助
                </n-button>
                <n-button
                  size="tiny"
                  :type="feedbackState[finding.id] === 'needs_review' ? 'warning' : 'default'"
                  secondary
                  @click="submitFeedback(finding.id, 'needs_review')"
                >
                  🔍 需复核
                </n-button>
              </n-space>
            </div>
          </n-card>
        </div>
      </n-card>

      <!-- Obligations section -->
      <n-card size="small" class="section-card" v-if="obligations.length > 0">
        <template #header>
          <span class="section-title">义务条款</span>
        </template>
        <n-table :bordered="false" :single-line="false" size="small" class="obligations-table">
          <thead>
            <tr>
              <th>义务方</th>
              <th>行为</th>
              <th>期限</th>
              <th>条件</th>
              <th>来源引用</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="ob in obligations" :key="ob.id">
              <td>{{ ob.party }}</td>
              <td>{{ ob.description }}</td>
              <td>{{ ob.deadline || '—' }}</td>
              <td>
                <template v-if="ob.conditions && ob.conditions.length > 0">
                  <span v-for="(c, i) in ob.conditions" :key="i">{{ c }}<br v-if="i < ob.conditions!.length - 1" /></span>
                </template>
                <span v-else>—</span>
              </td>
              <td>
                <n-collapse v-if="ob.clause_ref" class="source-collapse">
                  <n-collapse-item :title="ob.clause_ref" name="src">
                    <n-text depth="3">{{ ob.source_quote || '暂无原文引用' }}</n-text>
                  </n-collapse-item>
                </n-collapse>
                <span v-else>—</span>
              </td>
            </tr>
          </tbody>
        </n-table>
      </n-card>

      <!-- Quality & Context panel -->
      <n-card size="small" class="section-card">
        <n-collapse default-expanded-names="quality">
          <n-collapse-item title="质量与上下文" name="quality">
            <!-- Quality metrics -->
            <n-descriptions label-placement="left" :column="3" size="small" bordered>
              <n-descriptions-item label="AI是否参与">
                <n-tag :type="qualityData?.ai_involved ? 'info' : 'default'" size="small">
                  {{ qualityData?.ai_involved ? '是' : '否' }}
                </n-tag>
              </n-descriptions-item>
              <n-descriptions-item label="验证通过数">
                {{ qualityData?.validations_passed ?? '—' }}
              </n-descriptions-item>
              <n-descriptions-item label="完整度">
                {{ qualityData?.completeness_score != null ? `${qualityData.completeness_score}%` : '—' }}
              </n-descriptions-item>
            </n-descriptions>

            <!-- Warnings -->
            <div v-if="qualityWarnings.length > 0" class="quality-warnings">
              <n-text strong style="display: block; margin-bottom: 8px">警告信息：</n-text>
              <n-alert v-for="(w, i) in qualityWarnings" :key="i" type="warning" size="small" style="margin-bottom: 6px">
                {{ w }}
              </n-alert>
            </div>

            <!-- Knowledge sources -->
            <div v-if="knowledgeSources.length > 0" class="quality-sources">
              <n-text strong style="display: block; margin-bottom: 8px">知识来源：</n-text>
              <n-space size="small">
                <n-tag v-for="(src, i) in knowledgeSources" :key="i" size="small" :bordered="false" type="info">
                  {{ src }}
                </n-tag>
              </n-space>
            </div>

            <!-- Legal disclaimer -->
            <n-alert type="info" size="small" style="margin-top: 12px">
              本审阅报告由AI辅助生成，仅供参考，不构成法律意见。具体法律问题请咨询专业律师。
            </n-alert>
          </n-collapse-item>
        </n-collapse>
      </n-card>
    </template>

    <!-- Note input dialog for approve/reject -->
    <n-modal v-model:show="noteDialogVisible" preset="dialog" :title="noteDialogTitle">
      <n-input
        v-model:value="noteText"
        type="textarea"
        placeholder="请输入审批意见（可选）"
        :rows="3"
        :maxlength="500"
        show-count
      />
      <template #action>
        <n-space>
          <n-button @click="noteDialogVisible = false">取消</n-button>
          <n-button type="primary" :loading="decisionLoading" @click="confirmNoteDecision">
            确认
          </n-button>
        </n-space>
      </template>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, reactive } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import {
  NButton, NSkeleton, NResult, NAlert, NTag, NCard, NGrid, NGi,
  NStatistic, NTabs, NTabPane, NBlockquote, NText, NTable,
  NCollapse, NCollapseItem, NDescriptions, NDescriptionsItem,
  NSpace, NPopconfirm, NModal, NInput, useMessage,
} from 'naive-ui'
import { get, patch, post, del } from '@/api/client'
import { usePermission } from '@/composables/usePermission'
import type { ReviewDetail, RiskFinding, Obligation } from '@/types/api'

// ─── Extended local types ─────────────────────────────────────────────────────

interface ExtendedFinding extends Omit<RiskFinding, 'risk_level'> {
  risk_level: 'critical' | 'high' | 'medium' | 'low' | 'info'
  source?: 'rule' | 'ai' | 'hybrid'
  confidence?: number
}

interface ExtendedObligation extends Obligation {
  clause_ref?: string
  source_quote?: string
}

interface QualityData {
  ai_involved?: boolean
  validations_passed?: number
  completeness_score?: number
  evidence_coverage?: number
  warnings?: string[]
  knowledge_sources?: string[]
}

interface ExtendedReviewDetail extends ReviewDetail {
  decision_status?: 'draft' | 'in_review' | 'approved' | 'rejected'
  quality?: QualityData
}

// ─── Router & permissions ─────────────────────────────────────────────────────

const router = useRouter()
const route = useRoute()
const message = useMessage()
const { canApprove, canDeleteReview, isAdmin } = usePermission()

const reviewId = computed(() => route.params.id as string)

// ─── State ────────────────────────────────────────────────────────────────────

const loading = ref(true)
const notFound = ref(false)
const errorMsg = ref('')
const review = ref<ExtendedReviewDetail | null>(null)
const decisionLoading = ref(false)

// Findings filter
const activeFilter = ref<'all' | 'critical' | 'high' | 'medium' | 'low' | 'info'>('all')

// Feedback state per finding
const feedbackState = reactive<Record<string, 'helpful' | 'needs_review'>>({})

// Note dialog
const noteDialogVisible = ref(false)
const noteText = ref('')
const pendingAction = ref<'approve' | 'reject'>('approve')

// ─── Computed ─────────────────────────────────────────────────────────────────

const decisionStatus = computed(() => review.value?.decision_status ?? 'draft')

const decisionStatusLabel = computed(() => {
  const map: Record<string, string> = {
    draft: '草稿',
    in_review: '审阅中',
    approved: '已批准',
    rejected: '已拒绝',
  }
  return map[decisionStatus.value] ?? decisionStatus.value
})

const decisionTagType = computed(() => {
  const map: Record<string, 'default' | 'info' | 'success' | 'error' | 'warning'> = {
    draft: 'default',
    in_review: 'info',
    approved: 'success',
    rejected: 'error',
  }
  return map[decisionStatus.value] ?? 'default'
})

const findings = computed<ExtendedFinding[]>(() => {
  return (review.value?.report?.risk_findings as ExtendedFinding[]) ?? []
})

const filteredFindings = computed(() => {
  if (activeFilter.value === 'all') return findings.value
  return findings.value.filter((f) => f.risk_level === activeFilter.value)
})

const obligations = computed<ExtendedObligation[]>(() => {
  return (review.value?.report?.obligations as ExtendedObligation[]) ?? []
})

const qualityData = computed<QualityData | null>(() => {
  if (review.value?.quality) return review.value.quality
  // Fallback: derive from report.quality_metrics
  const qm = review.value?.report?.quality_metrics
  if (qm) {
    return {
      completeness_score: qm.completeness_score,
      ai_involved: undefined,
      validations_passed: undefined,
      evidence_coverage: undefined,
      warnings: qm.issues,
    }
  }
  return null
})

const totalFindings = computed(() => findings.value.length)

const highRiskCount = computed(() =>
  findings.value.filter((f) => f.risk_level === 'high' || f.risk_level === 'critical').length,
)

const obligationsCount = computed(() => obligations.value.length)

const evidenceCoverage = computed(() => {
  return qualityData.value?.evidence_coverage ?? review.value?.report?.quality_metrics?.completeness_score ?? 0
})

const qualityWarnings = computed(() => {
  const raw = qualityData.value?.warnings ?? []
  return raw.map(translateWarning)
})

const knowledgeSources = computed(() => qualityData.value?.knowledge_sources ?? [])

const noteDialogTitle = computed(() =>
  pendingAction.value === 'approve' ? '批准审阅' : '拒绝审阅',
)

// ─── Methods ──────────────────────────────────────────────────────────────────

async function fetchReview() {
  loading.value = true
  notFound.value = false
  errorMsg.value = ''
  try {
    const data = await get<ExtendedReviewDetail>(`/reviews/${reviewId.value}`)
    review.value = data
  } catch (err: any) {
    if (err?.status_code === 404) {
      notFound.value = true
    } else {
      errorMsg.value = err?.detail || '获取审阅详情失败，请稍后重试'
    }
  } finally {
    loading.value = false
  }
}

function countByLevel(level: string): number {
  return findings.value.filter((f) => f.risk_level === level).length
}

function riskLevelLabel(level: string): string {
  const map: Record<string, string> = {
    critical: '严重',
    high: '高',
    medium: '中',
    low: '低',
    info: '信息',
  }
  return map[level] ?? level
}

function riskColor(level: string): { bg: string; text: string } {
  const map: Record<string, { bg: string; text: string }> = {
    critical: { bg: '#fdecea', text: '#d32f2f' },
    high: { bg: '#fff3e0', text: '#e65100' },
    medium: { bg: '#fffde7', text: '#f9a825' },
    low: { bg: '#e3f2fd', text: '#1565c0' },
    info: { bg: '#f5f5f5', text: '#757575' },
  }
  return map[level] ?? { bg: '#f5f5f5', text: '#757575' }
}

function sourceLabel(source?: string): string {
  const map: Record<string, string> = {
    rule: '规则',
    ai: 'AI',
    hybrid: '混合',
  }
  return map[source ?? ''] ?? '规则'
}

function translateWarning(w: string): string {
  const translations: Record<string, string> = {
    'low_confidence_findings': '存在低置信度的发现项',
    'missing_evidence': '部分发现缺少证据引用',
    'incomplete_clauses': '合同条款可能不完整',
    'ai_hallucination_risk': 'AI生成内容可能存在幻觉风险',
    'no_legal_basis': '部分发现缺少法律依据',
  }
  return translations[w] ?? w
}

function formatTime(iso?: string): string {
  if (!iso) return ''
  const d = new Date(iso)
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')} ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
}

// ─── Decision / Approval ──────────────────────────────────────────────────────

function openNoteDialog(action: 'approve' | 'reject') {
  pendingAction.value = action
  noteText.value = ''
  noteDialogVisible.value = true
}

async function confirmNoteDecision() {
  noteDialogVisible.value = false
  await submitDecision(pendingAction.value, noteText.value || undefined)
}

async function submitDecision(action: string, note?: string) {
  if (!review.value) return
  decisionLoading.value = true
  try {
    const payload: Record<string, unknown> = {
      action,
      expected_version: review.value.version,
    }
    if (note) payload.note = note

    const updated = await patch<ExtendedReviewDetail>(
      `/reviews/${reviewId.value}/decision`,
      payload,
    )
    review.value = updated
    message.success('操作成功')
  } catch (err: any) {
    if (err?.status_code === 409) {
      // Conflict: reload and retry once
      message.warning('数据已被他人修改，正在刷新后重试…')
      try {
        const fresh = await get<ExtendedReviewDetail>(`/reviews/${reviewId.value}`)
        review.value = fresh
        const retryPayload: Record<string, unknown> = {
          action,
          expected_version: fresh.version,
        }
        if (note) retryPayload.note = note
        const updated = await patch<ExtendedReviewDetail>(
          `/reviews/${reviewId.value}/decision`,
          retryPayload,
        )
        review.value = updated
        message.success('操作成功')
      } catch (retryErr: any) {
        message.error(retryErr?.detail || '操作失败，请重试')
      }
    } else {
      message.error(err?.detail || '操作失败，请重试')
    }
  } finally {
    decisionLoading.value = false
  }
}

// ─── Delete / Restore ─────────────────────────────────────────────────────────

async function handleToggleDelete() {
  if (!review.value) return
  try {
    if (review.value.is_deleted) {
      const updated = await patch<ExtendedReviewDetail>(`/reviews/${reviewId.value}`, { is_deleted: false })
      review.value = updated
      message.success('已恢复')
    } else {
      await del(`/reviews/${reviewId.value}`)
      review.value = { ...review.value, is_deleted: true }
      message.success('已删除')
    }
  } catch (err: any) {
    message.error(err?.detail || '操作失败')
  }
}

// ─── Feedback ─────────────────────────────────────────────────────────────────

async function submitFeedback(findingId: string, type: 'helpful' | 'needs_review') {
  try {
    await post(`/reviews/${reviewId.value}/feedback`, {
      finding_id: findingId,
      feedback: type,
    })
    feedbackState[findingId] = type
    message.success('感谢反馈')
  } catch (err: any) {
    message.error(err?.detail || '提交反馈失败')
  }
}

// ─── Lifecycle ────────────────────────────────────────────────────────────────

onMounted(() => {
  fetchReview()
})
</script>

<style scoped>
.review-detail {
  max-width: 1100px;
  margin: 0 auto;
  padding: 0 4px;
}

.back-btn {
  margin-bottom: 16px;
  font-size: 14px;
}

.detail-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
  flex-wrap: wrap;
}

.detail-title {
  font-size: 22px;
  font-weight: 700;
  margin: 0;
  color: var(--text-primary, #1a1a1a);
}

.header-badges {
  display: flex;
  gap: 8px;
  align-items: center;
}

.action-bar {
  margin-bottom: 20px;
}

.section-card {
  margin-bottom: 20px;
  border-radius: var(--radius-md, 10px);
}

.section-title {
  font-size: 15px;
  font-weight: 600;
}

/* Approval */
.approval-card {
  border-left: 3px solid var(--n-color, #18a058);
}

.approval-content {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 12px;
}

.approval-status {
  display: flex;
  align-items: center;
  gap: 8px;
}

.approval-label {
  font-size: 14px;
  color: var(--text-secondary, #666);
}

.approval-meta {
  font-size: 12px;
  color: var(--text-tertiary, #999);
}

/* Summary grid */
.summary-grid {
  margin-bottom: 20px;
}

.stat-card {
  text-align: center;
  border-radius: var(--radius-md, 10px);
}

.stat-danger {
  color: #d32f2f;
  font-weight: 700;
}

/* Findings */
.findings-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-top: 12px;
}

.finding-card {
  border-radius: var(--radius-md, 8px);
}

.finding-header {
  display: flex;
  align-items: center;
  gap: 8px;
}

.finding-title {
  font-size: 14px;
  font-weight: 600;
}

.finding-desc {
  margin: 0 0 12px 0;
  font-size: 14px;
  line-height: 1.7;
  color: var(--text-secondary, #555);
}

.finding-evidence {
  margin-bottom: 12px;
}

.evidence-quote {
  margin: 0 0 8px 0;
  font-size: 13px;
}

.evidence-source {
  display: block;
  margin-top: 4px;
  font-size: 12px;
}

.finding-recommendation {
  margin-bottom: 12px;
  font-size: 14px;
  line-height: 1.6;
}

.finding-feedback {
  border-top: 1px solid var(--n-border-color, #efeff5);
  padding-top: 8px;
}

/* Obligations */
.obligations-table {
  font-size: 13px;
}

.source-collapse {
  min-width: 120px;
}

/* Quality */
.quality-warnings {
  margin-top: 12px;
}

.quality-sources {
  margin-top: 12px;
}
</style>
