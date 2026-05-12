import { defineStore } from 'pinia'
import { ref, watch } from 'vue'

import { applyDomTheme, readStoredDark, saveDark } from '@/utils/themePreference'

/** 全局明暗主题：与 localStorage、`data-theme` 同步，供 HomeView 与系统设置共用 */
export const useThemeStore = defineStore('theme', () => {
  const isDark = ref(readStoredDark() ?? false)

  function setDark(value: boolean) {
    isDark.value = value
  }

  watch(
    isDark,
    (v) => {
      applyDomTheme(v)
      saveDark(v)
    },
    { immediate: true },
  )

  return { isDark, setDark }
})
