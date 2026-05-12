<script setup lang="ts">
import { ref, onMounted, onActivated } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'

import { detectionApi, type DetectionRecord } from '@/api/detection'

const loading = ref(false)
const list = ref<DetectionRecord[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(15)

function clsLabel(idx: number | null | undefined) {
  if (idx === 0) return '伪造'
  if (idx === 1) return '真实'
  if (idx == null) return '—'
  return String(idx)
}

function formatDt(iso: string) {
  try {
    const d = new Date(iso)
    if (Number.isNaN(d.getTime())) return iso
    return d.toLocaleString('zh-CN', { hour12: false })
  } catch {
    return iso
  }
}

async function load() {
  loading.value = true
  try {
    const res = await detectionApi.list(page.value, pageSize.value)
    total.value = res.total
    list.value = res.items
  } catch {
    list.value = []
  } finally {
    loading.value = false
  }
}

async function onDelete(row: DetectionRecord) {
  try {
    await ElMessageBox.confirm(
      `确定删除记录「${row.source_filename}」？`,
      '删除确认',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' },
    )
    await detectionApi.remove(row.id)
    ElMessage.success('已删除')
    await load()
  } catch (e) {
    if (e !== 'cancel') {
      /* axios 已提示 */
    }
  }
}

function onPageChange(p: number) {
  page.value = p
  void load()
}

onMounted(() => {
  void load()
})

/** keep-alive 回到本 Tab 时拉最新列表（别处写入的新记录可见） */
onActivated(() => {
  void load()
})
</script>

<template>
  <div class="detection-history">
    <div class="dh-toolbar">
      <span class="dh-hint">以下为当前账号在服务器保存的检测摘要（不含 mask 图像；需登录）。</span>
      <el-button size="small" type="primary" plain :loading="loading" @click="load">刷新</el-button>
    </div>

    <el-table v-loading="loading" :data="list" stripe border size="small" :max-height="480" style="width: 100%">
      <el-table-column label="时间" width="178">
        <template #default="{ row }">
          {{ formatDt(row.created_at) }}
        </template>
      </el-table-column>
      <el-table-column prop="mode" label="模式" width="72">
        <template #default="{ row }">
          {{ row.mode === 'single' ? '单图' : '批量' }}
        </template>
      </el-table-column>
      <el-table-column prop="preset" label="权重" width="96" show-overflow-tooltip />
      <el-table-column prop="source_filename" label="文件名" min-width="140" show-overflow-tooltip />
      <el-table-column label="分类" width="72">
        <template #default="{ row }">
          <span v-if="row.ok">{{ clsLabel(row.image_class_index) }}</span>
          <span v-else class="dh-muted">—</span>
        </template>
      </el-table-column>
      <el-table-column label="伪造%" width="88">
        <template #default="{ row }">
          <span v-if="row.ok && row.fake_probability != null">{{ (row.fake_probability * 100).toFixed(2) }}</span>
          <span v-else class="dh-muted">—</span>
        </template>
      </el-table-column>
      <el-table-column label="真实%" width="88">
        <template #default="{ row }">
          <span v-if="row.ok && row.authentic_probability != null">{{ (row.authentic_probability * 100).toFixed(2) }}</span>
          <span v-else class="dh-muted">—</span>
        </template>
      </el-table-column>
      <el-table-column label="篡改占比%" width="96">
        <template #default="{ row }">
          <span v-if="row.ok && row.mask_tamper_ratio != null">{{ (row.mask_tamper_ratio * 100).toFixed(3) }}</span>
          <span v-else class="dh-muted">—</span>
        </template>
      </el-table-column>
      <el-table-column label="状态" width="88">
        <template #default="{ row }">
          <span v-if="row.ok" class="dh-ok">成功</span>
          <span v-else class="dh-err" :title="row.error_message ?? ''">失败</span>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="88" fixed="right">
        <template #default="{ row }">
          <el-button link type="danger" size="small" @click="onDelete(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <div class="dh-pagination">
      <el-pagination
        :current-page="page"
        :page-size="pageSize"
        :total="total"
        layout="total, prev, pager, next"
        small
        background
        @current-change="onPageChange"
      />
    </div>
  </div>
</template>

<style scoped>
.detection-history {
  width: 100%;
  max-width: 1200px;
}

.dh-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 14px;
  flex-wrap: wrap;
}

.dh-hint {
  font-size: 13px;
  color: var(--color-text-secondary, #6b7a99);
  line-height: 1.5;
}

.dh-muted {
  color: var(--color-text-muted, #94a3b8);
}

.dh-ok {
  color: var(--color-success, #16a34a);
  font-weight: 600;
}

.dh-err {
  color: var(--color-danger, #dc2626);
  font-size: 12px;
}

.dh-pagination {
  display: flex;
  justify-content: flex-end;
  margin-top: 14px;
}
</style>
