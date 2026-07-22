<template>
  <n-layout has-sider class="app-layout">
    <!-- Desktop Sidebar -->
    <n-layout-sider
      v-if="!isMobile"
      bordered
      :collapsed="collapsed"
      collapse-mode="width"
      :collapsed-width="64"
      :width="240"
      show-trigger
      @collapse="collapsed = true"
      @expand="collapsed = false"
      class="app-sider"
    >
      <div class="sider-logo" @click="router.push('/dashboard')">
        <span class="logo-icon">📋</span>
        <transition name="fade">
          <span v-if="!collapsed" class="logo-text">ContractGuard</span>
        </transition>
      </div>
      <n-menu
        :collapsed="collapsed"
        :collapsed-width="64"
        :collapsed-icon-size="20"
        :options="menuOptions"
        :value="activeKey"
        @update:value="handleMenuSelect"
      />
      <div class="sider-bottom">
        <n-menu
          :collapsed="collapsed"
          :collapsed-width="64"
          :collapsed-icon-size="20"
          :options="bottomMenuOptions"
          :value="activeKey"
          @update:value="handleMenuSelect"
        />
      </div>
    </n-layout-sider>

    <!-- Mobile Drawer -->
    <n-drawer v-model:show="drawerVisible" placement="left" :width="260">
      <n-drawer-content :native-scrollbar="false">
        <div class="sider-logo drawer-logo">
          <span class="logo-icon">📋</span>
          <span class="logo-text">ContractGuard</span>
        </div>
        <n-menu
          :options="menuOptions"
          :value="activeKey"
          @update:value="handleMobileMenuSelect"
        />
        <n-divider />
        <n-menu
          :options="bottomMenuOptions"
          :value="activeKey"
          @update:value="handleMobileMenuSelect"
        />
      </n-drawer-content>
    </n-drawer>

    <!-- Main Content -->
    <n-layout class="main-layout">
      <n-layout-header bordered class="app-header">
        <div class="header-left">
          <n-button
            v-if="isMobile"
            quaternary
            circle
            size="small"
            @click="drawerVisible = true"
            class="mobile-menu-btn"
          >
            <span style="font-size: 18px">☰</span>
          </n-button>
          <n-breadcrumb>
            <n-breadcrumb-item @click="router.push('/dashboard')">
              首页
            </n-breadcrumb-item>
            <n-breadcrumb-item>{{ currentPageTitle }}</n-breadcrumb-item>
          </n-breadcrumb>
        </div>
        <div class="header-right">
          <ThemeToggle />
          <n-dropdown
            trigger="click"
            :options="userDropdownOptions"
            @select="handleUserAction"
          >
            <n-button quaternary class="user-btn">
              <n-avatar
                round
                :size="32"
                :style="{ backgroundColor: '#667eea', fontSize: '14px' }"
              >
                {{ avatarText }}
              </n-avatar>
              <span v-if="!isMobile" class="user-name">{{ authStore.user?.display_name }}</span>
            </n-button>
          </n-dropdown>
        </div>
      </n-layout-header>

      <n-layout-content class="app-content" :native-scrollbar="false">
        <router-view v-slot="{ Component }">
          <transition name="page-fade" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </n-layout-content>
    </n-layout>
  </n-layout>
</template>

<script setup lang="ts">
import { ref, computed, h, onMounted, onUnmounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import {
  NLayout,
  NLayoutSider,
  NLayoutHeader,
  NLayoutContent,
  NMenu,
  NButton,
  NBreadcrumb,
  NBreadcrumbItem,
  NDropdown,
  NAvatar,
  NDrawer,
  NDrawerContent,
  NDivider,
  useMessage,
} from 'naive-ui'
import type { MenuOption, DropdownOption } from 'naive-ui'
import { useAuthStore } from '../../stores/auth'
import { usePermission } from '../../composables/usePermission'
import ThemeToggle from './ThemeToggle.vue'

const router = useRouter()
const route = useRoute()
const message = useMessage()
const authStore = useAuthStore()
const { isAdmin } = usePermission()

const collapsed = ref(false)
const drawerVisible = ref(false)
const isMobile = ref(false)

function checkMobile() {
  isMobile.value = window.innerWidth < 768
}

onMounted(() => {
  checkMobile()
  window.addEventListener('resize', checkMobile)
})

onUnmounted(() => {
  window.removeEventListener('resize', checkMobile)
})

const currentPageTitle = computed(() => {
  return (route.meta.title as string) || '工作台'
})

const avatarText = computed(() => {
  const name = authStore.user?.display_name
  return name ? name.charAt(0).toUpperCase() : 'U'
})

const activeKey = computed(() => {
  const path = route.path
  if (path.startsWith('/reviews/new')) return 'new'
  if (path.startsWith('/reviews')) return 'reviews'
  if (path.startsWith('/dashboard')) return 'dashboard'
  if (path.startsWith('/work')) return 'work'
  if (path.startsWith('/analytics')) return 'analytics'
  if (path.startsWith('/compare')) return 'compare'
  if (path.startsWith('/templates')) return 'templates'
  if (path.startsWith('/clauses')) return 'clauses'
  if (path.startsWith('/account')) return 'account'
  if (path.startsWith('/admin')) return 'admin'
  return 'dashboard'
})

function renderIcon(icon: string) {
  return () => h('span', { style: 'font-size: 16px' }, icon)
}

const menuOptions = computed<MenuOption[]>(() => [
  {
    label: '工作台',
    key: 'dashboard',
    icon: renderIcon('📊'),
  },
  {
    label: '审阅记录',
    key: 'reviews',
    icon: renderIcon('📄'),
  },
  {
    label: '新建审阅',
    key: 'new',
    icon: renderIcon('✨'),
  },
  {
    label: '处置中心',
    key: 'work',
    icon: renderIcon('🔧'),
  },
  {
    label: '数据分析',
    key: 'analytics',
    icon: renderIcon('📈'),
  },
  {
    label: '合同对比',
    key: 'compare',
    icon: renderIcon('⚖️'),
  },
  {
    label: '模板库',
    key: 'templates',
    icon: renderIcon('📁'),
  },
  {
    label: '条款库',
    key: 'clauses',
    icon: renderIcon('📚'),
  },
])

const bottomMenuOptions = computed<MenuOption[]>(() => {
  const items: MenuOption[] = [
    {
      label: '账户设置',
      key: 'account',
      icon: renderIcon('👤'),
    },
  ]
  if (isAdmin.value) {
    items.push({
      label: '管理后台',
      key: 'admin',
      icon: renderIcon('⚙️'),
    })
  }
  return items
})

const userDropdownOptions: DropdownOption[] = [
  {
    label: '个人资料',
    key: 'profile',
    icon: () => h('span', '👤'),
  },
  {
    type: 'divider',
    key: 'd1',
  },
  {
    label: '退出登录',
    key: 'logout',
    icon: () => h('span', '🚪'),
  },
]

function handleMenuSelect(key: string) {
  navigateTo(key)
}

function handleMobileMenuSelect(key: string) {
  drawerVisible.value = false
  navigateTo(key)
}

function navigateTo(key: string) {
  const routeMap: Record<string, string> = {
    dashboard: '/dashboard',
    reviews: '/reviews',
    new: '/reviews/new',
    work: '/work',
    analytics: '/analytics',
    compare: '/compare',
    templates: '/templates',
    clauses: '/clauses',
    account: '/account',
    admin: '/admin',
  }
  const path = routeMap[key]
  if (path) {
    router.push(path)
  }
}

function handleUserAction(key: string) {
  if (key === 'profile') {
    router.push('/account')
  } else if (key === 'logout') {
    authStore.logout()
    message.success('已退出登录')
    router.push('/login')
  }
}
</script>

<style scoped>
.app-layout {
  height: 100vh;
  overflow: hidden;
}

.app-sider {
  display: flex;
  flex-direction: column;
  background: var(--sidebar-bg);
}

.sider-logo {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 16px 20px;
  cursor: pointer;
  user-select: none;
  height: 60px;
  box-sizing: border-box;
  border-bottom: 1px solid var(--border-color);
}

.logo-icon {
  font-size: 24px;
  flex-shrink: 0;
}

.logo-text {
  font-size: 16px;
  font-weight: 700;
  background: var(--brand-gradient);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  white-space: nowrap;
}

.drawer-logo {
  border-bottom: none;
  margin-bottom: 8px;
}

.sider-bottom {
  margin-top: auto;
  border-top: 1px solid var(--border-color);
  padding-top: 4px;
}

.main-layout {
  display: flex;
  flex-direction: column;
}

.app-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  height: var(--header-height);
  background: var(--header-bg);
  backdrop-filter: blur(12px);
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.mobile-menu-btn {
  margin-right: 4px;
}

.user-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 8px;
}

.user-name {
  font-size: 14px;
  color: var(--text-primary);
  max-width: 120px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.app-content {
  padding: 24px;
  background: var(--app-bg);
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity var(--transition-fast);
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

.page-fade-enter-active,
.page-fade-leave-active {
  transition: opacity 0.25s ease, transform 0.25s ease;
}

.page-fade-enter-from {
  opacity: 0;
  transform: translateY(8px);
}

.page-fade-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}
</style>
