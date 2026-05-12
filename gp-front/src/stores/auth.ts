/**
 * 认证状态（Pinia）：token + 用户信息，与 localStorage 同步，供路由守卫与各页共享。
 *
 * axios（@/utils/request、@/api/fldcf）仍从 localStorage 读 token；
 * 登录/退出请通过本 store 写入，以保证内存与本地一致。
 */
import { ref, computed } from 'vue'
import { defineStore } from 'pinia'

import { userApi, type UserInfo } from '@/api/user'

const TOKEN_KEY = 'token'
const USER_INFO_KEY = 'userInfo'

function readUserFromStorage(): UserInfo | null {
  const raw = localStorage.getItem(USER_INFO_KEY)
  if (!raw) return null
  try {
    return JSON.parse(raw) as UserInfo
  } catch {
    return null
  }
}

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string | null>(localStorage.getItem(TOKEN_KEY))
  const user = ref<UserInfo | null>(readUserFromStorage())

  const isLoggedIn = computed(() => Boolean(token.value))

  /** 登录成功后写入 token，并持久化 */
  function setToken(accessToken: string) {
    token.value = accessToken
    localStorage.setItem(TOKEN_KEY, accessToken)
  }

  /** 调用 /auth/me 刷新内存中的用户（登录成功后建议调用一次） */
  async function fetchUser() {
    if (!token.value) {
      user.value = null
      return
    }
    try {
      // request 拦截器已解开 data，运行时即为 UserInfo；此处与 axios 泛型对齐
      const me = (await userApi.getUserInfo()) as unknown as UserInfo
      user.value = me
      localStorage.setItem(USER_INFO_KEY, JSON.stringify(me))
    } catch {
      user.value = null
      localStorage.removeItem(USER_INFO_KEY)
    }
  }

  /** 退出：清空内存与 localStorage */
  function clearAuth() {
    token.value = null
    user.value = null
    localStorage.removeItem(TOKEN_KEY)
    localStorage.removeItem(USER_INFO_KEY)
  }

  /**
   * 其它标签页改了 localStorage 时可调用（可选）；
   * 也可在路由进入前调用，与磁盘同步。
   */
  function syncFromStorage() {
    token.value = localStorage.getItem(TOKEN_KEY)
    user.value = readUserFromStorage()
  }

  return {
    token,
    user,
    isLoggedIn,
    setToken,
    fetchUser,
    clearAuth,
    syncFromStorage,
  }
})
