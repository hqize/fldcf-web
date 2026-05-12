import { defineStore } from 'pinia'
import { ref } from 'vue'

/** Home 壳层 UI：个人信息 / 系统设置弹窗开关 */
export const useHomeShellStore = defineStore('homeShell', () => {
  const profileDialogOpen = ref(false)
  const settingsDialogOpen = ref(false)

  return {
    profileDialogOpen,
    settingsDialogOpen,
  }
})
