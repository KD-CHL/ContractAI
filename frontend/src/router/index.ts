import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const routes: RouteRecordRaw[] = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('../views/auth/LoginView.vue'),
    meta: { public: true, title: '登录' },
  },
  {
    path: '/register',
    name: 'Register',
    component: () => import('../views/auth/RegisterView.vue'),
    meta: { public: true, title: '注册' },
  },
  {
    path: '/',
    component: () => import('../components/layout/AppLayout.vue'),
    children: [
      {
        path: '',
        redirect: '/dashboard',
      },
      {
        path: 'dashboard',
        name: 'Dashboard',
        component: () => import('../views/dashboard/DashboardView.vue'),
        meta: { title: '工作台' },
      },
      {
        path: 'reviews',
        name: 'Reviews',
        component: () => import('../views/reviews/ReviewsView.vue'),
        meta: { title: '审阅记录' },
      },
      {
        path: 'reviews/new',
        name: 'NewReview',
        component: () => import('../views/reviews/NewReviewView.vue'),
        meta: { title: '新建审阅' },
      },
      {
        path: 'reviews/:id',
        name: 'ReviewDetail',
        component: () => import('../views/reviews/ReviewDetailView.vue'),
        meta: { title: '审阅详情' },
      },
      {
        path: 'work',
        name: 'WorkCenter',
        component: () => import('../views/operations/WorkCenterView.vue'),
        meta: { title: '处置中心' },
      },
      {
        path: 'analytics',
        name: 'Analytics',
        component: () => import('../views/analytics/AnalyticsView.vue'),
        meta: { title: '数据分析' },
      },
      {
        path: 'compare',
        name: 'Compare',
        component: () => import('../views/compare/CompareView.vue'),
        meta: { title: '合同对比' },
      },
      {
        path: 'templates',
        name: 'Templates',
        component: () => import('../views/templates/TemplatesView.vue'),
        meta: { title: '模板库' },
      },
      {
        path: 'clauses',
        name: 'Clauses',
        component: () => import('../views/templates/ClausesView.vue'),
        meta: { title: '条款库' },
      },
      {
        path: 'account',
        name: 'Account',
        component: () => import('../views/settings/AccountView.vue'),
        meta: { title: '账户设置' },
      },
      {
        path: 'admin',
        name: 'Admin',
        component: () => import('../views/settings/AdminView.vue'),
        meta: { title: '管理后台', roles: ['owner', 'admin'] },
      },
    ],
  },
  {
    path: '/:pathMatch(.*)*',
    redirect: '/dashboard',
  },
]

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes,
})

router.beforeEach((to, _from, next) => {
  const authStore = useAuthStore()

  if (to.meta.public) {
    if (authStore.isAuthenticated && (to.path === '/login' || to.path === '/register')) {
      next('/dashboard')
      return
    }
    next()
    return
  }

  if (!authStore.isAuthenticated) {
    next({ path: '/login', query: { redirect: to.fullPath } })
    return
  }

  const requiredRoles = to.meta.roles as string[] | undefined
  if (requiredRoles && (!authStore.role || !requiredRoles.includes(authStore.role))) {
    next('/dashboard')
    return
  }

  next()
})

router.afterEach((to) => {
  const title = to.meta.title as string | undefined
  document.title = title ? `${title} - ContractGuard` : 'ContractGuard 合同风险审阅平台'
})

export default router
