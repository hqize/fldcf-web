/**
 * FLDCF：与主站同一 axios 实例；网关路径 /fldcf-api 与 /api 并列，不能拼在 baseURL=/api 后面。
 * 单次请求设 baseURL: ''，url 用站点根路径 /fldcf-api/...（避免 /api/../fldcf-api 在部分代理下异常）。
 */
import request from '@/utils/request'

export interface FldcfStatusResponse {
  inference_ready: boolean
  cuda_available: boolean
  use_cpu_request: boolean | null
  runs_on_cpu: boolean
  device: string
  fldcf_code_root: string
  weights_dir: string
  preset: string
  checkpoint: string
}

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

const fldcfOpts = { silent: true, timeout: 120_000, baseURL: '' } as const

export type FldcfPreset = 'fakeV' | 'fakeL' | 'studentV' | 'studentL'
export type FldcfDevicePreference = 'auto' | 'gpu' | 'cpu'

export function preferenceToUseCpuQuery(pref: FldcfDevicePreference): boolean | undefined {
  if (pref === 'auto') return undefined
  return pref === 'cpu'
}

export const fldcfApi = {
  async getStatus(
    preset?: string | null,
    useCpu?: boolean | undefined,
  ): Promise<FldcfStatusResponse | null> {
    const params: Record<string, string | boolean> = {}
    if (preset != null && preset !== '') params.preset = preset
    if (useCpu !== undefined) params.use_cpu = useCpu
    return (await request.get('/fldcf-api/status', {
      ...fldcfOpts,
      params: Object.keys(params).length ? params : undefined,
    })) as FldcfStatusResponse | null
  },

  async predict(file: File, preset: FldcfPreset, useCpu?: boolean | undefined): Promise<FldcfPredictResponse> {
    const form = new FormData()
    form.append('file', file)
    form.append('preset', preset)
    if (useCpu !== undefined) form.append('use_cpu', useCpu ? '1' : '0')
    const data = (await request.post('/fldcf-api/predict', form, fldcfOpts)) as FldcfPredictResponse | null
    if (data == null) throw new Error('推理失败')
    return data
  },
}
