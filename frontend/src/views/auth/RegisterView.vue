<template>
  <div class="auth-page">
    <!-- Left Brand Panel -->
    <div class="brand-panel">
      <div class="brand-content">
        <div class="brand-logo">
          <span class="brand-icon">📋</span>
          <h1 class="brand-name">ContractGuard</h1>
        </div>
        <p class="brand-tagline">AI 驱动的合同风险审阅平台</p>
        <div class="feature-list">
          <div class="feature-item">
            <span class="feature-icon">🔍</span>
            <div>
              <h3>智能风险识别</h3>
              <p>AI 自动识别合同中的潜在风险条款</p>
            </div>
          </div>
          <div class="feature-item">
            <span class="feature-icon">📐</span>
            <div>
              <h3>多维度分析</h3>
              <p>从法律、商业、合规多角度评估合同</p>
            </div>
          </div>
          <div class="feature-item">
            <span class="feature-icon">👥</span>
            <div>
              <h3>团队协作</h3>
              <p>支持多人协同审阅与工单处置</p>
            </div>
          </div>
          <div class="feature-item">
            <span class="feature-icon">📊</span>
            <div>
              <h3>数据洞察</h3>
              <p>可视化分析审阅数据与风险趋势</p>
            </div>
          </div>
        </div>
      </div>
      <div class="brand-footer">
        <p>&copy; 2026 ContractGuard. All rights reserved.</p>
      </div>
    </div>

    <!-- Right Form Panel -->
    <div class="form-panel">
      <div class="form-container">
        <div class="form-header">
          <h2>创建账户</h2>
          <p>开始使用 ContractGuard 合同风险审阅平台</p>
        </div>

        <n-alert v-if="errorMsg" type="error" closable @close="errorMsg = ''" class="error-alert">
          {{ errorMsg }}
        </n-alert>

        <n-form
          ref="formRef"
          :model="form"
          :rules="rules"
          label-placement="top"
          size="large"
        >
          <n-form-item label="组织名称" path="org_name">
            <n-input
              v-model:value="form.org_name"
              placeholder="请输入组织/公司名称"
            />
          </n-form-item>

          <n-form-item label="显示名称" path="display_name">
            <n-input
              v-model:value="form.display_name"
              placeholder="请输入您的姓名或昵称"
            />
          </n-form-item>

          <n-form-item label="邮箱地址" path="email">
            <n-input
              v-model:value="form.email"
              placeholder="请输入邮箱地址"
              type="text"
            />
          </n-form-item>

          <n-form-item label="密码" path="password">
            <n-input
              v-model:value="form.password"
              placeholder="至少 12 位，包含多种字符类型"
              type="password"
              show-password-on="click"
            />
          </n-form-item>

          <!-- Password Strength Indicator -->
          <div v-if="form.password" class="password-strength">
            <div class="strength-bar">
              <div
                class="strength-fill"
                :style="{ width: `${passwordStrength.percent}%` }"
                :class="passwordStrength.level"
              />
            </div>
            <span class="strength-text" :class="passwordStrength.level">
              {{ passwordStrength.label }}
            </span>
          </div>

          <n-form-item label="确认密码" path="confirm_password">
            <n-input
              v-model:value="form.confirm_password"
              placeholder="请再次输入密码"
              type="password"
              show-password-on="click"
              @keyup.enter="handleRegister"
            />
          </n-form-item>

          <n-button
            type="primary"
            block
            size="large"
            :loading="loading"
            @click="handleRegister"
            class="submit-btn"
          >
            注 册
          </n-button>
        </n-form>

        <div class="form-footer">
          <span>已有账户？</span>
          <router-link to="/login" class="link">返回登录</router-link>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed } from 'vue'
import { useRouter } from 'vue-router'
import {
  NForm,
  NFormItem,
  NInput,
  NButton,
  NAlert,
  useMessage,
} from 'naive-ui'
import type { FormInst, FormRules } from 'naive-ui'
import { useAuthStore } from '../../stores/auth'

const router = useRouter()
const message = useMessage()
const authStore = useAuthStore()

const loading = ref(false)
const errorMsg = ref('')
const formRef = ref<FormInst | null>(null)

const form = reactive({
  org_name: '',
  display_name: '',
  email: '',
  password: '',
  confirm_password: '',
})

const passwordStrength = computed(() => {
  const pwd = form.password
  if (!pwd) return { percent: 0, level: '', label: '' }

  let score = 0
  if (pwd.length >= 12) score++
  if (pwd.length >= 16) score++
  if (/[a-z]/.test(pwd)) score++
  if (/[A-Z]/.test(pwd)) score++
  if (/[0-9]/.test(pwd)) score++
  if (/[^a-zA-Z0-9]/.test(pwd)) score++

  if (score <= 2) return { percent: 25, level: 'weak', label: '弱' }
  if (score <= 3) return { percent: 50, level: 'fair', label: '一般' }
  if (score <= 4) return { percent: 75, level: 'good', label: '良好' }
  return { percent: 100, level: 'strong', label: '强' }
})

const rules: FormRules = {
  org_name: [
    { required: true, message: '请输入组织名称', trigger: 'blur' },
    { min: 2, max: 100, message: '组织名称长度为 2-100 个字符', trigger: 'blur' },
  ],
  display_name: [
    { required: true, message: '请输入显示名称', trigger: 'blur' },
    { min: 2, max: 50, message: '显示名称长度为 2-50 个字符', trigger: 'blur' },
  ],
  email: [
    { required: true, message: '请输入邮箱地址', trigger: 'blur' },
    { type: 'email', message: '请输入有效的邮箱地址', trigger: 'blur' },
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 12, message: '密码长度不能少于 12 位', trigger: 'blur' },
    {
      validator(_rule: unknown, value: string) {
        if (!value) return true
        let classes = 0
        if (/[a-z]/.test(value)) classes++
        if (/[A-Z]/.test(value)) classes++
        if (/[0-9]/.test(value)) classes++
        if (/[^a-zA-Z0-9]/.test(value)) classes++
        if (classes < 3) {
          return new Error('密码需包含大写字母、小写字母、数字、特殊字符中的至少 3 类')
        }
        return true
      },
      trigger: 'blur',
    },
  ],
  confirm_password: [
    { required: true, message: '请再次输入密码', trigger: 'blur' },
    {
      validator(_rule: unknown, value: string) {
        if (value !== form.password) {
          return new Error('两次输入的密码不一致')
        }
        return true
      },
      trigger: 'blur',
    },
  ],
}

async function handleRegister() {
  try {
    await formRef.value?.validate()
  } catch {
    return
  }

  loading.value = true
  errorMsg.value = ''
  try {
    await authStore.register({
      org_name: form.org_name,
      display_name: form.display_name,
      email: form.email,
      password: form.password,
    })
    message.success('注册成功，已自动登录')
    router.push('/dashboard')
  } catch (err: any) {
    errorMsg.value =
      err.response?.data?.detail || err.response?.data?.message || '注册失败，请稍后重试'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.auth-page {
  display: flex;
  min-height: 100vh;
  background: var(--app-bg, #f5f7fa);
}

.brand-panel {
  display: none;
  width: 45%;
  max-width: 600px;
  background: var(--brand-gradient, linear-gradient(135deg, #667eea 0%, #764ba2 100%));
  color: #fff;
  flex-direction: column;
  justify-content: space-between;
  padding: 60px 48px;
  position: relative;
  overflow: hidden;
}

.brand-panel::before {
  content: '';
  position: absolute;
  top: -50%;
  right: -50%;
  width: 100%;
  height: 100%;
  background: radial-gradient(circle, rgba(255, 255, 255, 0.08) 0%, transparent 70%);
  animation: float 8s ease-in-out infinite;
}

@keyframes float {
  0%, 100% { transform: translate(0, 0); }
  50% { transform: translate(-20px, 20px); }
}

@media (min-width: 960px) {
  .brand-panel {
    display: flex;
  }
}

.brand-content {
  position: relative;
  z-index: 1;
}

.brand-logo {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}

.brand-icon {
  font-size: 36px;
}

.brand-name {
  font-size: 28px;
  font-weight: 800;
  margin: 0;
  letter-spacing: -0.5px;
}

.brand-tagline {
  font-size: 16px;
  opacity: 0.9;
  margin: 0 0 48px 0;
}

.feature-list {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.feature-item {
  display: flex;
  align-items: flex-start;
  gap: 14px;
  animation: slideUp 0.5s ease forwards;
  opacity: 0;
}

.feature-item:nth-child(1) { animation-delay: 0.1s; }
.feature-item:nth-child(2) { animation-delay: 0.2s; }
.feature-item:nth-child(3) { animation-delay: 0.3s; }
.feature-item:nth-child(4) { animation-delay: 0.4s; }

@keyframes slideUp {
  from {
    opacity: 0;
    transform: translateY(16px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.feature-icon {
  font-size: 24px;
  flex-shrink: 0;
  margin-top: 2px;
}

.feature-item h3 {
  margin: 0 0 4px 0;
  font-size: 15px;
  font-weight: 600;
}

.feature-item p {
  margin: 0;
  font-size: 13px;
  opacity: 0.8;
}

.brand-footer {
  position: relative;
  z-index: 1;
  font-size: 12px;
  opacity: 0.6;
}

.brand-footer p {
  margin: 0;
}

.form-panel {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40px 24px;
}

.form-container {
  width: 100%;
  max-width: 420px;
  background: var(--sidebar-bg, #ffffff);
  border-radius: var(--radius-lg, 16px);
  padding: 40px 36px;
  box-shadow: var(--card-shadow, 0 2px 12px rgba(0, 0, 0, 0.06));
  border: 1px solid var(--border-color, #e8e8e8);
}

.form-container :deep(.n-input) {
  font-size: 15px;
  --n-text-color: var(--text-primary, #1a1a2e);
  --n-placeholder-color: var(--text-secondary, #9ca3af);
  --n-border: 1px solid var(--border-color, #d9d9d9);
  --n-border-hover: 1px solid var(--brand-primary, #667eea);
  --n-border-focus: 1px solid var(--brand-primary, #667eea);
  --n-color: var(--sidebar-bg, #fff);
  --n-color-focus: var(--sidebar-bg, #fff);
  --n-caret-color: var(--text-primary, #1a1a2e);
}

.form-container :deep(.n-input .n-input__input-el) {
  font-size: 15px;
  color: var(--text-primary, #1a1a2e);
  caret-color: var(--brand-primary, #667eea);
}

.form-container :deep(.n-input .n-input__placeholder) {
  font-size: 14px;
  color: var(--text-secondary, #9ca3af);
}

.form-container :deep(.n-form-item .n-form-item-label) {
  font-size: 14px;
  font-weight: 500;
  color: var(--text-primary, #1a1a2e);
}

.form-header {
  margin-bottom: 28px;
}

.form-header h2 {
  font-size: 26px;
  font-weight: 700;
  margin: 0 0 8px 0;
  color: var(--text-primary, #1a1a2e);
}

.form-header p {
  font-size: 14px;
  color: var(--text-secondary, #6b7280);
  margin: 0;
}

.error-alert {
  margin-bottom: 20px;
}

.password-strength {
  display: flex;
  align-items: center;
  gap: 10px;
  margin: -8px 0 16px 0;
}

.strength-bar {
  flex: 1;
  height: 4px;
  background: rgba(128, 128, 128, 0.2);
  border-radius: 2px;
  overflow: hidden;
}

.strength-fill {
  height: 100%;
  border-radius: 2px;
  transition: width 0.3s ease, background-color 0.3s ease;
}

.strength-fill.weak { background-color: #e53e3e; }
.strength-fill.fair { background-color: #dd6b20; }
.strength-fill.good { background-color: #38a169; }
.strength-fill.strong { background-color: #2f855a; }

.strength-text {
  font-size: 12px;
  min-width: 32px;
}

.strength-text.weak { color: #e53e3e; }
.strength-text.fair { color: #dd6b20; }
.strength-text.good { color: #38a169; }
.strength-text.strong { color: #2f855a; }

.submit-btn {
  margin-top: 8px;
  font-weight: 600;
  height: 44px;
  border-radius: 8px;
}

.form-footer {
  text-align: center;
  margin-top: 24px;
  font-size: 14px;
  color: var(--text-secondary, #6b7280);
}

.link {
  color: var(--brand-primary, #667eea);
  text-decoration: none;
  font-weight: 500;
  margin-left: 4px;
}

.link:hover {
  text-decoration: underline;
}
</style>
