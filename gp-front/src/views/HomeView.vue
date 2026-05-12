<template>
  <div class="home-shell">
    <!-- ========== TOP BAR ========== -->
    <header class="topbar">
      <div class="theme-toggle" style="margin-left: auto">
        <span class="theme-label">{{ isDark ? '🌙 暗色' : '☀️ 亮色' }}</span>
        <el-switch v-model="isDark" inline-prompt active-text="暗" inactive-text="亮" size="small" />
      </div>

      <el-dropdown trigger="click" @command="onUserCommand">
        <span class="user-menu-trigger">
          <el-avatar :size="30" :src="avatarDisplaySrc" class="user-avatar-el">
            {{ userInitials }}
          </el-avatar>
          <div class="user-info">
            <span class="user-name">{{ currentUser.name }}</span>
            <span class="user-role">{{ currentUser.role }}</span>
          </div>
          <span class="user-chevron">▾</span>
        </span>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item disabled class="dropdown-user-row">
              {{ currentUser.name }}
            </el-dropdown-item>
            <el-dropdown-item command="profile">
              <span class="dropdown-icon">👤</span>
              修改个人信息
            </el-dropdown-item>
            <el-dropdown-item command="settings">
              <span class="dropdown-icon">⚙️</span>
              系统设置
            </el-dropdown-item>
            <el-dropdown-item divided command="logout">
              <span class="dropdown-icon">🚪</span>
              退出登录
            </el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
    </header>

    <!-- ========== TITLE BAR ========== -->
    <div class="titlebar">
      <div class="brand-icon">
        <svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
          <path
            d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 14H9V8h2v8zm4 0h-2V8h2v8z"
          />
          <circle cx="12" cy="12" r="3" fill="rgba(255,255,255,0.4)" />
          <path d="M12 1 L14 5 L12 3 L10 5 Z" fill="rgba(255,255,255,0.8)" />
        </svg>
      </div>
      <div class="titlebar-content">
        <div class="titlebar-heading">
          <span class="titlebar-accent">卫星图像</span>伪造检测
        </div>
        <div class="titlebar-sub">
          SATELLITE IMAGE FORGERY DETECTION · POWERED BY FLDCF
          <span class="brand-badge">v2.0</span>
        </div>
      </div>
    </div>

    <!-- ========== NAV BAR ========== -->
    <nav class="navbar">
      <el-radio-group v-model="activeTab" size="default" class="home-tab-group">
        <el-radio-button v-for="tab in tabs" :key="tab.key" :label="tab.key">
          <span class="nav-tab-inner">
            <span class="nav-icon">{{ tab.icon }}</span>
            {{ tab.label }}
            <el-tag v-if="tab.badge" size="small" type="danger" effect="plain" class="nav-badge-tag">
              {{ tab.badge }}
            </el-tag>
          </span>
        </el-radio-button>
      </el-radio-group>
      <div class="nav-spacer"></div>
      <div class="nav-status" :title="navFldcfTitle">
        <span class="status-dot" :class="navFldcfDotClass"></span>
        {{ navFldcfLine }}
      </div>
    </nav>

    <!-- ========== MAIN CONTENT ========== -->
    <main class="main-content">
      <div class="view-container">
        <div class="page-header">
          <div class="page-header-icon">{{ tabPageHeader.icon }}</div>
          <div class="page-header-text">
            <h2>{{ tabPageHeader.title }}</h2>
            <p>{{ tabPageHeader.subtitle }}</p>
          </div>
        </div>
        <keep-alive :max="10">
          <component :is="tabPanelComponent" />
        </keep-alive>
      </div>
    </main>

    <UserProfileDialog v-model="shell.profileDialogOpen" />
    <AppSettingsDialog v-model="shell.settingsDialogOpen" @open-docs="activeTab = 'docs'" />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onBeforeUnmount, type Component } from 'vue'
import { storeToRefs } from 'pinia'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useRoute, useRouter } from 'vue-router'

import FldcfApi from '@/components/FldcfApi.vue'
import FldcfBatchApi from '@/components/FldcfBatchApi.vue'
import AiAssistant from '@/components/AiAssistant.vue'
import Documentation from '@/components/Documentation.vue'
import DetectionHistory from '@/components/DetectionHistory.vue'
import UserProfileDialog from '@/components/UserProfileDialog.vue'
import AppSettingsDialog from '@/components/AppSettingsDialog.vue'
import { useAuthStore } from '@/stores/auth'
import { useHomeShellStore } from '@/stores/homeShell'
import { useThemeStore } from '@/stores/theme'
import { resolveAvatarUrl } from '@/utils/resolveAvatarUrl'
import { fldcfApi, preferenceToUseCpuQuery, type FldcfStatusResponse } from '@/api/fldcf'
import { useFldcfPrefsStore } from '@/stores/fldcfPrefs'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const themeStore = useThemeStore()
const { isDark } = storeToRefs(themeStore)
const shell = useHomeShellStore()
const fldcfPrefs = useFldcfPrefsStore()
const { preset: fldcfPreset, devicePreference: fldcfDevicePreference } = storeToRefs(fldcfPrefs)

const avatarDisplaySrc = computed(() => resolveAvatarUrl(auth.user?.avatar_url))

const userInitials = computed(() => {
  const n = auth.user?.username?.trim()
  if (!n) return '?'
  return n.length >= 2 ? n.slice(0, 2).toUpperCase() : n.charAt(0).toUpperCase()
})

const currentUser = computed(() => ({
  name: auth.user?.username ?? '未登录',
  role: auth.user?.role ?? ''
}))

function onUserCommand(cmd: string) {
  if (cmd === 'profile') shell.profileDialogOpen = true
  else if (cmd === 'settings') shell.settingsDialogOpen = true
  else if (cmd === 'logout') handleLogout()
}

function handleLogout() {
  ElMessageBox.confirm('确认退出登录？', '退出确认', {
    confirmButtonText: '退出',
    cancelButtonText: '取消',
    type: 'warning'
  })
    .then(() => {
      auth.clearAuth()
      ElMessage.success('已退出登录')
      router.push('/entrance')
    })
    .catch(() => {})
}

// ---- 导航标签 ----
interface TabItem {
  key: string
  label: string
  icon: string
  badge?: string
}

const tabs = ref<TabItem[]>([
  { key: 'single', label: '单个检测', icon: '🛰️', badge: '' },
  { key: 'batch', label: '多个检测', icon: '📦', badge: '' },
  { key: 'history', label: '检测历史', icon: '📜', badge: '' },
  { key: 'assistant', label: 'AI 助手', icon: '🤖', badge: '' },
  { key: 'docs', label: '说明文档', icon: '📄', badge: '' }
])

const TAB_KEYS = ['single', 'batch', 'history', 'assistant', 'docs'] as const

const activeTab = ref<string>('single')

/** Tab 与面板组件（keep-alive 缓存，切换导航不销毁子组件） */
const TAB_PANEL_MAP: Record<string, Component> = {
  single: FldcfApi,
  batch: FldcfBatchApi,
  history: DetectionHistory,
  assistant: AiAssistant,
  docs: Documentation,
}

const TAB_PAGE_HEADERS: Record<
  string,
  {
    icon: string
    title: string
    subtitle: string
  }
> = {
  single: {
    icon: '🛰️',
    title: '单个图像检测',
    subtitle: 'upload single satellite image · run FLDCF inference',
  },
  batch: {
    icon: '📦',
    title: '批量图像检测',
    subtitle: 'batch upload · parallel inference · export results',
  },
  history: {
    icon: '📜',
    title: '检测历史',
    subtitle: 'server-side detection log · metrics only · no mask stored',
  },
  assistant: {
    icon: '🤖',
    title: 'AI 智能助手',
    subtitle: 'ask questions about detection results · model insights',
  },
  docs: {
    icon: '📄',
    title: '说明文档',
    subtitle: 'system manual · algorithm documentation · api reference',
  },
}

const tabPanelComponent = computed<Component>(() => TAB_PANEL_MAP[activeTab.value] ?? FldcfApi)

const tabPageHeader = computed(() => TAB_PAGE_HEADERS[activeTab.value] ?? TAB_PAGE_HEADERS.single!)

/** 导航栏 FLDCF 状态（与页内 FldcfApi 一致数据源：GET /fldcf/status） */
const fldcfNavStatus = ref<FldcfStatusResponse | null>(null)
const fldcfNavLoading = ref(true)
const fldcfNavFetchFailed = ref(false)

const NAV_FLDCF_POLL_MS = 45_000

let fldcfNavPollTimer: ReturnType<typeof setInterval> | null = null

async function refreshFldcfNavStatus() {
  fldcfNavLoading.value = true
  try {
    fldcfNavStatus.value = await fldcfApi.getStatus(
      fldcfPreset.value,
      preferenceToUseCpuQuery(fldcfDevicePreference.value),
    )
    fldcfNavFetchFailed.value = false
  } catch {
    // 仅首次从未成功拉取过时标记不可达；轮询失败保留上一次结果，避免闪烁
    fldcfNavFetchFailed.value = fldcfNavStatus.value == null
  } finally {
    fldcfNavLoading.value = false
  }
}

const navFldcfLine = computed(() => {
  if (fldcfNavLoading.value && !fldcfNavStatus.value && !fldcfNavFetchFailed.value) {
    return '推理服务检测中…'
  }
  if (fldcfNavFetchFailed.value || (!fldcfNavStatus.value && !fldcfNavLoading.value)) {
    return 'FLDCF 不可达'
  }
  const s = fldcfNavStatus.value!
  if (!s.inference_ready) {
    return '模型未就绪（检查权重与源码路径）'
  }
  const runsCpu = s.runs_on_cpu || String(s.device).toLowerCase().startsWith('cpu')
  const chip = runsCpu ? 'CPU' : 'GPU'
  const dev = s.device && s.device !== 'n/a' ? ` · ${s.device}` : ''
  return `模型已就绪 · ${chip}${dev}`
})

const navFldcfTitle = computed(() => {
  const s = fldcfNavStatus.value
  if (!s || fldcfNavFetchFailed.value) return navFldcfLine.value
  return [
    navFldcfLine.value,
    `CUDA ${s.cuda_available ? '可用' : '不可用'}`,
    s.checkpoint ? `权重 ${s.checkpoint}` : '',
  ]
    .filter(Boolean)
    .join('\n')
})

const navFldcfDotClass = computed(() => {
  if (fldcfNavLoading.value && !fldcfNavStatus.value && !fldcfNavFetchFailed.value) return 'is-loading'
  if (fldcfNavFetchFailed.value) return 'is-bad'
  const s = fldcfNavStatus.value
  if (!s) return 'is-warn'
  if (!s.inference_ready) return 'is-warn'
  return 'is-ok'
})

onMounted(() => {
  void auth.fetchUser()
  void refreshFldcfNavStatus()
  fldcfNavPollTimer = setInterval(() => void refreshFldcfNavStatus(), NAV_FLDCF_POLL_MS)
  const t = route.query.tab
  if (typeof t === 'string' && TAB_KEYS.includes(t as (typeof TAB_KEYS)[number])) {
    activeTab.value = t
  }
  if (route.query.tab !== activeTab.value) {
    router.replace({ path: '/home', query: { ...route.query, tab: activeTab.value } })
  }
})

onBeforeUnmount(() => {
  if (fldcfNavPollTimer != null) {
    clearInterval(fldcfNavPollTimer)
    fldcfNavPollTimer = null
  }
})

watch(activeTab, (tab) => {
  if (route.query.tab !== tab) {
    router.replace({ path: '/home', query: { ...route.query, tab } })
  }
})

watch(
  () => route.query.tab,
  (t) => {
    if (typeof t === 'string' && TAB_KEYS.includes(t as (typeof TAB_KEYS)[number]) && t !== activeTab.value) {
      activeTab.value = t
    }
  }
)

watch([fldcfPreset, fldcfDevicePreference], () => void refreshFldcfNavStatus())
</script>

<style>
/* ===================== CSS 变量 & 全局重置 ===================== */
:root {
  --color-bg: #f0f2f7;
  --color-surface: #ffffff;
  --color-surface-2: #f5f7fb;
  --color-border: #dde2ee;
  --color-text-primary: #1a1f36;
  --color-text-secondary: #6b7a99;
  --color-text-muted: #a0aabf;
  --color-accent: #2563eb;
  --color-accent-light: #eff4ff;
  --color-accent-hover: #1d4ed8;
  --color-success: #10b981;
  --color-warning: #f59e0b;
  --color-danger: #ef4444;
  --color-header-bg: #0f172a;
  --color-header-text: #e2e8f0;
  --color-header-sub: #94a3b8;
  --color-titlebar-bg: #53252d; /* 与 topbar 区分 */
  --color-nav-active-bg: rgba(37, 99, 235, 0.12);
  --color-nav-active-text: #2563eb;
  --color-nav-hover: rgba(37, 99, 235, 0.06);
  --color-tag-bg: rgba(37, 99, 235, 0.08);
  --shadow-sm: 0 1px 3px rgba(0, 0, 0, 0.08), 0 1px 2px rgba(0, 0, 0, 0.04);
  --shadow-md: 0 4px 16px rgba(0, 0, 0, 0.1);
  --shadow-header: 0 2px 12px rgba(0, 0, 0, 0.22);
  --transition: 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  --radius-sm: 6px;
  --radius-md: 10px;
  --radius-lg: 16px;
  --font-body: 'Noto Sans SC', sans-serif;
  --font-mono: 'Space Mono', monospace;
}

[data-theme='dark'] {
  --color-bg: #0d1117;
  --color-surface: #161b27;
  --color-surface-2: #1c2233;
  --color-border: #2a3349;
  --color-text-primary: #e2e8f0;
  --color-text-secondary: #94a3b8;
  --color-text-muted: #4a5568;
  --color-accent: #3b82f6;
  --color-accent-light: rgba(59, 130, 246, 0.1);
  --color-accent-hover: #60a5fa;
  --color-success: #34d399;
  --color-warning: #fbbf24;
  --color-danger: #f87171;
  --color-header-bg: #060c18;
  --color-header-text: #e2e8f0;
  --color-header-sub: #64748b;
  --color-titlebar-bg: #0d1b33; /* 暗色模式区分 */
  --color-nav-active-bg: rgba(59, 130, 246, 0.15);
  --color-nav-active-text: #60a5fa;
  --color-nav-hover: rgba(59, 130, 246, 0.07);
  --color-tag-bg: rgba(59, 130, 246, 0.1);
  --shadow-sm: 0 1px 3px rgba(0, 0, 0, 0.35);
  --shadow-md: 0 4px 16px rgba(0, 0, 0, 0.45);
  --shadow-header: 0 2px 16px rgba(0, 0, 0, 0.55);
}

*,
*::before,
*::after {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}

html,
body {
  height: 100%;
}

body {
  font-family: var(--font-body);
  background: var(--color-bg);
  color: var(--color-text-primary);
  transition: background var(--transition), color var(--transition);
  min-height: 100vh;
}

/* ===================== App Shell ===================== */
.home-shell {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
}

/* ===================== Top Bar ===================== */
.topbar {
  position: sticky;
  top: 0;
  z-index: 100;
  display: flex;
  align-items: center;
  background: var(--color-header-bg);
  box-shadow: var(--shadow-header);
  height: 60px;
  padding: 0 24px;
  transition: background var(--transition);
}

/* ===================== Theme Toggle ===================== */
.theme-toggle {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-right: 20px;
}

.theme-label {
  font-size: 12px;
  color: var(--color-header-sub);
  font-family: var(--font-mono);
}

.theme-toggle .el-switch__core {
  border-color: #334155;
}

/* ===================== User Menu ===================== */
.user-menu-trigger {
  display: flex;
  align-items: center;
  gap: 10px;
  cursor: pointer;
  padding: 6px 12px;
  border-radius: var(--radius-sm);
  border: 1px solid #1e293b;
  background: rgba(255, 255, 255, 0.04);
  transition: all var(--transition);
  position: relative;
}

.user-menu-trigger:hover {
  background: rgba(255, 255, 255, 0.08);
  border-color: #334155;
}

.user-avatar-el {
  flex-shrink: 0;
}

.user-info {
  display: flex;
  flex-direction: column;
  gap: 1px;
  align-items: flex-start;
}

.user-name {
  font-size: 13px;
  font-weight: 600;
  color: #e2e8f0;
  line-height: 1;
}

.user-role {
  font-size: 10px;
  color: #64748b;
  font-family: var(--font-mono);
}

.user-chevron {
  color: #475569;
  font-size: 11px;
  transition: transform var(--transition);
}

.user-menu-trigger:hover .user-chevron {
  color: #94a3b8;
}

.dropdown-user-row {
  font-weight: 700;
  color: var(--color-text-primary) !important;
  opacity: 1 !important;
}

.dropdown-icon {
  display: inline-block;
  width: 18px;
  text-align: center;
  margin-right: 4px;
  opacity: 0.85;
}

/* ===================== Title Bar (品牌区) ===================== */
.titlebar {
  background: var(--color-titlebar-bg);
  display: flex;
  align-items: center;
  justify-content: flex-start; /* 左对齐 */
  height: 64px;
  padding: 0 24px;
  position: sticky;
  top: 60px;
  z-index: 95;
  border-bottom: 2px solid var(--color-accent);
  box-shadow: 0 2px 16px rgba(37, 99, 235, 0.15);
  transition: background var(--transition);
}

.brand-icon {
  width: 36px;
  height: 36px;
  border-radius: 8px;
  background: linear-gradient(135deg, #2563eb 0%, #0ea5e9 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  box-shadow: 0 0 0 2px rgba(37, 99, 235, 0.3), 0 2px 8px rgba(37, 99, 235, 0.3);
  margin-right: 14px;
}

.brand-icon svg {
  width: 20px;
  height: 20px;
  fill: #fff;
}

.titlebar-content {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.titlebar-heading {
  font-size: 22px;
  font-weight: 700;
  color: #e2e8f0;
  letter-spacing: 0.05em;
  line-height: 1.2;
}

.titlebar-accent {
  color: #60a5fa;
}

.titlebar-sub {
  font-size: 10px;
  font-family: var(--font-mono);
  color: #64748b;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  display: flex;
  align-items: center;
  gap: 6px;
}

.brand-badge {
  font-size: 10px;
  font-family: var(--font-mono);
  background: rgba(37, 99, 235, 0.2);
  color: #60a5fa;
  border: 1px solid rgba(37, 99, 235, 0.35);
  border-radius: 4px;
  padding: 1px 6px;
  letter-spacing: 0.05em;
}

/* ===================== Navigation ===================== */
.navbar {
  background: var(--color-surface);
  border-bottom: 1px solid var(--color-border);
  padding: 0 24px;
  display: flex;
  align-items: center;
  gap: 4px;
  height: 50px;
  box-shadow: var(--shadow-sm);
  transition: background var(--transition), border-color var(--transition);
  position: sticky;
  top: 124px; /* 60 + 64 */
  z-index: 90;
}

.home-tab-group {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  align-items: center;
}

.home-tab-group .el-radio-button__inner {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.nav-tab-inner {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.nav-icon {
  font-size: 15px;
  line-height: 1;
}

.nav-badge-tag {
  margin-left: 2px;
}

.nav-spacer {
  flex: 1;
}

.nav-status {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 11px;
  color: var(--color-text-muted);
  font-family: var(--font-mono);
  max-width: min(420px, 42vw);
  text-align: right;
  line-height: 1.3;
}

@media (max-width: 720px) {
  .nav-status {
    max-width: 36vw;
    font-size: 10px;
  }
}

.status-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  flex-shrink: 0;
}

.status-dot.is-ok {
  background: var(--color-success);
  animation: pulse-ok 2s ease infinite;
}

.status-dot.is-loading {
  background: var(--color-text-muted);
  animation: pulse-muted 1.4s ease infinite;
}

.status-dot.is-warn {
  background: var(--color-warning);
  animation: pulse-warn 2s ease infinite;
}

.status-dot.is-bad {
  background: var(--color-danger);
  animation: none;
}

@keyframes pulse-ok {
  0%,
  100% {
    opacity: 1;
    box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.4);
  }
  50% {
    opacity: 0.85;
    box-shadow: 0 0 0 4px rgba(16, 185, 129, 0);
  }
}

@keyframes pulse-muted {
  0%,
  100% {
    opacity: 0.45;
  }
  50% {
    opacity: 1;
  }
}

@keyframes pulse-warn {
  0%,
  100% {
    opacity: 1;
    box-shadow: 0 0 0 0 rgba(245, 158, 11, 0.35);
  }
  50% {
    opacity: 0.85;
    box-shadow: 0 0 0 4px rgba(245, 158, 11, 0);
  }
}

/* ===================== Main Content ===================== */
.main-content {
  flex: 1;
  padding: 28px 28px 40px;
  max-width: 1400px;
  width: 100%;
  margin: 0 auto;
}

/* ===================== View Container ===================== */
.view-container {
  animation: viewFadeIn 0.25s ease;
}

@keyframes viewFadeIn {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* ===================== Empty placeholder ===================== */
.placeholder-card {
  background: var(--color-surface);
  border: 1px dashed var(--color-border);
  border-radius: var(--radius-lg);
  min-height: 480px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 16px;
  padding: 48px;
  transition: background var(--transition), border-color var(--transition);
}

.placeholder-icon {
  width: 64px;
  height: 64px;
  border-radius: var(--radius-md);
  background: var(--color-accent-light);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 28px;
}

.placeholder-title {
  font-size: 18px;
  font-weight: 700;
  color: var(--color-text-primary);
}

.placeholder-desc {
  font-size: 13px;
  color: var(--color-text-muted);
  font-family: var(--font-mono);
  text-align: center;
}

.placeholder-tag {
  font-size: 11px;
  font-family: var(--font-mono);
  background: var(--color-tag-bg);
  color: var(--color-accent);
  border-radius: 4px;
  padding: 3px 10px;
  border: 1px solid rgba(37, 99, 235, 0.15);
}

/* ===================== Page header ===================== */
.page-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 20px;
}

.page-header-icon {
  width: 40px;
  height: 40px;
  border-radius: var(--radius-sm);
  background: var(--color-accent-light);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  border: 1px solid rgba(37, 99, 235, 0.15);
}

.page-header-text h2 {
  font-size: 18px;
  font-weight: 700;
  color: var(--color-text-primary);
}

.page-header-text p {
  font-size: 12px;
  color: var(--color-text-muted);
  font-family: var(--font-mono);
  margin-top: 2px;
}

/* 滚动条美化 */
::-webkit-scrollbar {
  width: 6px;
}
::-webkit-scrollbar-track {
  background: transparent;
}
::-webkit-scrollbar-thumb {
  background: var(--color-border);
  border-radius: 3px;
}
</style>