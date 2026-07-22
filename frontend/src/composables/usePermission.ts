import { computed } from 'vue'
import { useAuthStore } from '../stores/auth'

export function usePermission() {
  const authStore = useAuthStore()

  const role = computed(() => authStore.role ?? '')

  const isOwner = computed(() => role.value === 'owner')
  const isAdmin = computed(() => role.value === 'admin' || role.value === 'owner')

  const canManageMembers = computed(() => isAdmin.value)
  const canApprove = computed(() => isAdmin.value || role.value === 'member')
  const canEditWorkItem = computed(() => isAdmin.value || role.value === 'member')
  const canDeleteReview = computed(() => isAdmin.value)

  function hasRole(...roles: string[]): boolean {
    return roles.includes(role.value)
  }

  return {
    role,
    isOwner,
    isAdmin,
    canManageMembers,
    canApprove,
    canEditWorkItem,
    canDeleteReview,
    hasRole,
  }
}
