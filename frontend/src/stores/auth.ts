import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { ChangePasswordRequest, LoginRequest, RegisterRequest, User } from '@/types/api'
import * as authApi from '@/api/auth'
import { clearTokens, setTokens } from '@/api/client'

const DEMO_MODE = import.meta.env.VITE_DEMO_MODE === 'true'

const DEMO_USER: User = {
  id: 'demo-user',
  email: 'demo@contractguard.app',
  display_name: 'Demo 用户',
  role: 'owner',
  org_id: 'demo-org',
  org_name: 'Demo 组织',
}

export const useAuthStore = defineStore('auth', () => {
  // ─── State ───────────────────────────────────────────────────────────────────

  const user = ref<User | null>(DEMO_MODE ? DEMO_USER : null)
  const isAuthenticated = ref(DEMO_MODE)
  const isBootstrap = ref(false)
  const loading = ref(false)

  // ─── Getters ─────────────────────────────────────────────────────────────────

  const role = computed(() => user.value?.role ?? null)
  const isOwner = computed(() => user.value?.role === 'owner')
  const isAdmin = computed(() => user.value?.role === 'admin' || user.value?.role === 'owner')
  const canManage = computed(() => isAdmin.value)

  // ─── Actions ─────────────────────────────────────────────────────────────────

  async function checkStatus(): Promise<void> {
    loading.value = true
    try {
      const status = await authApi.getAuthStatus()
      isBootstrap.value = status.bootstrap_required
      isAuthenticated.value = status.authenticated
      user.value = status.user ?? null
    } catch {
      isAuthenticated.value = false
      user.value = null
    } finally {
      loading.value = false
    }
  }

  async function login(data: LoginRequest): Promise<void> {
    loading.value = true
    try {
      const res = await authApi.login(data)
      setTokens(res.access_token, res.refresh_token)
      user.value = res.user
      isAuthenticated.value = true
      isBootstrap.value = false
    } finally {
      loading.value = false
    }
  }

  async function register(data: RegisterRequest): Promise<void> {
    loading.value = true
    try {
      const res = await authApi.register(data)
      setTokens(res.access_token, res.refresh_token)
      user.value = res.user
      isAuthenticated.value = true
      isBootstrap.value = false
    } finally {
      loading.value = false
    }
  }

  async function logout(): Promise<void> {
    try {
      await authApi.logout()
    } catch {
      // Proceed with local cleanup even if server call fails
    } finally {
      clearTokens()
      user.value = null
      isAuthenticated.value = false
    }
  }

  async function refresh(): Promise<void> {
    const me = await authApi.getMe()
    user.value = me
    isAuthenticated.value = true
  }

  async function changePassword(data: ChangePasswordRequest): Promise<void> {
    await authApi.changePassword(data)
  }

  return {
    // state
    user,
    isAuthenticated,
    isBootstrap,
    loading,
    // getters
    role,
    isOwner,
    isAdmin,
    canManage,
    // actions
    checkStatus,
    login,
    register,
    logout,
    refresh,
    changePassword,
  }
})
