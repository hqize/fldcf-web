/**
 * AI 助手：与主站同源 baseURL（VITE_API_BASE_URL → FastAPI /aichat）
 */
import request from '@/utils/request'

export interface AiChatStatus {
  configured: boolean
  default_model: string
}

export interface ChatMessagePayload {
  role: 'system' | 'user' | 'assistant'
  content: string
}

export interface AiChatResponse {
  reply: string
  model: string
}

const CHAT_TIMEOUT_MS = 120_000

export const aichatApi = {
  async getStatus(): Promise<AiChatStatus> {
    // axios 封装在拦截器里已解包为业务 data，类型与 AxiosResponse 不一致处做断言
    return request.get('/aichat/status') as Promise<AiChatStatus>
  },

  async chat(messages: ChatMessagePayload[]): Promise<AiChatResponse> {
    return request.post('/aichat/chat', { messages }, { timeout: CHAT_TIMEOUT_MS }) as Promise<AiChatResponse>
  },
}
