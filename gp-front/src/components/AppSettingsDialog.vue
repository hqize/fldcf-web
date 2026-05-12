<script setup lang="ts">
import { computed } from 'vue'
import { storeToRefs } from 'pinia'

import { useThemeStore } from '@/stores/theme'

defineProps<{
  modelValue: boolean
}>()

const emit = defineEmits<{
  'update:modelValue': [boolean]
  openDocs: []
}>()

const themeStore = useThemeStore()
const { isDark } = storeToRefs(themeStore)

const themeModel = computed({
  get: () => (isDark.value ? 'dark' : 'light'),
  set: (v: string) => themeStore.setDark(v === 'dark'),
})

function goDocs() {
  emit('openDocs')
  emit('update:modelValue', false)
}
</script>

<template>
  <el-dialog
    :model-value="modelValue"
    title="系统设置"
    width="420px"
    destroy-on-close
    @update:model-value="emit('update:modelValue', $event)"
  >
    <div class="settings-section">
      <div class="settings-label">外观</div>
      <el-radio-group v-model="themeModel" class="theme-group">
        <el-radio-button label="light">亮色</el-radio-button>
        <el-radio-button label="dark">暗色</el-radio-button>
      </el-radio-group>
      <p class="settings-hint">与顶部栏主题开关同步，并保存在本浏览器。</p>
    </div>

    <el-divider />

    <div class="settings-section">
      <div class="settings-label">关于</div>
      <p class="about-line"><strong>卫星图像伪造检测</strong> · FLDCF</p>
      <p class="about-meta">前端 v2.1 · 本地偏好存储</p>
      <el-button type="primary" link @click="goDocs">查看说明文档</el-button>
    </div>
  </el-dialog>
</template>

<style scoped>
.settings-section {
  padding: 4px 0;
}

.settings-label {
  font-size: 13px;
  font-weight: 700;
  color: var(--color-text-primary, #1a1f36);
  margin-bottom: 10px;
}

.theme-group {
  width: 100%;
  display: flex;
}

.theme-group :deep(.el-radio-button) {
  flex: 1;
}

.theme-group :deep(.el-radio-button__inner) {
  width: 100%;
}

.settings-hint {
  margin: 10px 0 0;
  font-size: 12px;
  color: var(--color-text-muted, #94a3b8);
  line-height: 1.5;
}

.about-line {
  margin: 0 0 6px;
  font-size: 14px;
  color: var(--color-text-secondary, #475569);
}

.about-meta {
  margin: 0 0 12px;
  font-size: 12px;
  color: var(--color-text-muted, #94a3b8);
}
</style>
