import { defineStore } from 'pinia'
import { ref } from 'vue'

import type { FldcfDevicePreference, FldcfPreset } from '@/api/fldcf'

/**
 * FLDCF 面板与主页导航栏共用：preset / 推理设备偏好，
 * 保证 GET /fldcf/status 与当前界面选择一致
 */
export const useFldcfPrefsStore = defineStore('fldcfPrefs', () => {
  const preset = ref<FldcfPreset>('fakeV')
  const devicePreference = ref<FldcfDevicePreference>('auto')

  return { preset, devicePreference }
})
