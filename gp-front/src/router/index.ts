import { createRouter, createWebHistory } from 'vue-router'

import { useAuthStore } from '@/stores/auth'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      redirect: '/entrance',
    },
    {
      path: '/viz',
      name: 'viz',
      redirect: { path: '/home', query: { tab: 'single' } },
    },
    {
      path: '/dev/fldcf-api',
      name: 'fldcfApi',
      redirect: { path: '/home', query: { tab: 'single' } },
    },
    {
      path: '/entrance',
      name: 'entrance',
      component: () => import('@/views/LoginRegister.vue'),
      meta: { guestOnly: true },
    },
    {
      path: '/home',
      name: 'home',
      // component: () => import('@/views/HomeView.vue'),
       component: () => import('@/views/HomeView.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/:pathMatch(.*)*', // 匹配所有未定义路径
      name: 'NotFound',         // 语义化命名
      component: () => import('@/views/404.vue')
    }
  ],
})

router.beforeEach((to) => {
  const auth = useAuthStore()
  auth.syncFromStorage()
  const isLoggedIn = auth.isLoggedIn

  if (to.meta.requiresAuth && !isLoggedIn) {
    return '/entrance'
  }
  if (to.meta.guestOnly && isLoggedIn) {
    return '/home'
  }
  return true
})

export default router