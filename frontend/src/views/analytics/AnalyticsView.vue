<template>
  <div class="analytics-page">
    <!-- Header -->
    <div class="page-header">
      <div class="header-left">
        <h1 class="page-title">数据分析</h1>
        <p class="page-subtitle">合同审阅风险与效率全景</p>
      </div>
      <n-button-group>
        <n-button
          v-for="opt in rangeOptions"
          :key="opt.value"
          :type="selectedRange === opt.value ? 'primary' : 'default'"
          size="small"
          @click="handleRangeChange(opt.value)"
        >
          {{ opt.label }}
        </n-button>
      </n-button-group>
    </div>

    <!-- Overview Cards -->
    <n-grid :cols="6" :x-gap="14" :y-gap="14" responsive="screen" item-responsive>
      <n-gi span="6 m:3 l:2 xl:1">
        <n-card class="metric-card" :bordered="false">
          <n-skeleton v-if="loadingOverview" text :repeat="2" />
          <n-statistic v-else label="审阅总数" :value="overview.total_reviews" />
        </n-card>
      </n-gi>
      <n-gi span="6 m:3 l:2 xl:1">
        <n-card class="metric-card" :bordered="false">
          <n-skeleton v-if="loadingOverview" text :repeat="2" />
          <n-statistic v-else label="本周新增" :value="overview.reviews_this_week" />
        </n-card>
      </n-gi>
      <n-gi span="6 m:3 l:2 xl:1">
        <n-card class="metric-card" :bordered="false">
          <n-skeleton v-if="loadingOverview" text :repeat="2" />
          <n-statistic v-else label="本月新增" :value="overview.reviews_this_month" />
        </n-card>
      </n-gi>
      <n-gi span="6 m:3 l:2 xl:1">
        <n-card class="metric-card" :bordered="false">
          <n-skeleton v-if="loadingOverview" text :repeat="2" />
          <n-statistic v-else label="平均耗时">
            <template #default>
              <span class="stat-value">{{ formatDuration(overview.avg_review_seconds) }}</span>
            </template>
          </n-statistic>
        </n-card>
      </n-gi>
      <n-gi span="6 m:3 l:2 xl:1">
        <n-card class="metric-card metric-card--danger" :bordered="false">
          <n-skeleton v-if="loadingOverview" text :repeat="2" />
          <n-statistic v-else label="开放风险" :value="overview.open_risks" />
        </n-card>
      </n-gi>
      <n-gi span="6 m:3 l:2 xl:1">
        <n-card class="metric-card metric-card--success" :bordered="false">
          <n-skeleton v-if="loadingOverview" text :repeat="2" />
          <n-statistic v-else label="完成率">
            <template #default>
              <span class="stat-value">{{ overview.completion_rate }}%</span>
            </template>
          </n-statistic>
        </n-card>
      </n-gi>
    </n-grid>

    <!-- Risk Trend Chart (full width) -->
    <n-card title="风险趋势" :bordered="false" class="chart-card">
      <n-skeleton v-if="loadingTrends" :height="320" />
      <template v-else>
        <n-empty v-if="riskTrends.length === 0" description="暂无风险趋势数据" class="empty-state" />
        <v-chart
          v-else
          :option="riskTrendOption"
          :theme="chartTheme"
          :autoresize="true"
          class="chart"
          style="height: 320px"
        />
      </template>
    </n-card>

    <!-- Efficiency Metrics -->
    <n-card title="审阅效率" :bordered="false" class="chart-card">
      <n-skeleton v-if="loadingEfficiency" text :repeat="3" />
      <template v-else>
        <n-grid :cols="3" :x-gap="16" responsive="screen" item-responsive>
          <n-gi span="3 m:1">
            <n-statistic label="平均审阅时长" class="efficiency-stat">
              <template #default>
                <span class="stat-value-lg">{{ formatDuration(efficiency.avg_review_seconds) }}</span>
              </template>
            </n-statistic>
          </n-gi>
          <n-gi span="3 m:1">
            <n-statistic label="完成率" class="efficiency-stat">
              <template #default>
                <span class="stat-value-lg">{{ efficiency.completion_rate }}%</span>
              </template>
            </n-statistic>
          </n-gi>
          <n-gi span="3 m:1">
            <n-statistic label="总审阅数" class="efficiency-stat">
              <template #default>
                <span class="stat-value-lg">{{ efficiency.total_reviews }}</span>
              </template>
              <template #suffix>
                <span class="stat-suffix">/ {{ efficiency.period_days }}天</span>
              </template>
            </n-statistic>
          </n-gi>
        </n-grid>
      </template>
    </n-card>

    <!-- Workload + Risk Categories side by side -->
    <n-grid :cols="2" :x-gap="16" :y-gap="16" responsive="screen" item-responsive>
      <n-gi span="2 l:1">
        <n-card title="工作负载分布" :bordered="false" class="chart-card">
          <n-skeleton v-if="loadingWorkload" :height="280" />
          <template v-else>
            <n-empty v-if="workloadData.length === 0" description="暂无工作负载数据" class="empty-state" />
            <v-chart
              v-else
              :option="workloadOption"
              :theme="chartTheme"
              :autoresize="true"
              class="chart"
              style="height: 280px"
            />
          </template>
        </n-card>
      </n-gi>
      <n-gi span="2 l:1">
        <n-card title="风险类别分布" :bordered="false" class="chart-card">
          <n-skeleton v-if="loadingCategories" :height="280" />
          <template v-else>
            <n-empty v-if="categoryData.length === 0" description="暂无风险类别数据" class="empty-state" />
            <v-chart
              v-else
              :option="categoryOption"
              :theme="chartTheme"
              :autoresize="true"
              class="chart"
              style="height: 280px"
            />
          </template>
        </n-card>
      </n-gi>
    </n-grid>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, watch } from 'vue'
import {
  NGrid,
  NGi,
  NCard,
  NStatistic,
  NSkeleton,
  NButton,
  NButtonGroup,
  NEmpty,
  useMessage,
} from 'naive-ui'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { LineChart, BarChart, PieChart } from 'echarts/charts'
import {
  GridComponent,
  TooltipComponent,
  LegendComponent,
  TitleComponent,
} from 'echarts/components'
import VChart from 'vue-echarts'
import { get } from '@/api/client'
import { useThemeStore } from '@/stores/theme'

// ─── Register ECharts modules ─────────────────────────────────────────────────

use([
  CanvasRenderer,
  LineChart,
  BarChart,
  PieChart,
  GridComponent,
  TooltipComponent,
  LegendComponent,
  TitleComponent,
])

// ─── Types ────────────────────────────────────────────────────────────────────

interface OverviewData {
  total_reviews: number
  avg_review_seconds: number
  open_risks: number
  completion_rate: number
  reviews_this_week: number
  reviews_this_month: number
}

interface RiskTrendPoint {
  date: string
  critical: number
  high: number
  medium: number
  low: number
  info: number
}

interface EfficiencyData {
  avg_review_seconds: number
  total_reviews: number
  completed_reviews: number
  completion_rate: number
  period_days: number
}

interface WorkloadEntry {
  assignee_name: string
  open_count: number
  completed_count: number
  overdue_count: number
}

interface RiskCategoryEntry {
  category: string
  count: number
  percentage: number
}

// ─── Store & Message ──────────────────────────────────────────────────────────

const themeStore = useThemeStore()
const message = useMessage()

// ─── State ────────────────────────────────────────────────────────────────────

const selectedRange = ref(30)
const rangeOptions = [
  { label: '近7天', value: 7 },
  { label: '近30天', value: 30 },
  { label: '近90天', value: 90 },
  { label: '近1年', value: 365 },
]

const loadingOverview = ref(true)
const loadingTrends = ref(true)
const loadingEfficiency = ref(true)
const loadingWorkload = ref(true)
const loadingCategories = ref(true)

const overview = reactive<OverviewData>({
  total_reviews: 0,
  avg_review_seconds: 0,
  open_risks: 0,
  completion_rate: 0,
  reviews_this_week: 0,
  reviews_this_month: 0,
})

const riskTrends = ref<RiskTrendPoint[]>([])
const efficiency = reactive<EfficiencyData>({
  avg_review_seconds: 0,
  total_reviews: 0,
  completed_reviews: 0,
  completion_rate: 0,
  period_days: 0,
})
const workloadData = ref<WorkloadEntry[]>([])
const categoryData = ref<RiskCategoryEntry[]>([])

// ─── Computed ─────────────────────────────────────────────────────────────────

const chartTheme = computed(() => (themeStore.isDark ? 'dark' : undefined))

const riskColors = {
  critical: '#e53935',
  high: '#fb8c00',
  medium: '#fdd835',
  low: '#1e88e5',
  info: '#9e9e9e',
}

const riskTrendOption = computed(() => {
  const dates = riskTrends.value.map((p) => p.date)
  return {
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'cross' },
    },
    legend: {
      data: ['严重', '高', '中', '低', '信息'],
      bottom: 0,
    },
    grid: {
      left: '3%',
      right: '4%',
      top: '8%',
      bottom: '14%',
      containLabel: true,
    },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: dates,
      axisLabel: {
        formatter: (val: string) => {
          const d = new Date(val)
          return `${d.getMonth() + 1}/${d.getDate()}`
        },
      },
    },
    yAxis: {
      type: 'value',
      minInterval: 1,
    },
    series: [
      {
        name: '严重',
        type: 'line',
        stack: 'risk',
        areaStyle: { opacity: 0.3 },
        emphasis: { focus: 'series' },
        data: riskTrends.value.map((p) => p.critical),
        itemStyle: { color: riskColors.critical },
        smooth: true,
      },
      {
        name: '高',
        type: 'line',
        stack: 'risk',
        areaStyle: { opacity: 0.3 },
        emphasis: { focus: 'series' },
        data: riskTrends.value.map((p) => p.high),
        itemStyle: { color: riskColors.high },
        smooth: true,
      },
      {
        name: '中',
        type: 'line',
        stack: 'risk',
        areaStyle: { opacity: 0.3 },
        emphasis: { focus: 'series' },
        data: riskTrends.value.map((p) => p.medium),
        itemStyle: { color: riskColors.medium },
        smooth: true,
      },
      {
        name: '低',
        type: 'line',
        stack: 'risk',
        areaStyle: { opacity: 0.3 },
        emphasis: { focus: 'series' },
        data: riskTrends.value.map((p) => p.low),
        itemStyle: { color: riskColors.low },
        smooth: true,
      },
      {
        name: '信息',
        type: 'line',
        stack: 'risk',
        areaStyle: { opacity: 0.3 },
        emphasis: { focus: 'series' },
        data: riskTrends.value.map((p) => p.info),
        itemStyle: { color: riskColors.info },
        smooth: true,
      },
    ],
  }
})

const workloadOption = computed(() => {
  const names = workloadData.value.map((w) => w.assignee_name)
  return {
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
    },
    legend: {
      data: ['待处理', '已完成', '逾期'],
      bottom: 0,
    },
    grid: {
      left: '3%',
      right: '6%',
      top: '6%',
      bottom: '14%',
      containLabel: true,
    },
    xAxis: {
      type: 'value',
      minInterval: 1,
    },
    yAxis: {
      type: 'category',
      data: names,
      axisLabel: {
        width: 80,
        overflow: 'truncate',
      },
    },
    series: [
      {
        name: '待处理',
        type: 'bar',
        stack: 'total',
        data: workloadData.value.map((w) => w.open_count),
        itemStyle: { color: '#1e88e5' },
        barMaxWidth: 24,
      },
      {
        name: '已完成',
        type: 'bar',
        stack: 'total',
        data: workloadData.value.map((w) => w.completed_count),
        itemStyle: { color: '#43a047' },
        barMaxWidth: 24,
      },
      {
        name: '逾期',
        type: 'bar',
        stack: 'total',
        data: workloadData.value.map((w) => w.overdue_count),
        itemStyle: { color: '#e53935' },
        barMaxWidth: 24,
      },
    ],
  }
})

const categoryOption = computed(() => {
  const palette = [
    '#e53935', '#fb8c00', '#fdd835', '#1e88e5', '#9e9e9e',
    '#8e24aa', '#00897b', '#5c6bc0', '#d81b60', '#6d4c41',
  ]
  return {
    tooltip: {
      trigger: 'item',
      formatter: '{b}: {c} ({d}%)',
    },
    legend: {
      orient: 'vertical',
      right: '4%',
      top: 'center',
      type: 'scroll',
    },
    color: palette,
    series: [
      {
        type: 'pie',
        radius: ['40%', '70%'],
        center: ['40%', '50%'],
        avoidLabelOverlap: true,
        itemStyle: {
          borderRadius: 6,
          borderColor: themeStore.isDark ? '#1e1e2e' : '#ffffff',
          borderWidth: 2,
        },
        label: {
          show: true,
          formatter: '{b}\n{d}%',
        },
        emphasis: {
          label: {
            show: true,
            fontSize: 14,
            fontWeight: 'bold',
          },
        },
        data: categoryData.value.map((c) => ({
          name: c.category,
          value: c.count,
        })),
      },
    ],
  }
})

// ─── Helpers ──────────────────────────────────────────────────────────────────

function formatDuration(seconds: number): string {
  if (!seconds || seconds <= 0) return '0秒'
  const mins = Math.floor(seconds / 60)
  const secs = Math.round(seconds % 60)
  if (mins === 0) return `${secs}秒`
  return `${mins}分${secs}秒`
}

// ─── Data Fetching ────────────────────────────────────────────────────────────

async function fetchOverview() {
  loadingOverview.value = true
  try {
    const data = await get<OverviewData>('/analytics/overview')
    overview.total_reviews = data.total_reviews ?? 0
    overview.avg_review_seconds = data.avg_review_seconds ?? 0
    overview.open_risks = data.open_risks ?? 0
    overview.completion_rate = data.completion_rate ?? 0
    overview.reviews_this_week = data.reviews_this_week ?? 0
    overview.reviews_this_month = data.reviews_this_month ?? 0
  } catch {
    message.error('获取概览数据失败')
  } finally {
    loadingOverview.value = false
  }
}

async function fetchRiskTrends() {
  loadingTrends.value = true
  try {
    const data = await get<RiskTrendPoint[]>('/analytics/risk-trends', {
      params: { days: selectedRange.value },
    })
    riskTrends.value = Array.isArray(data) ? data : []
  } catch {
    message.error('获取风险趋势失败')
    riskTrends.value = []
  } finally {
    loadingTrends.value = false
  }
}

async function fetchEfficiency() {
  loadingEfficiency.value = true
  try {
    const data = await get<EfficiencyData>('/analytics/efficiency', {
      params: { days: selectedRange.value },
    })
    efficiency.avg_review_seconds = data.avg_review_seconds ?? 0
    efficiency.total_reviews = data.total_reviews ?? 0
    efficiency.completed_reviews = data.completed_reviews ?? 0
    efficiency.completion_rate = data.completion_rate ?? 0
    efficiency.period_days = data.period_days ?? selectedRange.value
  } catch {
    message.error('获取效率数据失败')
  } finally {
    loadingEfficiency.value = false
  }
}

async function fetchWorkload() {
  loadingWorkload.value = true
  try {
    const data = await get<WorkloadEntry[]>('/analytics/workload')
    workloadData.value = Array.isArray(data) ? data : []
  } catch {
    message.error('获取工作负载失败')
    workloadData.value = []
  } finally {
    loadingWorkload.value = false
  }
}

async function fetchCategories() {
  loadingCategories.value = true
  try {
    const data = await get<RiskCategoryEntry[]>('/analytics/risk-categories')
    categoryData.value = Array.isArray(data) ? data : []
  } catch {
    message.error('获取风险类别失败')
    categoryData.value = []
  } finally {
    loadingCategories.value = false
  }
}

function fetchAll() {
  fetchOverview()
  fetchRiskTrends()
  fetchEfficiency()
  fetchWorkload()
  fetchCategories()
}

// ─── Event Handlers ───────────────────────────────────────────────────────────

function handleRangeChange(days: number) {
  selectedRange.value = days
  fetchRiskTrends()
  fetchEfficiency()
}

// ─── Lifecycle ────────────────────────────────────────────────────────────────

onMounted(() => {
  fetchAll()
})
</script>

<style scoped>
.analytics-page {
  max-width: 1200px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 12px;
}

.header-left {
  display: flex;
  flex-direction: column;
}

.page-title {
  font-size: 24px;
  font-weight: 700;
  margin: 0;
  color: var(--text-primary, #1a1a2e);
}

.page-subtitle {
  font-size: 14px;
  color: var(--text-secondary, #6b7280);
  margin: 4px 0 0 0;
}

.metric-card {
  border-radius: var(--radius-md, 10px);
  box-shadow: var(--card-shadow, 0 2px 12px rgba(0, 0, 0, 0.06));
  transition: transform 0.2s ease, box-shadow 0.2s ease;
  height: 100%;
}

.metric-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
}

.metric-card--danger :deep(.n-statistic-value) {
  color: #e53935;
}

.metric-card--success :deep(.n-statistic-value) {
  color: #43a047;
}

.stat-value {
  font-size: 24px;
  font-weight: 600;
}

.stat-value-lg {
  font-size: 28px;
  font-weight: 700;
  color: var(--text-primary, #1a1a2e);
}

.stat-suffix {
  font-size: 13px;
  color: var(--text-secondary, #6b7280);
  margin-left: 4px;
}

.chart-card {
  border-radius: var(--radius-md, 10px);
  box-shadow: var(--card-shadow, 0 2px 12px rgba(0, 0, 0, 0.06));
}

.chart {
  width: 100%;
}

.empty-state {
  padding: 60px 0;
}

.efficiency-stat {
  text-align: center;
  padding: 12px 0;
}
</style>
