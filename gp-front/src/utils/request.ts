/**
 * 同源 axios：baseURL 与后端同一来源（默认 /api，可被 VITE_API_BASE_URL 覆盖）。
 * 业务路径写相对 base 的短路径（如 /auth/login）。FLDCF 等并列网关见 fldcf.ts（单次请求 baseURL: ''）。
 * 需静默失败时传 silent: true；长耗时请求单独设 timeout。
 */
import axios from 'axios'
import type { AxiosInstance, AxiosResponse, InternalAxiosRequestConfig } from 'axios'
import { ElMessage } from 'element-plus'

function isSilent(config: InternalAxiosRequestConfig) {
  return Boolean((config as InternalAxiosRequestConfig & { silent?: boolean }).silent)
}

function attachAuthAndFormData(config: InternalAxiosRequestConfig) {
  const token = localStorage.getItem('token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  if (config.data instanceof FormData) {
    delete config.headers['Content-Type']
  }
  return config
}

const request: AxiosInstance = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api',
  timeout: 30_000,
  headers: { 'Content-Type': 'application/json' },
})

request.interceptors.request.use(attachAuthAndFormData, (error) => {
  console.error('请求错误:', error)
  return Promise.reject(error)
})

request.interceptors.response.use(
  (response: AxiosResponse) => {
    const res = response.data
    const silent = isSilent(response.config)
    if (res?.code === '200') return res.data
    if (!silent) {
      ElMessage.error(res?.msg || '请求失败')
      return Promise.reject(res)
    }
    return Promise.reject(new Error(res?.msg || '请求失败'))
  },
  (error) => {
    console.error('响应错误:', error)
    const silent = error.config ? isSilent(error.config) : false
    if (!silent) {
      if (error.message.includes('Network Error')) ElMessage.error('网络连接异常')
      else if (error.message.includes('timeout')) ElMessage.error('请求超时')
      else ElMessage.error(error.response?.data?.msg || '请求失败')
      return Promise.reject(error)
    }
    const msg =
      (typeof error.response?.data?.msg === 'string' && error.response.data.msg) ||
      (error.message.includes('timeout') ? '请求超时' : '') ||
      error.message ||
      '请求失败'
    return Promise.reject(new Error(msg))
  },
)

export default request
