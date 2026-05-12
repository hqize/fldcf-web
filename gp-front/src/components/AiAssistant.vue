<script setup lang="ts">
import { ref, computed, onMounted, watch, nextTick } from 'vue'
import { ElMessage } from 'element-plus'

import { aichatApi, type AiChatStatus } from '@/api/aichat'
import { useAuthStore } from '@/stores/auth'
import {
  loadAiChatTurns,
  saveAiChatTurns,
  clearAiChatTurns,
} from '@/utils/aiChatStorage'
import { renderAiMarkdown } from '@/utils/renderAiMarkdown'

const SYSTEM_PROMPT =
  '你是卫星遥感图像伪造检测系统的智能助手。请用简明中文回答，涉及模型输出时可解释伪造/真实概率与篡改 mask 的含义；不确定时请说明局限。'

/** 一键填入并发送的预设问题（与说明文档「AI 助手」小节保持一致） */
const PRESET_QUESTIONS = [
  {
    label: '概率含义',
    text: 'FLDCF 输出的「伪造概率」「真实概率」分别表示什么？如何判断一张卫星图是否可疑？',
  },
  {
    label: 'mask 解读',
    text: 'mask 可视化里黑色和白色区域分别代表什么？「篡改像素占比」数值该如何理解？',
  },
  {
    label: '权重线区别',
    text: 'fakeV、fakeL、studentV、studentL 等权重线有什么区别？各自更适合什么数据或场景？',
  },
  {
    label: '批量检测',
    text: '批量图像检测时推理是顺序执行还是并行？结果表格里的分类与导出 CSV 大致包含哪些内容？',
  },
  {
    label: '方法局限',
    text: '卫星遥感图像伪造检测有哪些常见思路？在实际应用中有哪些局限需要注意？',
  },
] as const

type Turn = { role: 'user' | 'assistant'; content: string }

const auth = useAuthStore()

const status = ref<AiChatStatus | null>(null)
const loadingStatus = ref(true)
const sending = ref(false)
const input = ref('')
const thread = ref<Turn[]>([])
const scrollRef = ref<HTMLElement | null>(null)

const configured = computed(() => status.value?.configured === true)

async function loadStatus() {
  loadingStatus.value = true
  try {
    status.value = await aichatApi.getStatus()
  } catch {
    status.value = null
  } finally {
    loadingStatus.value = false
  }
}

async function scrollToBottom() {
  await nextTick()
  const el = scrollRef.value
  if (el) el.scrollTop = el.scrollHeight
}

async function send() {
  const text = input.value.trim()
  if (!text || sending.value) return
  if (!configured.value) {
    ElMessage.warning('服务端未配置 DeepSeek，请在后端 .env 填写 DEEPSEEK_BASE_URL 与 DEEPSEEK_API_KEY')
    return
  }

  sending.value = true
  input.value = ''
  thread.value.push({ role: 'user', content: text })

  const messages: { role: 'system' | 'user' | 'assistant'; content: string }[] = [
    { role: 'system', content: SYSTEM_PROMPT },
    ...thread.value.map((t) => ({ role: t.role, content: t.content })),
  ]

  try {
    const res = await aichatApi.chat(messages)
    thread.value.push({ role: 'assistant', content: res.reply || '（模型未返回文本）' })
    await scrollToBottom()
  } catch (e) {
    thread.value.pop()
    const msg = e instanceof Error ? e.message : '发送失败'
    ElMessage.error(msg)
  } finally {
    sending.value = false
    await scrollToBottom()
  }
}

function clearThread() {
  thread.value = []
  clearAiChatTurns(auth.user?.username)
}

function pickPreset(text: string) {
  input.value = text
  void send()
}

function onKeydown(e: KeyboardEvent) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    void send()
  }
}

function hydrateThreadFromStorage() {
  thread.value = loadAiChatTurns(auth.user?.username) as Turn[]
}

watch(
  () => auth.user?.username,
  () => {
    hydrateThreadFromStorage()
  },
  { immediate: true },
)

watch(
  thread,
  (list) => {
    saveAiChatTurns(auth.user?.username, list)
  },
  { deep: true },
)

onMounted(() => {
  void loadStatus()
})
</script>

<template>
  <div class="ai-assistant">
    <div v-if="loadingStatus" class="ai-banner muted">正在检查 AI 服务配置…</div>
    <div v-else-if="status && !status.configured" class="ai-banner warn">
      后端未配置 DeepSeek（缺少 DEEPSEEK_BASE_URL / DEEPSEEK_API_KEY）。配置并重启 main.py 后即可对话。
    </div>
    <div v-else-if="status" class="ai-banner ok">
      模型：<span class="mono">{{ status.default_model }}</span>
    </div>

    <div class="ai-shell">
      <div ref="scrollRef" class="ai-thread">
        <div v-if="!thread.length" class="ai-empty">
          输入问题后开始对话。可询问检测结果含义、流程说明或与遥感伪造检测相关的概念。
        </div>
        <div
          v-for="(m, i) in thread"
          :key="i"
          class="ai-msg"
          :class="m.role === 'user' ? 'ai-msg-user' : 'ai-msg-assistant'"
        >
          <span class="ai-msg-label">{{ m.role === 'user' ? '你' : '助手' }}</span>
          <div
            v-if="m.role === 'assistant'"
            class="ai-msg-body ai-msg-md"
            v-html="renderAiMarkdown(m.content)"
          />
          <div v-else class="ai-msg-body">{{ m.content }}</div>
        </div>
        <div v-if="sending" class="ai-msg ai-msg-assistant ai-msg-pending">
          <span class="ai-msg-label">助手</span>
          <div class="ai-msg-body">思考中…</div>
        </div>
      </div>

      <div class="ai-input-row">
        <div v-if="configured && !loadingStatus" class="ai-presets">
          <span class="ai-presets-label">快捷提问</span>
          <div class="ai-presets-chips">
            <el-button
              v-for="(p, idx) in PRESET_QUESTIONS"
              :key="idx"
              size="small"
              plain
              type="primary"
              :disabled="sending"
              :title="p.text"
              class="ai-preset-btn"
              @click="pickPreset(p.text)"
            >
              {{ p.label }}
            </el-button>
          </div>
        </div>
        <el-input
          v-model="input"
          type="textarea"
          :rows="3"
          resize="none"
          placeholder="输入内容，Enter 发送；Shift+Enter 换行"
          :disabled="sending || loadingStatus"
          class="ai-textarea"
          @keydown="onKeydown"
        />
        <div class="ai-actions">
          <el-button size="default" :disabled="sending || loadingStatus" @click="clearThread">清空对话</el-button>
          <el-button type="primary" :loading="sending" :disabled="loadingStatus" @click="send">发送</el-button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.ai-assistant {
  width: 100%;
  max-width: 900px;
  margin-left: 0;
  margin-right: auto;
}

.ai-banner {
  padding: 10px 14px;
  border-radius: 10px;
  font-size: 13px;
  margin-bottom: 14px;
  line-height: 1.5;
}

.ai-banner.muted {
  background: var(--color-surface-2, #f5f7fb);
  color: var(--color-text-secondary, #6b7a99);
}

.ai-banner.warn {
  background: rgba(245, 158, 11, 0.12);
  color: var(--color-warning, #b45309);
  border: 1px solid rgba(245, 158, 11, 0.35);
}

.ai-banner.ok {
  background: rgba(37, 99, 235, 0.08);
  color: var(--color-text-secondary, #475569);
  border: 1px solid rgba(37, 99, 235, 0.2);
}

.mono {
  font-family: var(--font-mono, ui-monospace, monospace);
  font-weight: 600;
}

.ai-shell {
  border: 1px solid var(--color-border, #dde2ee);
  border-radius: 12px;
  background: var(--color-surface, #fff);
  box-shadow: var(--shadow-sm, 0 1px 3px rgba(0, 0, 0, 0.06));
  overflow: hidden;
  display: flex;
  flex-direction: column;
  min-height: min(62vh, 520px);
  max-height: min(70vh, 580px);
}

.ai-thread {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 16px 18px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.ai-empty {
  font-size: 13px;
  color: var(--color-text-muted, #94a3b8);
  text-align: center;
  padding: 32px 16px;
  line-height: 1.6;
}

.ai-msg {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 6px;
  max-width: 92%;
}

.ai-msg-user {
  align-self: flex-end;
  align-items: flex-end;
}

.ai-msg-assistant {
  align-self: flex-start;
}

.ai-msg-label {
  font-size: 11px;
  font-weight: 700;
  color: var(--color-text-muted, #94a3b8);
  letter-spacing: 0.04em;
}

.ai-msg-body {
  padding: 10px 14px;
  border-radius: 12px;
  font-size: 14px;
  line-height: 1.55;
  white-space: pre-wrap;
  word-break: break-word;
}

.ai-msg-user .ai-msg-body {
  background: var(--color-accent-light, #eff4ff);
  color: var(--color-text-primary, #1a1f36);
  border: 1px solid rgba(37, 99, 235, 0.18);
}

.ai-msg-assistant .ai-msg-body {
  background: var(--color-surface-2, #f6f8fa);
  color: var(--color-text-primary, #1a1f36);
  border: 1px solid var(--color-border, #e5e7eb);
}

/* Markdown（助手消息） */
.ai-msg-md {
  white-space: normal;
}

.ai-msg-md :deep(p) {
  margin: 0 0 0.65em;
}

.ai-msg-md :deep(p:last-child) {
  margin-bottom: 0;
}

.ai-msg-md :deep(h1),
.ai-msg-md :deep(h2),
.ai-msg-md :deep(h3),
.ai-msg-md :deep(h4) {
  margin: 0.85em 0 0.45em;
  font-weight: 700;
  line-height: 1.35;
}

.ai-msg-md :deep(h1:first-child),
.ai-msg-md :deep(h2:first-child),
.ai-msg-md :deep(h3:first-child) {
  margin-top: 0;
}

.ai-msg-md :deep(ul),
.ai-msg-md :deep(ol) {
  margin: 0.35em 0 0.65em;
  padding-left: 1.35rem;
}

.ai-msg-md :deep(li) {
  margin: 0.2em 0;
}

.ai-msg-md :deep(pre) {
  margin: 0.5em 0;
  padding: 10px 12px;
  border-radius: 8px;
  background: var(--color-bg, #0d1117);
  color: #e6edf3;
  overflow-x: auto;
  font-size: 12px;
  line-height: 1.45;
}

.ai-msg-md :deep(code) {
  font-family: var(--font-mono, ui-monospace, monospace);
  font-size: 0.92em;
  padding: 0.1em 0.35em;
  border-radius: 4px;
  background: rgba(0, 0, 0, 0.06);
}

.ai-msg-md :deep(pre code) {
  padding: 0;
  background: transparent;
  color: inherit;
  font-size: inherit;
}

.ai-msg-md :deep(blockquote) {
  margin: 0.5em 0;
  padding: 0.35em 0 0.35em 0.85em;
  border-left: 3px solid var(--color-accent, #2563eb);
  color: var(--color-text-secondary, #475569);
}

.ai-msg-md :deep(a) {
  color: var(--color-accent, #2563eb);
  text-decoration: underline;
  text-underline-offset: 2px;
}

.ai-msg-md :deep(table) {
  border-collapse: collapse;
  font-size: 13px;
  margin: 0.5em 0;
  width: 100%;
}

.ai-msg-md :deep(th),
.ai-msg-md :deep(td) {
  border: 1px solid var(--color-border, #e5e7eb);
  padding: 6px 8px;
}

.ai-msg-md :deep(th) {
  background: var(--color-surface-2, #f1f5f9);
}

[data-theme='dark'] .ai-msg-md :deep(pre) {
  background: #161b22;
  color: #e6edf3;
}

[data-theme='dark'] .ai-msg-md :deep(code) {
  background: rgba(255, 255, 255, 0.08);
}

.ai-msg-pending .ai-msg-body {
  color: var(--color-text-muted, #94a3b8);
  font-style: italic;
}

.ai-input-row {
  flex-shrink: 0;
  padding: 12px 14px 14px;
  border-top: 1px dashed var(--color-border, #dde2ee);
  background: var(--color-surface-2, #fafbfc);
}

.ai-presets {
  margin-bottom: 10px;
}

.ai-presets-label {
  display: block;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.06em;
  color: var(--color-text-muted, #94a3b8);
  margin-bottom: 8px;
}

.ai-presets-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.ai-preset-btn {
  font-size: 12px;
}

.ai-textarea :deep(.el-textarea__inner) {
  font-size: 14px;
  border-radius: 10px;
}

.ai-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 10px;
}
</style>
