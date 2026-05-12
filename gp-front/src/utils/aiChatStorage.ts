/**
 * AI 助手对话本地持久化（localStorage，按用户名隔离；不上传服务器）
 */

export interface AiChatTurn {
  role: 'user' | 'assistant'
  content: string
}

const PREFIX = 'acid-ai-chat-v1:'
/** 防止撑爆存储：最多保留轮次（user+assistant 各算一条） */
const MAX_TURNS = 120

export function aiChatStorageKey(username: string | undefined | null): string {
  const u = typeof username === 'string' && username.trim() ? username.trim() : 'guest'
  return `${PREFIX}${u}`
}

function normalizeTurns(raw: unknown): AiChatTurn[] {
  if (!Array.isArray(raw)) return []
  const out: AiChatTurn[] = []
  for (const x of raw) {
    if (!x || typeof x !== 'object') continue
    const role = (x as { role?: string }).role
    const content = (x as { content?: string }).content
    if (role !== 'user' && role !== 'assistant') continue
    if (typeof content !== 'string') continue
    out.push({ role, content })
  }
  return out
}

export function loadAiChatTurns(username: string | undefined | null): AiChatTurn[] {
  try {
    const raw = localStorage.getItem(aiChatStorageKey(username))
    if (!raw) return []
    const parsed = JSON.parse(raw) as unknown
    return normalizeTurns(parsed)
  } catch {
    return []
  }
}

export function saveAiChatTurns(username: string | undefined | null, turns: AiChatTurn[]): void {
  try {
    let list = turns
    if (list.length > MAX_TURNS) {
      list = list.slice(list.length - MAX_TURNS)
    }
    const key = aiChatStorageKey(username)
    if (list.length === 0) {
      localStorage.removeItem(key)
      return
    }
    localStorage.setItem(key, JSON.stringify(list))
  } catch {
    /* quota / 隐私模式等 */
  }
}

export function clearAiChatTurns(username: string | undefined | null): void {
  try {
    localStorage.removeItem(aiChatStorageKey(username))
  } catch {
    /* ignore */
  }
}
