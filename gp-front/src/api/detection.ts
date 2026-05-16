/**
 * 检测历史（需登录）
 */
import request from '@/utils/request'

import type { FldcfPredictResponse } from '@/api/fldcf'

export type DetectionMode = 'single' | 'batch'

export interface DetectionCreateItem {
  mode: DetectionMode
  preset: string
  source_filename: string
  ok: boolean
  error_message?: string | null
  image_class_index?: number | null
  fake_probability?: number | null
  authentic_probability?: number | null
  mask_tamper_ratio?: number | null
  localization_override?: boolean
  input_height?: number | null
  input_width?: number | null
  mask_height?: number | null
  mask_width?: number | null
}

export interface DetectionRecord {
  id: number
  created_at: string
  mode: string
  preset: string
  source_filename: string
  ok: boolean
  error_message?: string | null
  image_class_index?: number | null
  fake_probability?: number | null
  authentic_probability?: number | null
  mask_tamper_ratio?: number | null
  localization_override?: boolean
  input_height?: number | null
  input_width?: number | null
  mask_height?: number | null
  mask_width?: number | null
}

export interface DetectionListResult {
  total: number
  page: number
  page_size: number
  items: DetectionRecord[]
}

export function buildDetectionLogItem(
  mode: DetectionMode,
  preset: string,
  sourceFilename: string,
  pred: FldcfPredictResponse | null | undefined,
  ok: boolean,
  errorMessage?: string | null,
): DetectionCreateItem {
  if (!ok || !pred) {
    return {
      mode,
      preset,
      source_filename: sourceFilename,
      ok: false,
      error_message: errorMessage ?? '推理失败',
      localization_override: false,
    }
  }
  return {
    mode,
    preset,
    source_filename: sourceFilename,
    ok: true,
    image_class_index: pred.image_class_index,
    fake_probability: pred.fake_probability,
    authentic_probability: pred.authentic_probability,
    mask_tamper_ratio: pred.mask_tamper_ratio,
    localization_override: pred.localization_override,
    input_height: pred.input_height,
    input_width: pred.input_width,
    mask_height: pred.mask_height,
    mask_width: pred.mask_width,
  }
}

export const detectionApi = {
  create(item: DetectionCreateItem) {
    return request.post('/detections', item) as Promise<DetectionRecord>
  },

  createBatch(items: DetectionCreateItem[]) {
    if (!items.length) return Promise.resolve({ created: 0 })
    return request.post('/detections/batch', { items }) as Promise<{ created: number }>
  },

  list(page = 1, pageSize = 20) {
    return request.get('/detections', {
      params: { page, page_size: pageSize },
    }) as Promise<DetectionListResult>
  },

  remove(id: number) {
    return request.delete(`/detections/${id}`) as Promise<unknown>
  },
}
