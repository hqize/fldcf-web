<script setup lang="ts">
import {
  computed,
  inject,
  nextTick,
  onBeforeUnmount,
  onMounted,
  ref,
  watch,
} from 'vue'

import type { ImageInstance } from 'element-plus'

import { storeToRefs } from 'pinia'

import { buildDetectionLogItem, detectionApi } from '@/api/detection'
import {
  fldcfApi,
  type FldcfPreset,
  type FldcfPredictResponse,
  type FldcfStatusResponse,
  preferenceToUseCpuQuery,
} from '@/api/fldcf'
import { useFldcfPrefsStore } from '@/stores/fldcfPrefs'
import { echartsKey, type EChartsOption } from '@/plugins/echarts'

const _echarts = inject(echartsKey)
if (!_echarts) {
  throw new Error('FldcfApi: echarts 未在应用入口 provide，请检查 main.ts')
}
const echarts = _echarts

/** 命名插槽 mask / json / echart 的 props（父组件可覆盖默认 UI） */
interface FldcfSlotProps {
  prediction: FldcfPredictResponse | null
  previewUrl: string
  maskDataUrl: string
  jsonText: string
  loading: boolean
  preset: FldcfPreset
}

const fldcfPrefs = useFldcfPrefsStore()
const { preset, devicePreference } = storeToRefs(fldcfPrefs)
const fldcfStatus = ref<FldcfStatusResponse | null>(null)
/** 最近一次推理的文件名（用于写入检测历史） */
const lastSourceFilename = ref('')
const loading = ref(false)
const errorMsg = ref('')
const jsonText = ref('')
const maskDataUrl = ref('')
const previewUrl = ref('')
const prediction = ref<FldcfPredictResponse | null>(null)

const activeOutputTab = ref<'mask' | 'json' | 'echart'>('mask')

const chartElRef = ref<HTMLDivElement | null>(null)
let chartInstance: echarts.ECharts | null = null
/** 图表已 setOption，用于下载按钮；plain let 非响应式，需配合 ref */
const chartReady = ref(false)

const slotProps = computed<FldcfSlotProps>(() => ({
  prediction: prediction.value,
  previewUrl: previewUrl.value,
  maskDataUrl: maskDataUrl.value,
  jsonText: jsonText.value,
  loading: loading.value,
  preset: preset.value,
}))

const cudaAvailable = computed(() => fldcfStatus.value?.cuda_available ?? false)

const summary = computed(() => {
  if (!prediction.value) return ''
  const j = prediction.value
  const cls =
    j.image_class_index === 0 ? '伪造(0)' : j.image_class_index === 1 ? '真实(1)' : String(j.image_class_index)
  const loc = j.localization_override ? ' | 已按定位覆盖为伪造' : ''
  const dev = j.inference_device ? ` | 设备: ${j.inference_device}` : ''
  return `伪造概率: ${(j.fake_probability * 100).toFixed(2)}% | 真实概率: ${(j.authentic_probability * 100).toFixed(2)}% | 分类: ${cls}${loc} | 篡改像素占比: ${(j.mask_tamper_ratio * 100).toFixed(3)}%${dev}`
})

const hasResult = computed(() => Boolean(prediction.value && jsonText.value))

const inputPreviewList = computed(() => (previewUrl.value ? [previewUrl.value] : []))
const maskPreviewList = computed(() => (maskDataUrl.value ? [maskDataUrl.value] : []))

const inputImageRef = ref<ImageInstance>()
const maskImageRef = ref<ImageInstance>()

function openInputPreview() {
  inputImageRef.value?.showPreview()
}

function openMaskPreview() {
  maskImageRef.value?.showPreview()
}

const canDownload = computed(() => {
  if (!hasResult.value) return false
  if (activeOutputTab.value === 'mask') return Boolean(maskDataUrl.value)
  if (activeOutputTab.value === 'json') return Boolean(jsonText.value)
  return Boolean(prediction.value && chartReady.value)
})

function resizeChart() {
  chartInstance?.resize()
}

function buildChartOption(p: FldcfPredictResponse): EChartsOption {
  return {
    tooltip: {
      trigger: 'item',
      formatter: (params: unknown) => {
        const x = params as { name: string; value: number; percent: number }
        return `${x.name}<br/>占比：${(x.value * 100).toFixed(2)}%（扇区 ${x.percent.toFixed(1)}%）`
      },
    },
    legend: {
      orient: 'horizontal',
      bottom: 6,
      left: 'center',
      itemWidth: 12,
      itemHeight: 12,
      textStyle: { fontSize: 11 },
    },
    series: [
      {
        type: 'pie',
        radius: ['36%', '58%'],
        center: ['50%', '46%'],
        avoidLabelOverlap: true,
        itemStyle: {
          borderRadius: 6,
          borderColor: '#fff',
          borderWidth: 2,
        },
        label: {
          formatter: '{b}\n{d}%',
          fontSize: 11,
        },
        emphasis: {
          itemStyle: {
            shadowBlur: 10,
            shadowOffsetX: 0,
            shadowColor: 'rgba(0, 0, 0, 0.18)',
          },
        },
        data: [
          { value: p.fake_probability, name: '伪造', itemStyle: { color: '#ef4444' } },
          { value: p.authentic_probability, name: '真实', itemStyle: { color: '#22c55e' } },
        ],
      },
    ],
  }
}

function renderOrUpdateChart() {
  const p = prediction.value
  const el = chartElRef.value
  if (!p || !el) {
    chartReady.value = false
    return
  }
  if (!chartInstance) {
    chartInstance = echarts.init(el)
  }
  chartInstance.setOption(buildChartOption(p), true)
  chartReady.value = true
  nextTick(() => resizeChart())
}

watch(prediction, (val) => {
  if (!val) {
    chartInstance?.dispose()
    chartInstance = null
    chartReady.value = false
  }
})

async function refreshFldcfStatus() {
  try {
    fldcfStatus.value = await fldcfApi.getStatus(
      preset.value,
      preferenceToUseCpuQuery(devicePreference.value),
    )
  } catch {
    fldcfStatus.value = null
  }
}

watch(preset, () => {
  void refreshFldcfStatus()
})

watch(devicePreference, () => {
  void refreshFldcfStatus()
})

watch(
  [prediction, activeOutputTab],
  async () => {
    if (activeOutputTab.value !== 'echart' || !prediction.value) return
    await nextTick()
    renderOrUpdateChart()
  },
  { flush: 'post' },
)

watch(chartElRef, () => {
  if (activeOutputTab.value === 'echart' && prediction.value) {
    nextTick(() => renderOrUpdateChart())
  }
})

let onWinResize: (() => void) | null = null

onMounted(() => {
  onWinResize = () => resizeChart()
  window.addEventListener('resize', onWinResize)
  void refreshFldcfStatus()
})

onBeforeUnmount(() => {
  if (onWinResize) window.removeEventListener('resize', onWinResize)
  chartInstance?.dispose()
  chartInstance = null
  chartReady.value = false
})

async function onFileChange(ev: Event) {
  const input = ev.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = ''
  if (!file) return
  lastSourceFilename.value = file.name

  const prevPreview = previewUrl.value
  if (prevPreview) URL.revokeObjectURL(prevPreview)

  errorMsg.value = ''
  jsonText.value = ''
  maskDataUrl.value = ''
  prediction.value = null
  chartReady.value = false
  chartInstance?.dispose()
  chartInstance = null

  previewUrl.value = URL.createObjectURL(file)

  loading.value = true
  try {
    const pred = await fldcfApi.predict(
      file,
      preset.value,
      preferenceToUseCpuQuery(devicePreference.value),
    )
    prediction.value = pred
    jsonText.value = JSON.stringify(pred, null, 2)
    maskDataUrl.value = `data:image/png;base64,${pred.mask_png_base64}`
    activeOutputTab.value = 'mask'
    void detectionApi
      .create(
        buildDetectionLogItem('single', preset.value, lastSourceFilename.value || file.name, pred, true),
      )
      .catch(() => {})
  } catch (e) {
    errorMsg.value = e instanceof Error ? e.message : String(e)
    prediction.value = null
  } finally {
    loading.value = false
  }
}

function triggerFileInput() {
  document.getElementById('fldcf-file-input')?.click()
}

function downloadBlob(filename: string, mime: string, data: BlobPart) {
  const blob = new Blob([data], { type: mime })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}

function downloadCurrent() {
  if (!hasResult.value) return
  const ts = new Date().toISOString().slice(0, 19).replace(/[:T]/g, '-')
  if (activeOutputTab.value === 'mask' && maskDataUrl.value) {
    const a = document.createElement('a')
    a.href = maskDataUrl.value
    a.download = `fldcf-mask_${ts}.png`
    a.click()
    return
  }
  if (activeOutputTab.value === 'json' && jsonText.value) {
    downloadBlob(`fldcf-result_${ts}.json`, 'application/json', jsonText.value)
    return
  }
  if (activeOutputTab.value === 'echart' && prediction.value) {
    void nextTick(() => {
      renderOrUpdateChart()
      if (!chartInstance) return
      const url = chartInstance.getDataURL({
        type: 'png',
        pixelRatio: 2,
        backgroundColor: '#fff',
      })
      const a = document.createElement('a')
      a.href = url
      a.download = `fldcf-chart_${ts}.png`
      a.click()
    })
  }
}

const fileInputId = 'fldcf-file-input'
</script>

<template>
  <div class="fldcf-api">
    <div class="fldcf-shell">
      <!-- 左侧：输入 -->
      <section class="fldcf-panel fldcf-input-panel">
        <div class="panel-label">输入</div>
        <div class="input-controls">
          <div class="control-row">
            <span class="control-label">模型选择</span>
            <el-select
              v-model="preset"
              class="model-select"
              placeholder="选择权重线"
              :disabled="loading"
              size="default"
            >
              <el-option label="fakeV 原（Vaihingen）" value="fakeV" />
              <el-option label="fakeL 原（LoveDA）" value="fakeL" />
              <el-option label="studentV 自训练（Vaihingen）" value="studentV" />
              <el-option label="studentL 自训练（LoveDA）" value="studentL" />
            </el-select>
          </div>
          <div class="control-row">
            <span class="control-label">推理设备</span>
            <div class="device-controls">
              <el-radio-group v-model="devicePreference" size="small" :disabled="loading">
                <el-radio-button label="auto">自动</el-radio-button>
                <el-radio-button label="gpu">GPU</el-radio-button>
                <el-radio-button label="cpu">CPU</el-radio-button>
              </el-radio-group>
              <p v-if="fldcfStatus && devicePreference === 'gpu' && !cudaAvailable" class="device-hint warn">
                后端未检测到 CUDA，选择 GPU 时仍将使用 CPU 推理。
              </p>
              <p v-if="fldcfStatus" class="device-hint">
                就绪：{{ fldcfStatus.inference_ready ? '是' : '否' }} · 当前
                {{ fldcfStatus.device }} · CUDA {{ fldcfStatus.cuda_available ? '可用' : '不可用' }}
              </p>
              <p v-else class="device-hint muted">推理服务状态加载中…</p>
            </div>
          </div>
          <div class="control-row">
            <span class="control-label">图像文件</span>
            <input
              :id="fileInputId"
              type="file"
              class="visually-hidden"
              accept="image/*"
              :disabled="loading"
              @change="onFileChange"
            />
            <el-button type="primary" :loading="loading" @click="triggerFileInput">
              选择文件
            </el-button>
          </div>
        </div>
        <div class="input-preview">
          <template v-if="previewUrl">
            <div class="preview-block">
              <div class="preview-toolbar">
                <span class="preview-caption">输入预览</span>
                <el-button size="small" link type="primary" @click="openInputPreview">
                  放大查看
                </el-button>
              </div>
              <div class="preview-image-wrap">
                <el-image
                  ref="inputImageRef"
                  class="fldcf-el-image"
                  :src="previewUrl"
                  :preview-src-list="inputPreviewList"
                  fit="contain"
                  preview-teleported
                  show-progress
                />
              </div>
            </div>
          </template>
          <div v-else class="preview-empty preview-placeholder">请选择一张卫星图像</div>
        </div>
      </section>

      <!-- 右侧：输出 -->
      <section class="fldcf-panel fldcf-output-panel">
        <div class="output-head">
          <div class="panel-label">输出</div>
          <el-button size="small" type="primary" plain :disabled="!canDownload" @click="downloadCurrent">
            下载
          </el-button>
        </div>

        <div class="output-tabs">
          <el-radio-group v-model="activeOutputTab" size="small">
            <el-radio-button label="mask">mask</el-radio-button>
            <el-radio-button label="json">json</el-radio-button>
            <el-radio-button label="echart">echart</el-radio-button>
          </el-radio-group>
        </div>

        <div class="output-state" aria-live="polite">
          <p v-if="loading" class="state-msg">请求中…</p>
          <p v-else-if="errorMsg" class="state-msg err">{{ errorMsg }}</p>
          <p v-else-if="summary && !loading" class="state-msg sum">{{ summary }}</p>
        </div>

        <div class="output-body">
          <!-- mask -->
          <div v-show="activeOutputTab === 'mask'" class="tab-pane tab-pane-mask">
            <slot name="mask" v-bind="slotProps">
              <template v-if="hasResult">
                <figure v-if="maskDataUrl" class="fig fig-mask">
                  <div class="mask-toolbar">
                    <span class="fig-title">定位 mask（黑=真实，白=篡改）</span>
                    <el-button size="small" link type="primary" @click="openMaskPreview">
                      放大查看
                    </el-button>
                  </div>
                  <div class="mask-image-wrap">
                    <el-image
                      ref="maskImageRef"
                      class="fldcf-el-image"
                      :src="maskDataUrl"
                      :preview-src-list="maskPreviewList"
                      fit="contain"
                      preview-teleported
                      show-progress
                    />
                  </div>
                </figure>
              </template>
              <div v-else class="empty-out tab-empty">推理完成后在此查看 mask（原图见左侧输入预览）</div>
            </slot>
          </div>

          <!-- json -->
          <div v-show="activeOutputTab === 'json'" class="tab-pane tab-pane-json">
            <slot name="json" v-bind="slotProps">
              <pre v-if="jsonText" class="json-block">{{ jsonText }}</pre>
              <div v-else class="empty-out tab-empty">暂无 JSON，请先完成推理</div>
            </slot>
          </div>

          <!-- echart -->
          <div v-show="activeOutputTab === 'echart'" class="tab-pane tab-pane-chart">
            <slot name="echart" v-bind="slotProps">
              <div v-if="prediction" ref="chartElRef" class="chart-host" />
              <div v-else class="empty-out tab-empty">暂无图表数据，请先完成推理</div>
            </slot>
          </div>
        </div>
      </section>
    </div>
  </div>
</template>

<style scoped>
.fldcf-api {
  /* 输入/输出卡片共用上限；缩略图区域略小以保证卡片内留出标题与控件空间 */
  --fldcf-panel-max-height: min(75vh, 650px);
  --fldcf-thumb-max-h: min(34vh, 320px);
  width: 100%;
  max-width: 1400px;
  margin-left: 0;
  margin-right: auto;
}

.fldcf-shell {
  display: grid;
  grid-template-columns: minmax(420px, 560px) minmax(0, 1fr);
  gap: 16px;
  /* 与固定高度面板配合，两列同高 */
  align-items: stretch;
}

@media (max-width: 960px) {
  .fldcf-shell {
    grid-template-columns: 1fr;
  }
}

.fldcf-panel {
  box-sizing: border-box;
  width: 100%;
  border: 1px solid var(--color-border, #dde2ee);
  border-radius: 12px;
  background: var(--color-surface, #fff);
  padding: 16px 18px;
  display: flex;
  flex-direction: column;
  min-width: 0;
  min-height: 0;
  box-shadow: var(--shadow-sm, 0 1px 3px rgba(0, 0, 0, 0.06));
  /* 所有状态下输入/输出外框高度一致 */
  height: var(--fldcf-panel-max-height);
  max-height: var(--fldcf-panel-max-height);
  overflow: hidden;
}

.device-controls {
  display: flex;
  flex-direction: column;
  gap: 6px;
  align-items: flex-start;
}

.device-hint {
  margin: 0;
  font-size: 12px;
  line-height: 1.35;
  color: var(--el-text-color-secondary);
}

.device-hint.muted {
  opacity: 0.75;
}

.device-hint.warn {
  color: var(--el-color-warning);
}

.fldcf-input-panel {
  width: 100%;
}

.fldcf-output-panel {
  width: 100%;
}

.panel-label {
  font-size: 13px;
  font-weight: 700;
  color: var(--color-text-primary, #1a1f36);
  margin-bottom: 12px;
  letter-spacing: 0.06em;
}

.input-controls {
  display: flex;
  flex-direction: column;
  gap: 12px;
  flex-shrink: 0;
}

.control-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px;
}

.control-label {
  font-size: 12px;
  color: var(--color-text-secondary, #6b7a99);
  min-width: 72px;
}

.model-select {
  flex: 1;
  min-width: 260px;
}

.visually-hidden {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  border: 0;
}

.input-preview {
  flex: 1;
  min-height: 0;
  padding-top: 16px;
  margin-top: 12px;
  border-top: 1px dashed var(--color-border, #dde2ee);
  display: flex;
  flex-direction: column;
  align-items: stretch;
  gap: 8px;
  overflow-y: auto;
}

.preview-block {
  display: flex;
  flex-direction: column;
  gap: 8px;
  width: 100%;
  flex: 1;
  min-height: 0;
}

.preview-image-wrap {
  box-sizing: border-box;
  flex: 1;
  min-height: 0;
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 8px;
  border: 1px solid var(--color-border, #e5e7eb);
  overflow: hidden;
  background: var(--color-surface-2, #f9fafb);
}

.preview-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

/* el-image：禁止拉伸变形，在框内按比例缩放；根节点不占满宽以免误触布局拉伸 */
.fldcf-el-image {
  display: block;
  width: fit-content;
  max-width: 100%;
  margin: 0 auto;
}

.fldcf-el-image :deep(.el-image__wrapper) {
  width: auto !important;
  max-width: 100% !important;
  height: auto !important;
  max-height: var(--fldcf-thumb-max-h) !important;
  background: transparent !important;
}

.fldcf-el-image :deep(.el-image__inner) {
  position: relative !important;
  inset: auto !important;
  top: auto !important;
  left: auto !important;
  transform: none !important;
  width: auto !important;
  max-width: 100% !important;
  height: auto !important;
  max-height: var(--fldcf-thumb-max-h) !important;
  object-fit: contain !important;
  cursor: zoom-in;
}

.preview-caption {
  font-size: 12px;
  font-weight: 600;
  color: var(--color-text-secondary, #6b7a99);
}

.preview-empty {
  font-size: 13px;
  color: var(--color-text-muted, #a0aabf);
}

.preview-placeholder {
  flex: 1;
  min-height: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  text-align: center;
  padding: 16px;
  border-radius: 8px;
  border: 1px dashed var(--color-border, #e5e7eb);
  background: var(--color-surface-2, #f9fafb);
}

.output-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 8px;
  flex-shrink: 0;
}

.output-head .panel-label {
  margin-bottom: 0;
}

.output-tabs {
  margin-bottom: 12px;
  flex-shrink: 0;
}

.output-tabs :deep(.el-radio-group) {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.output-tabs :deep(.el-radio-button__inner) {
  font-family: var(--font-mono, ui-monospace, monospace);
  font-size: 12px;
  padding: 6px 14px;
}

.output-state {
  flex-shrink: 0;
  min-height: 40px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 4px;
}

.state-msg {
  font-size: 12px;
  margin: 0;
  flex-shrink: 0;
}

.state-msg.err {
  color: #c00;
}

.state-msg.sum {
  font-weight: 600;
  color: var(--color-text-secondary, #475569);
}

.output-body {
  flex: 1;
  min-height: 0;
  position: relative;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.tab-pane {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.tab-pane-mask {
  min-height: 0;
}

.tab-pane-json {
  min-height: 0;
  overflow: hidden;
}

.fig {
  margin: 0;
}

.fig-mask {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

.mask-image-wrap {
  box-sizing: border-box;
  flex: 1;
  min-height: 0;
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 8px;
  border: 1px solid var(--color-border, #e5e7eb);
  overflow: hidden;
  background: var(--color-surface-2, #f9fafb);
}

.mask-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 8px;
}

.fig-title {
  font-size: 12px;
  font-weight: 600;
  color: var(--color-text-muted, #94a3b8);
}

.json-block {
  flex: 1;
  min-height: 0;
  margin: 0;
  padding: 12px;
  background: var(--color-surface-2, #f6f8fa);
  border-radius: 8px;
  font-size: 11px;
  line-height: 1.45;
  overflow: auto;
  white-space: pre-wrap;
  word-break: break-word;
}

.tab-pane-chart {
  min-height: 0;
}

.chart-host {
  flex: 1;
  min-height: 240px;
  width: 100%;
}

.empty-out {
  font-size: 13px;
  color: var(--color-text-muted, #a0aabf);
}

.tab-empty {
  flex: 1;
  min-height: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  text-align: center;
  padding: 16px;
}
</style>
