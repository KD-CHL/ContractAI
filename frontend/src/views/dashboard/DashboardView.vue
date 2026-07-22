<template>
  <div class="dashboard-page">
    <div class="page-header">
      <h1 class="page-title">工作台</h1>
      <p class="page-subtitle">欢迎回来，{{ authStore.user?.display_name }}</p>
    </div>

    <!-- Metric Cards -->
    <n-grid :cols="4" :x-gap="16" :y-gap="16" responsive="screen" :collapsed-rows="1" item-responsive>
      <n-gi span="4 m:2 l:1">
        <n-card class="metric-card" :bordered="false">
          <n-skeleton v-if="loading" text :repeat="2" />
          <template v-else>
            <n-statistic label="审阅总数" :value="dashboardData.total_reviews">
              <template #prefix>
                <span class="metric-icon">📄</span>
              </template>
            </n-statistic>
          </template>
        </n-card>
      </n-gi>
      <n-gi span="4 m:2 l:1">
        <n-card class="metric-card metric-card--danger" :bordered="false">
          <n-skeleton v-if="loading" text :repeat="2" />
          <template v-else>
            <n-statistic label="高风险项" :value="dashboardData.high_risk_count">
              <template #prefix>
                <span class="metric-icon">🚨</span>
              </template>
            </n-statistic>
          </template>
        </n-card>
      </n-gi>
      <n-gi span="4 m:2 l:1">
        <n-card class="metric-card metric-card--warning" :bordered="false">
          <n-skeleton v-if="loading" text :repeat="2" />
          <template v-else>
            <n-statistic label="待处理工单" :value="opsData.open_items">
              <template #prefix>
                <span class="metric-icon">🔧</span>
              </template>
            </n-statistic>
          </template>
        </n-card>
      </n-gi>
      <n-gi span="4 m:2 l:1">
        <n-card class="metric-card metric-card--overdue" :bordered="false">
          <n-skeleton v-if="loading" text :repeat="2" />
          <template v-else>
            <n-statistic label="逾期项" :value="opsData.overdue_items">
              <template #prefix>
                <span class="metric-icon">⏰</span>
              </template>
            </n-statistic>
          </template>
        </n-card>
      </n-gi>
    </n-grid>

    <!-- Quick Actions -->
    <div class="quick-actions">
      <n-button type="primary" size="large" @click="router.push('/reviews/new')" class="action-btn">
        <template #icon><span>✨</span></template>
        新建审阅
      </n-button>
      <n-button size="large" @click="router.push('/work')" class="action-btn">
        <template #icon><span>🔧</span></template>
        查看处置中心
      </n-button>
    </div>

    <!-- Recent Reviews -->
    <n-card title="最近审阅" :bordered="false" class="recent-card">
      <template #header-extra>
        <n-button text type="primary" @click="router.push('/reviews')">
          查看全部
        </n-button>
      </template>

      <n-skeleton v-if="loading" :height="200" />

      <template v-else>
        <n-empty
          v-if="recentReviews.length === 0"
          description="暂无审阅记录，点击「新建审阅」开始"
          class="empty-state"
        >
          <template #extra>
            <n-button type="primary" size="small" @click="router.push('/reviews/new')">
              新建审阅
            </n-button>
          </template>
        </n-empty>

        <n-list v-else hoverable clickable>
          <n-list-item
            v-for="review in recentReviews"
            :key="review.id"
            @click="router.push(`/reviews/${review.id}`)"
          >
            <template #prefix>
              <n-tag :type="getRiskTagType(review.risk_level)" size="small" round>
                {{ getRiskLabel(review.risk_level) }}
              </n-tag>
            </template>
            <n-thing :title="review.name" :description="review.summary || '暂无摘要'" />
            <template #suffix>
              <div class="review-meta">
                <n-tag :type="getStatusTagType(review.status)" size="tiny" :bordered="false">
                  {{ getStatusLabel(review.status) }}
                </n-tag>
                <span class="review-time">{{ formatTime(review.created_at) }}</span>
              </div>
            </template>
          </n-list-item>
        </n-list>
      </template>
    </n-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import {
  NGrid,
  NGi,
  NCard,
  NStatistic,
  NSkeleton,
  NButton,
  NList,
  NListItem,
  NThing,
  NTag,
  NEmpty,
  useMessage,
} from 'naive-ui'
import { useAuthStore } from '../../stores/auth'
import api from '../../api/client'

interface ReviewItem {
  id: string
  name: string
  summary: string
  risk_level: 'high' | 'medium' | 'low' | 'none'
  status: 'pending' | 'complete' | 'failed'
  created_at: string
}

interface DashboardSummary {
  total_reviews: number
  high_risk_count: number
  recent_reviews: ReviewItem[]
}

interface OpsSummary {
  open_items: number
  overdue_items: number
}

const router = useRouter()
const message = useMessage()
const authStore = useAuthStore()

const loading = ref(true)

const dashboardData = reactive<DashboardSummary>({
  total_reviews: 0,
  high_risk_count: 0,
  recent_reviews: [],
})

const opsData = reactive<OpsSummary>({
  open_items: 0,
  overdue_items: 0,
})

const recentReviews = ref<ReviewItem[]>([])

onMounted(async () => {
  await fetchData()
})

async function fetchData() {
  loading.value = true
  try {
    const [dashRes, opsRes] = await Promise.allSettled([
      api.get('/dashboard/summary'),
      api.get('/operations/summary'),
    ])

    if (dashRes.status === 'fulfilled') {
      const data = dashRes.value.data
      dashboardData.total_reviews = data.total_reviews ?? 0
      dashboardData.high_risk_count = data.high_risk_count ?? 0
      dashboardData.recent_reviews = data.recent_reviews ?? []
      recentReviews.value = data.recent_reviews ?? []
    }

    if (opsRes.status === 'fulfilled') {
      const data = opsRes.value.data
      opsData.open_items = data.open_items ?? 0
      opsData.overdue_items = data.overdue_items ?? 0
    }
  } catch (err: any) {
    message.error('获取工作台数据失败')
  } finally {
    loading.value = false
  }
}

function getRiskTagType(level: string): 'error' | 'warning' | 'info' | 'success' {
  const map: Record<string, 'error' | 'warning' | 'info' | 'success'> = {
    high: 'error',
    medium: 'warning',
    low: 'info',
    none: 'success',
  }
  return map[level] || 'info'
}

function getRiskLabel(level: string): string {
  const map: Record<string, string> = {
    high: '高风险',
    medium: '中风险',
    low: '低风险',
    none: '无风险',
  }
  return map[level] || '未知'
}

function getStatusTagType(status: string): 'default' | 'info' | 'success' | 'error' {
  const map: Record<string, 'default' | 'info' | 'success' | 'error'> = {
    pending: 'info',
    complete: 'success',
    failed: 'error',
  }
  return map[status] || 'default'
}

function getStatusLabel(status: string): string {
  const map: Record<string, string> = {
    pending: '审阅中',
    complete: '已完成',
    failed: '审阅失败',
  }
  return map[status] || status
}

function formatTime(dateStr: string): string {
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
  return date.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' })
}
</script>

<style scoped>
.dashboard-page {
  max-width: 1200px;
  margin: 0 auto;
}

.page-header {
  margin-bottom: 24px;
}

.page-title {
  font-size: 24px;
  font-weight: 700;
  margin: 0 0 4px 0;
  color: var(--text-primary, #1a1a2e);
}

.page-subtitle {
  font-size: 14px;
  color: var(--text-secondary, #6b7280);
  margin: 0;
}

.metric-card {
  border-radius: var(--radius-md, 10px);
  box-shadow: var(--card-shadow, 0 2px 12px rgba(0, 0, 0, 0.06));
  transition: transform var(--transition-fast, 0.2s ease), box-shadow var(--transition-fast, 0.2s ease);
}

.metric-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
}

.metric-icon {
  font-size: 20px;
  margin-right: 4px;
}

.quick-actions {
  display: flex;
  gap: 12px;
  margin: 24px 0;
  flex-wrap: wrap;
}

.action-btn {
  border-radius: 8px;
  font-weight: 500;
}

.recent-card {
  border-radius: var(--radius-md, 10px);
  box-shadow: var(--card-shadow, 0 2px 12px rgba(0, 0, 0, 0.06));
}

.empty-state {
  padding: 40px 0;
}

.review-meta {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 4px;
}

.review-time {
  font-size: 12px;
  color: var(--text-secondary, #6b7280);
}
</style>
