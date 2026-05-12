/**
 * FLDCF 专用请求：独立 baseURL（/fldcf-api 或 VITE_FLDCF_BASE_URL），
 * 与 @/utils/request 的 /api 主站隔离。
 */
import axios, { type AxiosInstance, type InternalAxiosRequestConfig } from 'axios'

/** 与 backend `utils.response.Result` 一致 */
export interface Result<T> {
  code: string
  msg: string
  data: T | null
}

/** 对应 backend FldcfStatusResponse 的 data */
export interface FldcfStatusResponse {
  inference_ready: boolean
  cuda_available: boolean
  /** 与请求参数一致：未传则为 null（服务端沿用 FLDCF_CPU） */
  use_cpu_request: boolean | null
  runs_on_cpu: boolean
  device: string
  fldcf_code_root: string
  weights_dir: string
  preset: string
  checkpoint: string
}

/** 对应 backend FldcfPredictResponse 的 data */
export interface FldcfPredictResponse {
  ok: boolean
  inference_device: string
  image_class_index: number
  fake_probability: number
  authentic_probability: number
  mask_tamper_ratio: number
  localization_override: boolean
  mask_png_base64: string
  mask_height: number
  mask_width: number
  input_height: number
  input_width: number
  detail?: string | null
}

const baseURL = import.meta.env.VITE_FLDCF_BASE_URL ?? '/fldcf-api'

const fldcfClient: AxiosInstance = axios.create({
  baseURL,
  timeout: 120_000,
})

fldcfClient.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

/** HTTP 非 2xx 或 BizError 响应体里带 msg */
fldcfClient.interceptors.response.use(
  (response) => response,
  (error) => {
    const d = error.response?.data as { msg?: string } | undefined
    const msg = typeof d?.msg === 'string' ? d.msg : error.message
    return Promise.reject(new Error(msg))
  },
)

export type FldcfPreset = 'fakeV' | 'fakeL' | 'studentV' | 'studentL'

/** 自动=不传 use_cpu；GPU=false；CPU=true */
export type FldcfDevicePreference = 'auto' | 'gpu' | 'cpu'

/** 转为 GET use_cpu 查询：undefined 表示沿用服务端默认 */
export function preferenceToUseCpuQuery(pref: FldcfDevicePreference): boolean | undefined {
  if (pref === 'auto') return undefined
  return pref === 'cpu'
}

export const fldcfApi = {
  /** GET /fldcf/status（经代理为 /fldcf-api/status） */
  async getStatus(
    preset?: string | null,
    useCpu?: boolean | undefined,
  ): Promise<FldcfStatusResponse | null> {
    const params: Record<string, string | boolean> = {}
    if (preset != null && preset !== '') params.preset = preset
    if (useCpu !== undefined) params.use_cpu = useCpu
    const res = await fldcfClient.get<Result<FldcfStatusResponse | null>>('/status', {
      params: Object.keys(params).length ? params : undefined,
    })
    const body = res.data
    if (body?.code === '200') return body.data ?? null
    throw new Error(body?.msg ?? '请求失败')
  },

  /** POST /fldcf/predict，multipart；勿手动设置 Content-Type */
  async predict(
    file: File,
    preset: FldcfPreset,
    useCpu?: boolean | undefined,
  ): Promise<FldcfPredictResponse> {
    const form = new FormData()
    form.append('file', file)
    form.append('preset', preset)
    if (useCpu !== undefined) form.append('use_cpu', useCpu ? '1' : '0')
    const res = await fldcfClient.post<Result<FldcfPredictResponse>>('/predict', form)
    const body = res.data
    if (body?.code === '200' && body.data != null) return body.data
    throw new Error(body?.msg ?? '推理失败')
  },
}
