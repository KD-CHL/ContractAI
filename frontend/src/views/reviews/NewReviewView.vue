<template>
  <div class="page-container">
    <!-- Page Header -->
    <div class="page-header">
      <n-button text @click="router.push('/reviews')" class="back-btn">
        ← 返回审阅列表
      </n-button>
      <h1 class="page-title">新建审阅</h1>
    </div>

    <!-- Submitting State -->
    <transition name="fade" mode="out-in">
      <n-card v-if="submitting" :bordered="false" class="content-card submitting-card">
        <div class="submitting-panel">
          <div class="submitting-icon">🔍</div>
          <h3 class="submitting-title">正在审阅中...</h3>
          <n-progress
            type="line"
            :percentage="100"
            :indicator-placement="'inside'"
            :height="8"
            :border-radius="4"
            :fill-border-radius="4"
            status="info"
            :show-indicator="false"
            class="submitting-progress"
          />
          <p class="submitting-tip">AI 正在分析合同条款，请稍候（最长约3分钟）</p>
          <n-button size="small" quaternary type="error" @click="handleCancel">
            取消审阅
          </n-button>
        </div>
      </n-card>

      <!-- Form State -->
      <div v-else class="form-wrapper">
        <!-- Error Alert -->
        <n-alert
          v-if="errorMessage"
          type="error"
          closable
          class="error-alert"
          @close="errorMessage = ''"
        >
          {{ errorMessage }}
        </n-alert>

        <n-card :bordered="false" class="content-card">
          <!-- Tabs -->
          <n-tabs v-model:value="activeTab" type="line" animated>
            <!-- Tab 1: Paste Text -->
            <n-tab-pane name="text" tab="粘贴文本">
              <div class="tab-content">
                <n-input
                  v-model:value="contractText"
                  type="textarea"
                  placeholder="请粘贴合同文本..."
                  :rows="16"
                  :autosize="{ minRows: 12, maxRows: 24 }"
                  show-count
                  :maxlength="100000"
                  class="contract-textarea"
                />
                <div class="tab-actions">
                  <n-button size="small" quaternary type="info" @click="fillSampleContract">
                    📝 使用示例合同
                  </n-button>
                  <span v-if="contractText.length > 0" class="char-count">
                    {{ contractText.length }} 字
                  </span>
                </div>
              </div>
            </n-tab-pane>

            <!-- Tab 2: Upload File -->
            <n-tab-pane name="upload" tab="上传文件">
              <div class="tab-content">
                <n-upload
                  v-model:file-list="fileList"
                  :max="1"
                  :accept="'.pdf,.docx,.txt,.md,.png,.jpg'"
                  :default-upload="false"
                  :on-before-upload="handleBeforeUpload"
                  directory-dnd
                  class="upload-zone"
                >
                  <n-upload-dragger class="upload-dragger">
                    <div class="upload-icon">📄</div>
                    <n-text class="upload-title">点击或拖拽文件到此区域上传</n-text>
                    <n-p depth="3" class="upload-hint">
                      支持 PDF、Word、TXT、Markdown、PNG、JPG 格式，单个文件不超过 20MB
                    </n-p>
                  </n-upload-dragger>
                </n-upload>
              </div>
            </n-tab-pane>
          </n-tabs>

          <!-- Advanced Section -->
          <n-collapse class="advanced-section">
            <n-collapse-item title="高级选项" name="advanced">
              <n-form label-placement="left" label-width="100">
                <n-form-item label="合同编号">
                  <n-input
                    v-model:value="contractId"
                    placeholder="可选，关联已有合同编号（如 HT-2024-001）"
                    clearable
                  />
                </n-form-item>
              </n-form>
            </n-collapse-item>
          </n-collapse>

          <!-- Submit Button -->
          <n-button
            type="primary"
            block
            size="large"
            :disabled="!canSubmit"
            class="submit-btn"
            @click="handleSubmit"
          >
            开始审阅
          </n-button>
        </n-card>
      </div>
    </transition>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import {
  NCard,
  NButton,
  NInput,
  NTabs,
  NTabPane,
  NUpload,
  NUploadDragger,
  NCollapse,
  NCollapseItem,
  NForm,
  NFormItem,
  NAlert,
  NProgress,
  NText,
  NP,
  useMessage,
} from 'naive-ui'
import type { UploadFileInfo } from 'naive-ui'
import { post } from '@/api/client'
import type { ReviewSummary, ReviewTextRequest } from '@/types/api'

// ─── Router & Message ────────────────────────────────────────────────────────

const router = useRouter()
const message = useMessage()

// ─── State ───────────────────────────────────────────────────────────────────

const activeTab = ref<'text' | 'upload'>('text')
const contractText = ref('')
const contractId = ref('')
const fileList = ref<UploadFileInfo[]>([])
const submitting = ref(false)
const errorMessage = ref('')

let abortController: AbortController | null = null

// ─── Computed ────────────────────────────────────────────────────────────────

const canSubmit = computed(() => {
  if (activeTab.value === 'text') {
    return contractText.value.trim().length >= 10
  }
  return fileList.value.length > 0
})

// ─── Sample Contract ─────────────────────────────────────────────────────────

const SAMPLE_CONTRACT = `技术服务合同

甲方（委托方）：深圳市星辰科技有限公司
乙方（服务方）：杭州云智信息技术有限公司

鉴于甲方需要技术开发服务，乙方具备相应技术能力，双方经协商一致，订立本合同。

第一条 服务内容
乙方为甲方提供企业管理系统的定制开发服务，包括但不限于需求分析、系统设计、编码开发、测试部署及上线支持。

第二条 服务期限
本合同自签订之日起生效，服务期限为一年。合同到期前三十日内，如任何一方未以书面形式提出终止，则本合同自动续期一年，续期次数不限。

第三条 服务费用及支付
甲方应在合同签订后五个工作日内支付全部服务费用人民币伍拾万元整（¥500,000.00）。如甲方逾期支付，每逾期一日，应按合同总金额的5%向乙方支付违约金。

第四条 知识产权
乙方在履行本合同过程中产生的所有知识产权（包括但不限于源代码、文档、设计方案）均归乙方所有。甲方仅享有非排他性的使用权，且不得进行二次开发或修改。

第五条 保密条款
双方应对合同内容及履行过程中知悉的对方商业秘密承担保密义务，保密期限为合同终止后十年。任何一方违反保密义务的，应向对方支付合同总金额三倍的违约金。

第六条 违约责任
因甲方原因导致合同无法继续履行的，甲方已支付的费用不予退还，且甲方应另行赔偿乙方全部预期利润损失（按合同总金额的200%计算）。因乙方原因导致合同无法继续履行的，乙方仅退还已收取费用的10%作为补偿，不承担其他任何责任。

第七条 不可抗力
因不可抗力导致合同无法履行的，乙方不承担任何责任，且已收取的费用不予退还。

第八条 争议解决
本合同发生争议时，由乙方所在地人民法院管辖。甲方放弃对管辖法院提出异议的权利。

第九条 其他
本合同未尽事宜，由乙方单方面决定并通知甲方执行。本合同一式两份，双方各执一份，具有同等法律效力。

甲方（盖章）：                    乙方（盖章）：
代表人签字：                      代表人签字：
日期：2024年  月  日              日期：2024年  月  日`

function fillSampleContract() {
  contractText.value = SAMPLE_CONTRACT
  activeTab.value = 'text'
  message.success('已填入示例合同')
}

// ─── Upload Validation ───────────────────────────────────────────────────────

function handleBeforeUpload({ file }: { file: UploadFileInfo }) {
  const MAX_SIZE = 20 * 1024 * 1024 // 20MB
  const allowedExts = ['.pdf', '.docx', '.txt', '.md', '.png', '.jpg']

  const fileName = file.name || ''
  const ext = fileName.substring(fileName.lastIndexOf('.')).toLowerCase()

  if (!allowedExts.includes(ext)) {
    message.error(`不支持的文件格式：${ext}，请上传 ${allowedExts.join('、')} 格式的文件`)
    return false
  }

  if (file.file && file.file.size > MAX_SIZE) {
    message.error('文件大小不能超过 20MB')
    return false
  }

  return true
}

// ─── Submit ──────────────────────────────────────────────────────────────────

async function handleSubmit() {
  if (!canSubmit.value) return

  errorMessage.value = ''
  submitting.value = true
  abortController = new AbortController()

  const timeoutId = setTimeout(() => {
    abortController?.abort()
  }, 180000) // 180s timeout

  try {
    let result: ReviewSummary

    if (activeTab.value === 'text') {
      // Text submission
      const payload: ReviewTextRequest = {
        text: contractText.value.trim(),
      }
      if (contractId.value.trim()) {
        payload.contract_id = contractId.value.trim()
      }

      result = await post<ReviewSummary>('/reviews/text', payload, {
        signal: abortController.signal,
      })
    } else {
      // File upload (multipart)
      const formData = new FormData()
      const file = fileList.value[0]?.file
      if (!file) {
        throw new Error('请选择要上传的文件')
      }
      formData.append('file', file)
      if (contractId.value.trim()) {
        formData.append('contract_id', contractId.value.trim())
      }

      result = await post<ReviewSummary>('/reviews', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
        signal: abortController.signal,
      })
    }

    message.success('审阅已提交，正在分析中...')
    router.push(`/reviews/${result.id}`)
  } catch (err: unknown) {
    if (abortController?.signal.aborted) {
      errorMessage.value = '审阅请求超时（已超过3分钟），请稍后重试或联系管理员。'
    } else {
      const apiErr = err as { detail?: string; message?: string }
      errorMessage.value = apiErr.detail || apiErr.message || '提交失败，请稍后重试'
    }
    submitting.value = false
  } finally {
    clearTimeout(timeoutId)
    abortController = null
  }
}

function handleCancel() {
  abortController?.abort()
  submitting.value = false
  message.info('已取消审阅')
}
</script>

<style scoped>
.page-container {
  max-width: 900px;
  margin: 0 auto;
  padding: 0 4px;
}

.page-header {
  margin-bottom: 20px;
}

.back-btn {
  margin-bottom: 12px;
  font-size: 13px;
  color: var(--text-secondary, #6b7280);
}

.page-title {
  font-size: 22px;
  font-weight: 700;
  margin: 0;
  color: var(--text-primary, #1a1a2e);
}

.content-card {
  border-radius: var(--radius-md, 10px);
  box-shadow: var(--card-shadow, 0 2px 12px rgba(0, 0, 0, 0.06));
}

/* Error Alert */
.error-alert {
  margin-bottom: 16px;
  border-radius: 8px;
}

/* Tab Content */
.tab-content {
  padding-top: 16px;
}

.contract-textarea {
  font-size: 14px;
  line-height: 1.7;
}

.contract-textarea :deep(textarea) {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Hiragino Sans GB',
    'Microsoft YaHei', sans-serif;
}

.tab-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 10px;
}

.char-count {
  font-size: 12px;
  color: var(--text-secondary, #999);
}

/* Upload Zone */
.upload-zone {
  width: 100%;
}

.upload-dragger {
  padding: 40px 20px;
  text-align: center;
  border: 2px dashed var(--border-color, #e0e0e6);
  border-radius: 10px;
  transition: border-color 0.3s ease, background-color 0.3s ease;
  cursor: pointer;
}

.upload-dragger:hover {
  border-color: var(--primary-color, #2080f0);
  background-color: rgba(32, 128, 240, 0.03);
}

.upload-icon {
  font-size: 48px;
  margin-bottom: 12px;
}

.upload-title {
  display: block;
  font-size: 15px;
  font-weight: 500;
  margin-bottom: 8px;
}

.upload-hint {
  font-size: 13px;
  color: var(--text-secondary, #999);
  margin: 0;
}

/* Advanced Section */
.advanced-section {
  margin-top: 20px;
  border-top: 1px solid var(--border-color, #efeff5);
  padding-top: 8px;
}

/* Submit Button */
.submit-btn {
  margin-top: 24px;
  height: 46px;
  font-size: 16px;
  font-weight: 600;
  border-radius: 8px;
}

/* Submitting Panel */
.submitting-card {
  min-height: 360px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.submitting-panel {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 40px;
  text-align: center;
}

.submitting-icon {
  font-size: 56px;
  margin-bottom: 20px;
  animation: pulse 2s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% {
    transform: scale(1);
    opacity: 1;
  }
  50% {
    transform: scale(1.1);
    opacity: 0.8;
  }
}

.submitting-title {
  font-size: 20px;
  font-weight: 600;
  color: var(--text-primary, #1a1a2e);
  margin: 0 0 24px 0;
}

.submitting-progress {
  width: 100%;
  max-width: 360px;
  margin-bottom: 16px;
}

.submitting-tip {
  font-size: 14px;
  color: var(--text-secondary, #6b7280);
  margin: 0 0 24px 0;
  line-height: 1.6;
}

/* Transitions */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease, transform 0.3s ease;
}

.fade-enter-from {
  opacity: 0;
  transform: translateY(8px);
}

.fade-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}

/* Responsive */
@media (max-width: 768px) {
  .page-container {
    padding: 0;
  }

  .submitting-panel {
    padding: 40px 20px;
  }

  .upload-dragger {
    padding: 30px 16px;
  }
}
</style>
