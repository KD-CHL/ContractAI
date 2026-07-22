import { defineStore } from 'pinia'
import { useDark, useToggle } from '@vueuse/core'
import { computed } from 'vue'

export const useThemeStore = defineStore('theme', () => {
  // ─── State ───────────────────────────────────────────────────────────────────
  // useDark persists to localStorage by default (key: 'vueuse-color-scheme')
  // and reactively applies the 'dark' class to <html>.

  const isDark = useDark({
    selector: 'html',
    attribute: 'class',
    valueDark: 'dark',
    valueLight: '',
  })

  const toggleDark = useToggle(isDark)

  // ─── Getters ─────────────────────────────────────────────────────────────────

  const theme = computed(() => (isDark.value ? 'dark' : 'light'))

  // ─── Actions ─────────────────────────────────────────────────────────────────

  function toggle(): void {
    toggleDark()
  }

  function setDark(value: boolean): void {
    isDark.value = value
  }

  return {
    // state
    isDark,
    // getters
    theme,
    // actions
    toggle,
    setDark,
  }
})
