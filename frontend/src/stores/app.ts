import { defineStore } from 'pinia'
import { ref } from 'vue'

// ─── Toast types ───────────────────────────────────────────────────────────────

export type ToastType = 'success' | 'error' | 'warning' | 'info'

export interface Toast {
  id: string
  type: ToastType
  message: string
  duration?: number
}

let toastId = 0

export const useAppStore = defineStore('app', () => {
  // ─── State ───────────────────────────────────────────────────────────────────

  const sidebarCollapsed = ref(false)
  const toasts = ref<Toast[]>([])

  // ─── Actions ─────────────────────────────────────────────────────────────────

  function toggleSidebar(): void {
    sidebarCollapsed.value = !sidebarCollapsed.value
  }

  function setSidebarCollapsed(value: boolean): void {
    sidebarCollapsed.value = value
  }

  function showToast(type: ToastType, message: string, duration: number = 4000): string {
    const id = `toast-${++toastId}`
    const toast: Toast = { id, type, message, duration }
    toasts.value.push(toast)

    if (duration > 0) {
      setTimeout(() => {
        dismissToast(id)
      }, duration)
    }

    return id
  }

  function dismissToast(id: string): void {
    const index = toasts.value.findIndex((t) => t.id === id)
    if (index !== -1) {
      toasts.value.splice(index, 1)
    }
  }

  function clearToasts(): void {
    toasts.value = []
  }

  return {
    // state
    sidebarCollapsed,
    toasts,
    // actions
    toggleSidebar,
    setSidebarCollapsed,
    showToast,
    dismissToast,
    clearToasts,
  }
})
