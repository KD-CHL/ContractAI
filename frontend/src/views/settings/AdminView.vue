<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">管理后台</h1>
    </div>

    <n-card :bordered="false" class="content-card">
      <n-tabs type="line" animated>
        <!-- ─── 成员管理 ─────────────────────────────────────────────────── -->
        <n-tab-pane name="members" tab="成员管理">
          <div class="tab-toolbar">
            <n-button type="primary" size="small" @click="openCreateModal">
              添加成员
            </n-button>
          </div>

          <n-data-table
            :columns="memberColumns"
            :data="members"
            :loading="membersLoading"
            :row-key="(row: User) => row.id"
            striped
          />
        </n-tab-pane>

        <!-- ─── 审计日志 ─────────────────────────────────────────────────── -->
        <n-tab-pane name="audit" tab="审计日志">
          <n-data-table
            :columns="auditColumns"
            :data="auditLogs"
            :loading="auditLoading"
            :row-key="(row: AuditLog) => row.id"
            striped
            :max-height="520"
            virtual-scroll
          />
        </n-tab-pane>
      </n-tabs>
    </n-card>

    <!-- ─── 添加成员 Modal ───────────────────────────────────────────────── -->
    <n-modal
      v-model:show="createModalVisible"
      preset="card"
      title="添加成员"
      style="width: 460px"
      :mask-closable="false"
    >
      <n-form
        ref="createFormRef"
        :model="createForm"
        :rules="createRules"
        label-placement="left"
        label-width="80"
      >
        <n-form-item label="姓名" path="display_name">
          <n-input v-model:value="createForm.display_name" placeholder="请输入成员姓名" />
        </n-form-item>
        <n-form-item label="邮箱" path="email">
          <n-input v-model:value="createForm.email" placeholder="请输入邮箱地址" />
        </n-form-item>
        <n-form-item label="密码" path="password">
          <n-input
            v-model:value="createForm.password"
            type="password"
            show-password-on="click"
            placeholder="至少12位，含3类字符"
          />
        </n-form-item>
        <n-form-item label="角色" path="role">
          <n-select
            v-model:value="createForm.role"
            :options="roleOptions"
            placeholder="请选择角色"
          />
        </n-form-item>
      </n-form>
      <template #footer>
        <n-space justify="end">
          <n-button @click="createModalVisible = false">取消</n-button>
          <n-button type="primary" :loading="creating" @click="handleCreate">
            确认添加
          </n-button>
        </n-space>
      </template>
    </n-modal>

    <!-- ─── 编辑角色 Modal ───────────────────────────────────────────────── -->
    <n-modal
      v-model:show="editModalVisible"
      preset="card"
      title="编辑成员角色"
      style="width: 400px"
      :mask-closable="false"
    >
      <n-form label-placement="left" label-width="80">
        <n-form-item label="成员">
          <n-input :value="editingMember?.display_name" disabled />
        </n-form-item>
        <n-form-item label="角色">
          <n-select
            v-model:value="editRole"
            :options="roleOptions"
            placeholder="请选择角色"
          />
        </n-form-item>
      </n-form>
      <template #footer>
        <n-space justify="end">
          <n-button @click="editModalVisible = false">取消</n-button>
          <n-button type="primary" :loading="updatingMember" @click="handleEditRole">
            保存
          </n-button>
        </n-space>
      </template>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, h } from 'vue'
import {
  NCard,
  NTabs,
  NTabPane,
  NDataTable,
  NButton,
  NTag,
  NSpace,
  NModal,
  NForm,
  NFormItem,
  NInput,
  NSelect,
  NPopconfirm,
  NText,
  useMessage,
  type DataTableColumns,
  type FormInst,
  type FormRules,
} from 'naive-ui'
import { get, post, patch } from '@/api/client'
import type { User, MemberCreate, MemberUpdate, AuditLog, PaginatedResponse } from '@/types/api'

const message = useMessage()

// ─── Members ─────────────────────────────────────────────────────────────────

const members = ref<User[]>([])
const membersLoading = ref(false)

const roleOptions = [
  { label: '管理员', value: 'admin' },
  { label: '成员', value: 'member' },
]

const memberColumns: DataTableColumns<User> = [
  {
    title: '姓名',
    key: 'display_name',
    width: 140,
    ellipsis: { tooltip: true },
  },
  {
    title: '邮箱',
    key: 'email',
    width: 220,
    ellipsis: { tooltip: true },
  },
  {
    title: '角色',
    key: 'role',
    width: 100,
    render(row) {
      const typeMap: Record<string, 'error' | 'warning' | 'info'> = {
        owner: 'error',
        admin: 'warning',
        member: 'info',
      }
      const labelMap: Record<string, string> = {
        owner: '所有者',
        admin: '管理员',
        member: '成员',
      }
      return h(NTag, { size: 'small', type: typeMap[row.role] || 'info' }, { default: () => labelMap[row.role] || row.role })
    },
  },
  {
    title: '状态',
    key: 'status',
    width: 90,
    render(row) {
      const isActive = row.status !== 'disabled'
      return h(
        NTag,
        { size: 'small', type: isActive ? 'success' : 'default', bordered: false },
        { default: () => (isActive ? '正常' : '已禁用') },
      )
    },
  },
  {
    title: '操作',
    key: 'actions',
    width: 180,
    render(row) {
      // Owner row is protected
      if (row.role === 'owner') {
        return h(NText, { depth: 3, style: 'font-size: 12px' }, { default: () => '—' })
      }

      const buttons: ReturnType<typeof h>[] = []

      // Edit role
      buttons.push(
        h(
          NButton,
          { size: 'tiny', quaternary: true, type: 'primary', onClick: () => openEditModal(row) },
          { default: () => '编辑' },
        ),
      )

      // Disable / Enable
      const isActive = row.status !== 'disabled'
      if (isActive) {
        buttons.push(
          h(
            NPopconfirm,
            {
              positiveText: '确认禁用',
              negativeText: '取消',
              onPositiveClick: () => handleToggleStatus(row, 'disabled'),
            },
            {
              trigger: () =>
                h(
                  NButton,
                  { size: 'tiny', quaternary: true, type: 'error' },
                  { default: () => '禁用' },
                ),
              default: () => `确定要禁用成员「${row.display_name}」吗？`,
            },
          ),
        )
      } else {
        buttons.push(
          h(
            NButton,
            { size: 'tiny', quaternary: true, type: 'success', onClick: () => handleToggleStatus(row, 'active') },
            { default: () => '启用' },
          ),
        )
      }

      return h(NSpace, { size: 4 }, { default: () => buttons })
    },
  },
]

async function fetchMembers() {
  membersLoading.value = true
  try {
    const data = await get<PaginatedResponse<User>>('/users', { params: { page_size: 200 } })
    members.value = data.items
  } catch {
    message.error('获取成员列表失败')
  } finally {
    membersLoading.value = false
  }
}

// ─── Create Member ───────────────────────────────────────────────────────────

const createModalVisible = ref(false)
const creating = ref(false)
const createFormRef = ref<FormInst | null>(null)

const createForm = reactive<MemberCreate>({
  display_name: '',
  email: '',
  password: '',
  role: 'member',
})

function validateCreatePassword(_rule: unknown, value: string): boolean | Error {
  if (!value) return new Error('请输入密码')
  if (value.length < 12) return new Error('密码长度不能少于12位')
  let classes = 0
  if (/[a-z]/.test(value)) classes++
  if (/[A-Z]/.test(value)) classes++
  if (/[0-9]/.test(value)) classes++
  if (/[^a-zA-Z0-9]/.test(value)) classes++
  if (classes < 3) return new Error('需包含大写字母、小写字母、数字、特殊字符中的至少3类')
  return true
}

const createRules: FormRules = {
  display_name: [{ required: true, message: '请输入成员姓名', trigger: 'blur' }],
  email: [
    { required: true, message: '请输入邮箱', trigger: 'blur' },
    { type: 'email', message: '请输入有效的邮箱地址', trigger: 'blur' },
  ],
  password: [{ required: true, validator: validateCreatePassword, trigger: ['input', 'blur'] }],
  role: [{ required: true, message: '请选择角色', trigger: 'change' }],
}

function openCreateModal() {
  createForm.display_name = ''
  createForm.email = ''
  createForm.password = ''
  createForm.role = 'member'
  createModalVisible.value = true
}

async function handleCreate() {
  try {
    await createFormRef.value?.validate()
  } catch {
    return
  }

  creating.value = true
  try {
    await post<User>('/users', { ...createForm })
    message.success('成员添加成功')
    createModalVisible.value = false
    fetchMembers()
  } catch (err: unknown) {
    const apiErr = err as { detail?: string }
    message.error(apiErr.detail || '添加成员失败')
  } finally {
    creating.value = false
  }
}

// ─── Edit Role ───────────────────────────────────────────────────────────────

const editModalVisible = ref(false)
const updatingMember = ref(false)
const editingMember = ref<User | null>(null)
const editRole = ref<'admin' | 'member'>('member')

function openEditModal(member: User) {
  editingMember.value = member
  editRole.value = member.role === 'admin' ? 'admin' : 'member'
  editModalVisible.value = true
}

async function handleEditRole() {
  if (!editingMember.value) return
  updatingMember.value = true
  try {
    const payload: MemberUpdate = { role: editRole.value }
    await patch<User>(`/users/${editingMember.value.id}`, payload)
    message.success('角色更新成功')
    editModalVisible.value = false
    fetchMembers()
  } catch (err: unknown) {
    const apiErr = err as { detail?: string }
    message.error(apiErr.detail || '更新角色失败')
  } finally {
    updatingMember.value = false
  }
}

// ─── Toggle Status ───────────────────────────────────────────────────────────

async function handleToggleStatus(member: User, status: 'active' | 'disabled') {
  try {
    const payload: MemberUpdate = { status }
    await patch<User>(`/users/${member.id}`, payload)
    message.success(status === 'disabled' ? '已禁用该成员' : '已启用该成员')
    fetchMembers()
  } catch (err: unknown) {
    const apiErr = err as { detail?: string }
    message.error(apiErr.detail || '操作失败')
  }
}

// ─── Audit Logs ──────────────────────────────────────────────────────────────

const auditLogs = ref<AuditLog[]>([])
const auditLoading = ref(false)

const auditColumns: DataTableColumns<AuditLog> = [
  {
    title: '时间',
    key: 'created_at',
    width: 170,
    render(row) {
      return formatDateTime(row.created_at)
    },
  },
  {
    title: '操作者',
    key: 'actor_name',
    width: 120,
    ellipsis: { tooltip: true },
    render(row) {
      return row.actor_name || '系统'
    },
  },
  {
    title: '动作',
    key: 'action',
    width: 180,
    ellipsis: { tooltip: true },
    render(row) {
      const label = row.resource_type ? `${row.action} (${row.resource_type})` : row.action
      return label
    },
  },
  {
    title: '结果',
    key: 'result',
    width: 80,
    render(row) {
      const isSuccess = row.result !== 'failure'
      return h(
        NTag,
        { size: 'small', type: isSuccess ? 'success' : 'error', bordered: false },
        { default: () => (isSuccess ? '成功' : '失败') },
      )
    },
  },
  {
    title: '详情',
    key: 'detail',
    ellipsis: { tooltip: true },
    render(row) {
      return row.detail || '-'
    },
  },
]

async function fetchAuditLogs() {
  auditLoading.value = true
  try {
    const data = await get<PaginatedResponse<AuditLog>>('/audit-logs', {
      params: { page_size: 50 },
    })
    auditLogs.value = data.items
  } catch {
    message.error('获取审计日志失败')
  } finally {
    auditLoading.value = false
  }
}

// ─── Helpers ─────────────────────────────────────────────────────────────────

function formatDateTime(dateStr: string): string {
  const d = new Date(dateStr)
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
}

// ─── Init ────────────────────────────────────────────────────────────────────

onMounted(() => {
  fetchMembers()
  fetchAuditLogs()
})
</script>

<style scoped>
.page-container {
  max-width: 1200px;
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

.tab-toolbar {
  display: flex;
  justify-content: flex-end;
  margin-bottom: 12px;
}
</style>
