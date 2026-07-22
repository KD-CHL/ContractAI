<template>
  <n-tooltip trigger="hover">
    <template #trigger>
      <n-button quaternary circle size="small" @click="themeStore.toggle()">
        <span class="theme-icon">{{ themeStore.isDark ? '☀️' : '🌙' }}</span>
      </n-button>
    </template>
    {{ themeStore.isDark ? '切换到浅色模式' : '切换到深色模式' }}
  </n-tooltip>
</template>

<script setup lang="ts">
import { NButton, NTooltip } from 'naive-ui'
import { useThemeStore } from '../../stores/theme'

const themeStore = useThemeStore()
</script>

<style scoped>
.theme-icon {
  font-size: 16px;
  line-height: 1;
}
</style>
