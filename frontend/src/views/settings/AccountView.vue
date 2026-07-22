<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">账户设置</h1>
    </div>

    <n-space vertical :size="16">
      <!-- 个人信息 -->
      <n-card title="个人信息" :bordered="false" class="content-card">
        <n-descriptions :column="1" label-placement="left" bordered>
          <n-descriptions-item label="显示名称">
            {{ authStore.user?.display_name || '-' }}
          </n-descriptions-item>
          <n-descriptions-item label="邮箱">
            {{ authStore.user?.email || '-' }}
          </n-descriptions-item>
          <n-descriptions-item label="角色">
            <n-tag :type="roleTagType" size="small">{{ roleLabel }}</n-tag>
          </n-descriptions-item>
          <n-descriptions-item label="所属组织">
            {{ authStore.user?.org_name || '-' }}
          </n-descriptions-item>
          <n-descriptions-item label="注册时间">
            {{ authStore.user?.created_at ? formatDateTime(authStore.user.created_at) : '-' }}
          </n-descriptions-item>
        </n-descriptions>
      </n-card>

      <!-- 修改密码 -->
      <n-card title="修改密码" :bordered="false" class="content-card">
        <n-form
          ref="passwordFormRef"
          :model="passwordForm"
          :rules="passwordRules"
          label-placement="left"
          label-width="100"
          style="max-width: 460px"
        >
          <n-form-item label="当前密码" path="current_password">
            <n-input
              v-model:value="passwordForm.current_password"
              type="password"
              show-password-on="click"
              placeholder="请输入当前密码"
            />
          </n-form-item>
          <n-form-item label="新密码" path="new_password">
            <n-input
              v-model:value="passwordForm.new_password"
              type="password"
              show-password-on="click"
              placeholder="至少12位，包含大小写字母、数字、特殊字符中的3类"
              @input="onPasswordInput"
            />
          </n-form-item>

          <!-- Password Strength Indicator -->
          <n-form-item label="密码强度" :show-feedback="false">
            <div style="width: 100%">
              <n-progress
                type="line"
                :percentage="strengthPercent"
                :color="strengthColor"
                :rail-color="'rgba(128,128,128,0.12)'"
                :show-indicator="false"
                :height="8"
                :border-radius="4"
              />
              <n-text :style="{ color: strengthColor, fontSize: '12px' }">
                {{ strengthLabel }}
              </n-text>
            </div>
          </n-form-item>

          <n-form-item label="确认密码" path="confirm_password">
            <n-input
              v-model:value="passwordForm.confirm_password"
              type="password"
              show-password-on="click"
              placeholder="请再次输入新密码"
            />
          </n-form-item>
          <n-form-item>
            <n-button
              type="primary"
              :loading="changingPassword"
              @click="handleChangePassword"
            >
              确认修改
            </n-button>
          </n-form-item>
        </n-form>
        <n-alert type="info" :bordered="false" style="max-width: 460px">
          修改密码成功后，系统将要求您重新登录以确保安全。
        </n-alert>
      </n-card>

      <!-- 会话信息 -->
      <n-card title="会话信息" :bordered="false" class="content-card">
        <n-space vertical :size="12">
          <n-text depth="3">
            退出登录后，您需要重新输入邮箱和密码才能访问系统。
          </n-text>
          <n-popconfirm
            positive-text="确认退出"
            negative-text="取消"
            @positive-click="handleLogout"
          >
            <template #trigger>
              <n-button type="error" secondary :loading="loggingOut">
                退出登录
              </n-button>
            </template>
            确定要退出当前登录会话吗？
          </n-popconfirm>
        </n-space>
      </n-card>
    </n-space>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed } from 'vue'
import { useRouter } from 'vue-router'
import {
  NCard,
  NSpace,
  NDescriptions,
  NDescriptionsItem,
  NTag,
  NForm,
  NFormItem,
  NInput,
  NButton,
  NProgress,
  NText,
  NAlert,
  NPopconfirm,
  useMessage,
  type FormInst,
  type FormRules,
} from 'naive-ui'
import { useAuthStore } from '@/stores/auth'

const message = useMessage()
const router = useRouter()
const authStore = useAuthStore()

// ─── Role Display ────────────────────────────────────────────────────────────

const roleLabel = computed(() => {
  const map: Record<string, string> = { owner: '所有者', admin: '管理员', member: '成员' }
  return map[authStore.user?.role || ''] || authStore.user?.role || '-'
})

const roleTagType = computed<'default' | 'info' | 'success' | 'warning' | 'error'>(() => {
  const map: Record<string, 'default' | 'info' | 'success' | 'warning' | 'error'> = {
    owner: 'error',
    admin: 'warning',
    member: 'info',
  }
  return map[authStore.user?.role || ''] || 'default'
})

// ─── Password Change ─────────────────────────────────────────────────────────

const passwordFormRef = ref<FormInst | null>(null)
const changingPassword = ref(false)

const passwordForm = reactive({
  current_password: '',
  new_password: '',
  confirm_password: '',
})

/**
 * Password policy: >=12 chars, at least 3 of 4 character classes
 * (uppercase, lowercase, digits, special characters)
 */
function validatePasswordPolicy(_rule: unknown, value: string): boolean | Error {
  if (!value) return new Error('请输入新密码')
  if (value.length < 12) return new Error('密码长度不能少于12位')
  let classes = 0
  if (/[a-z]/.test(value)) classes++
  if (/[A-Z]/.test(value)) classes++
  if (/[0-9]/.test(value)) classes++
  if (/[^a-zA-Z0-9]/.test(value)) classes++
  if (classes < 3) return new Error('密码需包含大写字母、小写字母、数字、特殊字符中的至少3类')
  return true
}

function validateConfirm(_rule: unknown, value: string): boolean | Error {
  if (!value) return new Error('请再次输入新密码')
  if (value !== passwordForm.new_password) return new Error('两次输入的密码不一致')
  return true
}

const passwordRules: FormRules = {
  current_password: [{ required: true, message: '请输入当前密码', trigger: 'blur' }],
  new_password: [{ required: true, validator: validatePasswordPolicy, trigger: ['input', 'blur'] }],
  confirm_password: [{ required: true, validator: validateConfirm, trigger: ['input', 'blur'] }],
}

// ─── Password Strength ───────────────────────────────────────────────────────

const strengthScore = ref(0)

function onPasswordInput() {
  const pwd = passwordForm.new_password
  let score = 0
  if (pwd.length >= 12) score += 25
  if (pwd.length >= 16) score += 10
  if (/[a-z]/.test(pwd)) score += 15
  if (/[A-Z]/.test(pwd)) score += 15
  if (/[0-9]/.test(pwd)) score += 15
  if (/[^a-zA-Z0-9]/.test(pwd)) score += 20
  strengthScore.value = Math.min(score, 100)
}

const strengthPercent = computed(() => strengthScore.value)

const strengthColor = computed(() => {
  const s = strengthScore.value
  if (s === 0) return 'rgba(128,128,128,0.3)'
  if (s < 40) return '#d03050'
  if (s < 70) return '#f0a020'
  return '#18a058'
})

const strengthLabel = computed(() => {
  const s = strengthScore.value
  if (s === 0) return ''
  if (s < 40) return '弱'
  if (s < 70) return '中等'
  return '强'
})

// ─── Actions ─────────────────────────────────────────────────────────────────

async function handleChangePassword() {
  try {
    await passwordFormRef.value?.validate()
  } catch {
    return
  }

  changingPassword.value = true
  try {
    await authStore.changePassword({
      current_password: passwordForm.current_password,
      new_password: passwordForm.new_password,
    })
    message.success('密码修改成功，请重新登录')
    // Force re-login
    setTimeout(async () => {
      await authStore.logout()
      router.push('/login')
    }, 1500)
  } catch (err: unknown) {
    const apiErr = err as { detail?: string }
    message.error(apiErr.detail || '密码修改失败，请检查当前密码是否正确')
  } finally {
    changingPassword.value = false
  }
}

const loggingOut = ref(false)

async function handleLogout() {
  loggingOut.value = true
  try {
    await authStore.logout()
    router.push('/login')
  } finally {
    loggingOut.value = false
  }
}

// ─── Helpers ─────────────────────────────────────────────────────────────────

function formatDateTime(dateStr: string): string {
  const d = new Date(dateStr)
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}
</script>

<style scoped>
.page-container {
  max-width: 800px;
  margin: 0 auto;
}

.page-header {
  margin-bottom: 20px;
}

.page-title {
  font-size: 22px;
  font-weight: 700;
  margin: 0;
  color: var(--text-primary);
}

.content-card {
  border-radius: var(--radius-md, 10px);
  box-shadow: var(--card-shadow);
}
</style>
