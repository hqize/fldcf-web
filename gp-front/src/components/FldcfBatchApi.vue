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

import { storeToRefs } from 'pinia'

import { buildDetectionLogItem, detectionApi } from '@/api/detection'
import {
  fldcfApi,
  type FldcfPredictResponse,
  type FldcfStatusResponse,
  preferenceToUseCpuQuery,
} from '@/api/fldcf'
import { useFldcfPrefsStore } from '@/stores/fldcfPrefs'
import { echartsKey, type EChartsOption } from '@/plugins/echarts'

const _echarts = inject(echartsKey)
if (!_echarts) {
  throw new Error('FldcfBatchApi: echarts 未在应用入口 provide，请检查 main.ts')
}
const echarts = _echarts

const MAX_BATCH_FILES = 40

interface BatchRow {
  name: string
  ok: boolean
  prediction?: FldcfPredictResponse
  error?: string
}

const fldcfPrefs = useFldcfPrefsStore()
const { preset, devicePreference } = storeToRefs(fldcfPrefs)
const fldcfStatus = ref<FldcfStatusResponse | null>(null)
const loading = ref(false)
const selectedFiles = ref<File[]>([])
const results = ref<BatchRow[]>([])
const batchProgress = ref('')
const activeOutputTab = ref<'table' | 'json' | 'echart'>('table')

const chartElRef = ref<HTMLDivElement | null>(null)
let chartInstance: echarts.ECharts | null = null
const chartReady = ref(false)

const jsonText = computed(() =>
  results.value.length ? JSON.stringify(results.value, null, 2) : '',
)

const successfulPreds = computed(() =>
  results.value.filter((r) => r.ok && r.prediction).map((r) => r.prediction!),
)

const hasResult = computed(() => results.value.length > 0)

const cudaAvailable = computed(() => fldcfStatus.value?.cuda_available ?? false)

const summary = computed(() => {
  const n = results.value.length
  if (!n) return ''
  const ok = results.value.filter((r) => r.ok).length
  const fail = n - ok
  const fakeVotes = successfulPreds.value.filter((p) => p.image_class_index === 0).length
  const authVotes = successfulPreds.value.filter((p) => p.image_class_index === 1).length
  const dev = successfulPreds.value[0]?.inference_device
  const devSuffix = dev ? ` · 设备 ${dev}` : ''
  return `共 ${n} 张 · 成功 ${ok} · 失败 ${fail} · 判伪 ${fakeVotes} · 判真 ${authVotes}${devSuffix}`
})

const canDownload = computed(() => {
  if (!hasResult.value) return false
  if (activeOutputTab.value === 'table') return true
  if (activeOutputTab.value === 'json') return Boolean(jsonText.value)
  return chartReady.value && successfulPreds.value.length > 0
})

function resizeChart() {
  chartInstance?.resize()
}

function buildBatchPieOption(): EChartsOption | null {
  const preds = successfulPreds.value
  if (!preds.length) return null
  let fake = 0
  let auth = 0
  for (const p of preds) {
    if (p.image_class_index === 0) fake += 1
    else auth += 1
  }
  if (fake === 0 && auth === 0) return null
  // 不要向饼图传入 value=0 的项：双环图在「一侧为 0、一侧全满」时部分环境下整图不绘制
  const data: { value: number; name: string; itemStyle: { color: string } }[] = []
  if (fake > 0) data.push({ value: fake, name: '判伪(0)', itemStyle: { color: '#ef4444' } })
  if (auth > 0) data.push({ value: auth, name: '判真(1)', itemStyle: { color: '#22c55e' } })
  if (!data.length) return null
  return {
    tooltip: {
      trigger: 'item',
      formatter: '{b}<br/>张数：{c}（{d}%）',
    },
    legend: {
      orient: 'horizontal',
      bottom: 6,
      left: 'center',
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
        label: { formatter: '{b}\n{d}%', fontSize: 11 },
        data,
      },
    ],
  }
}

function renderOrUpdateChart() {
  const el = chartElRef.value
  const opt = buildBatchPieOption()
  if (!el || !opt) {
    chartReady.value = false
    return
  }
  if (!chartInstance) chartInstance = echarts.init(el)
  chartInstance.setOption(opt, true)
  chartReady.value = true
  nextTick(() => {
    resizeChart()
    // tab 由隐藏变为显示时首帧宽高可能仍为 0，延迟再测一次
    requestAnimationFrame(() => {
      resizeChart()
      requestAnimationFrame(() => resizeChart())
    })
  })
}

watch(
  [results, activeOutputTab],
  async () => {
    if (activeOutputTab.value !== 'echart') return
    await nextTick()
    if (!successfulPreds.value.length) {
      chartInstance?.dispose()
      chartInstance = null
      chartReady.value = false
      return
    }
    renderOrUpdateChart()
  },
  { flush: 'post' },
)

watch(chartElRef, () => {
  if (activeOutputTab.value === 'echart' && successfulPreds.value.length) {
    nextTick(() => renderOrUpdateChart())
  }
})

let onWinResize: (() => void) | null = null

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

onMounted(() => {
  onWinResize = () => resizeChart()
  window.addEventListener('resize', onWinResize)
  void refreshFldcfStatus()
})

onBeforeUnmount(() => {
  if (onWinResize) window.removeEventListener('resize', onWinResize)
  chartInstance?.dispose()
  chartInstance = null
})

const batchInputId = 'fldcf-batch-file-input'

function addFiles(files: File[]) {
  const next = [...selectedFiles.value]
  for (const f of files) {
    if (!f.type.startsWith('image/')) continue
    if (next.length >= MAX_BATCH_FILES) break
    const dup = next.some((x) => x.name === f.name && x.size === f.size)
    if (!dup) next.push(f)
  }
  selectedFiles.value = next
}

function onMultiFilePick(ev: Event) {
  const input = ev.target as HTMLInputElement
  const files = Array.from(input.files || [])
  input.value = ''
  if (!files.length) return
  addFiles(files)
}

function triggerBatchInput() {
  document.getElementById(batchInputId)?.click()
}

function removeFileAt(i: number) {
  if (loading.value) return
  selectedFiles.value = selectedFiles.value.filter((_, idx) => idx !== i)
}

function clearFiles() {
  if (loading.value) return
  selectedFiles.value = []
}

async function runBatch() {
  if (!selectedFiles.value.length || loading.value) return
  results.value = []
  loading.value = true
  const files = [...selectedFiles.value]
  const len = files.length
  try {
    let i = 0
    for (const file of files) {
      i += 1
      batchProgress.value = `${i} / ${len}`
      try {
        const prediction = await fldcfApi.predict(
          file,
          preset.value,
          preferenceToUseCpuQuery(devicePreference.value),
        )
        results.value.push({ name: file.name, ok: true, prediction })
      } catch (e) {
        const msg = e instanceof Error ? e.message : String(e)
        results.value.push({ name: file.name, ok: false, error: msg })
      }
    }
    activeOutputTab.value = 'table'
    const batchLogs = results.value.map((r) =>
      buildDetectionLogItem(
        'batch',
        preset.value,
        r.name,
        r.prediction,
        r.ok,
        r.error,
      ),
    )
    if (batchLogs.length) {
      void detectionApi.createBatch(batchLogs).catch(() => {})
    }
  } finally {
    loading.value = false
    batchProgress.value = ''
  }
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

function rowsToCsv(): string {
  const header = '文件名,分类索引,伪造概率,真实概率,篡改像素占比,是否成功,错误信息\n'
  const lines = results.value.map((r) => {
    if (!r.ok) {
      return `"${r.name.replace(/"/g, '""')}",,,,,否,"${(r.error ?? '').replace(/"/g, '""')}"`
    }
    const p = r.prediction!
    return [
      `"${r.name.replace(/"/g, '""')}"`,
      p.image_class_index,
      p.fake_probability.toFixed(6),
      p.authentic_probability.toFixed(6),
      p.mask_tamper_ratio.toFixed(6),
      '是',
      '',
    ].join(',')
  })
  return header + lines.join('\n')
}

function downloadCurrent() {
  if (!hasResult.value) return
  const ts = new Date().toISOString().slice(0, 19).replace(/[:T]/g, '-')
  if (activeOutputTab.value === 'table') {
    downloadBlob(`fldcf-batch_${ts}.csv`, 'text/csv;charset=utf-8', '\uFEFF' + rowsToCsv())
    return
  }
  if (activeOutputTab.value === 'json' && jsonText.value) {
    downloadBlob(`fldcf-batch_${ts}.json`, 'application/json', jsonText.value)
    return
  }
  if (activeOutputTab.value === 'echart' && chartInstance) {
    const url = chartInstance.getDataURL({ type: 'png', pixelRatio: 2, backgroundColor: '#fff' })
    const a = document.createElement('a')
    a.href = url
    a.download = `fldcf-batch-chart_${ts}.png`
    a.click()
  }
}

function clsLabel(idx: number) {
  if (idx === 0) return '伪造'
  if (idx === 1) return '真实'
  return String(idx)
}
</script>

<template>
  <div class="fldcf-batch">
    <div class="fldcf-shell">
      <section class="fldcf-panel fldcf-input-panel">
        <div class="panel-label">输入</div>
        <div class="input-controls">
          <div class="control-row">
            <span class="control-label">模型选择</span>
            <el-select v-model="preset" class="model-select" placeholder="选择权重线" :disabled="loading" size="default">
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
          <div class="control-row batch-actions">
            <input
              :id="batchInputId"
              type="file"
              class="visually-hidden"
              accept="image/*"
              multiple
              :disabled="loading"
              @change="onMultiFilePick"
            />
            <el-button type="primary" plain :disabled="loading" @click="triggerBatchInput">选择文件（多选）</el-button>
            <el-button type="danger" plain :disabled="loading || !selectedFiles.length" @click="clearFiles">
              清空列表
            </el-button>
          </div>
          <div class="control-row">
            <el-button type="primary" :loading="loading" :disabled="!selectedFiles.length || loading" @click="runBatch">
              开始批量检测
            </el-button>
            <span v-if="batchProgress" class="progress-hint">{{ batchProgress }}</span>
            <span class="file-limit">最多 {{ MAX_BATCH_FILES }} 张 · 当前 {{ selectedFiles.length }} 张</span>
          </div>
        </div>

        <div class="batch-file-list-wrap">
          <template v-if="selectedFiles.length">
            <ul class="batch-file-list">
              <li v-for="(f, i) in selectedFiles" :key="`${f.name}-${f.size}-${i}`" class="batch-file-item">
                <span class="batch-file-name" :title="f.name">{{ f.name }}</span>
                <el-button
                  link
                  type="danger"
                  size="small"
                  :disabled="loading"
                  @click="removeFileAt(i)"
                >
                  移除
                </el-button>
              </li>
            </ul>
          </template>
          <div v-else class="preview-placeholder batch-placeholder">请选择多张卫星图像后点击「开始批量检测」</div>
        </div>
      </section>

      <section class="fldcf-panel fldcf-output-panel">
        <div class="output-head">
          <div class="panel-label">输出</div>
          <el-button size="small" type="primary" plain :disabled="!canDownload" @click="downloadCurrent">
            下载
          </el-button>
        </div>

        <div class="output-tabs">
          <el-radio-group v-model="activeOutputTab" size="small">
            <el-radio-button label="table">列表</el-radio-button>
            <el-radio-button label="json">json</el-radio-button>
            <el-radio-button label="echart">echart</el-radio-button>
          </el-radio-group>
        </div>

        <div class="output-state" aria-live="polite">
          <p v-if="summary" class="state-msg sum">{{ summary }}</p>
        </div>

        <div class="output-body">
          <div v-show="activeOutputTab === 'table'" class="tab-pane tab-pane-table">
            <div v-if="hasResult" class="table-inner">
              <el-table
                class="batch-result-table"
                :data="results"
                stripe
                border
                size="small"
                height="100%"
                style="width: 100%"
              >
                <el-table-column prop="name" label="文件名" min-width="140" show-overflow-tooltip />
                <el-table-column label="分类" width="88">
                  <template #default="{ row }">
                    <span v-if="row.ok && row.prediction">{{ clsLabel(row.prediction.image_class_index) }}</span>
                    <span v-else class="muted">—</span>
                  </template>
                </el-table-column>
                <el-table-column label="伪造%" width="92">
                  <template #default="{ row }">
                    <span v-if="row.ok && row.prediction">{{ (row.prediction.fake_probability * 100).toFixed(2) }}</span>
                    <span v-else class="muted">—</span>
                  </template>
                </el-table-column>
                <el-table-column label="真实%" width="92">
                  <template #default="{ row }">
                    <span v-if="row.ok && row.prediction">{{ (row.prediction.authentic_probability * 100).toFixed(2) }}</span>
                    <span v-else class="muted">—</span>
                  </template>
                </el-table-column>
                <el-table-column label="篡改占比%" width="102">
                  <template #default="{ row }">
                    <span v-if="row.ok && row.prediction">{{ (row.prediction.mask_tamper_ratio * 100).toFixed(3) }}</span>
                    <span v-else class="muted">—</span>
                  </template>
                </el-table-column>
                <el-table-column label="状态" min-width="120" show-overflow-tooltip>
                  <template #default="{ row }">
                    <span v-if="row.ok" class="ok-tag">成功</span>
                    <span v-else class="err-tag">{{ row.error }}</span>
                  </template>
                </el-table-column>
              </el-table>
            </div>
            <div v-else class="empty-out tab-empty">暂无结果，请先完成批量检测</div>
          </div>

          <div v-show="activeOutputTab === 'json'" class="tab-pane tab-pane-json">
            <pre v-if="jsonText" class="json-block">{{ jsonText }}</pre>
            <div v-else class="empty-out tab-empty">暂无 JSON</div>
          </div>

          <div v-show="activeOutputTab === 'echart'" class="tab-pane tab-pane-chart">
            <div v-if="successfulPreds.length" ref="chartElRef" class="chart-host" />
            <div v-else class="empty-out tab-empty">暂无图表（需至少一张推理成功）</div>
          </div>
        </div>
      </section>
    </div>
  </div>
</template>

<style scoped>
.fldcf-batch {
  --fldcf-panel-max-height: min(75vh, 650px);
  width: 100%;
  max-width: 1400px;
  margin-left: 0;
  margin-right: auto;
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

.fldcf-shell {
  display: grid;
  grid-template-columns: minmax(420px, 560px) minmax(0, 1fr);
  gap: 16px;
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
  height: var(--fldcf-panel-max-height);
  max-height: var(--fldcf-panel-max-height);
  overflow: hidden;
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

.batch-actions {
  gap: 8px;
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

.progress-hint {
  font-size: 12px;
  font-family: var(--font-mono, ui-monospace, monospace);
  color: var(--color-accent, #2563eb);
}

.file-limit {
  font-size: 11px;
  color: var(--color-text-muted, #94a3b8);
}

.batch-file-list-wrap {
  flex: 1;
  min-height: 0;
  margin-top: 12px;
  padding-top: 16px;
  border-top: 1px dashed var(--color-border, #dde2ee);
  overflow-y: auto;
}

.batch-file-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.batch-file-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 6px 10px;
  border-radius: 8px;
  background: var(--color-surface-2, #f9fafb);
  border: 1px solid var(--color-border, #e5e7eb);
  font-size: 12px;
}

.batch-file-name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  flex: 1;
  min-width: 0;
}

.preview-placeholder,
.batch-placeholder {
  flex: 1;
  min-height: 120px;
  display: flex;
  align-items: center;
  justify-content: center;
  text-align: center;
  padding: 16px;
  font-size: 13px;
  color: var(--color-text-muted, #a0aabf);
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
  min-height: 28px;
  display: flex;
  flex-direction: column;
  justify-content: center;
}

.state-msg {
  font-size: 12px;
  margin: 0;
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

.tab-pane-table {
  min-height: 0;
}

.tab-pane-table .table-inner {
  flex: 1 1 0;
  min-height: 0;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.batch-result-table {
  flex: 1;
  min-height: 0;
}

.tab-pane-json {
  min-height: 0;
  overflow: hidden;
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

.muted {
  color: var(--color-text-muted, #94a3b8);
}

.ok-tag {
  color: var(--color-success, #16a34a);
  font-weight: 600;
}

.err-tag {
  color: var(--color-danger, #dc2626);
  font-size: 11px;
}
</style>
