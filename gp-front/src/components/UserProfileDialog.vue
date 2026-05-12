<script setup lang="ts">
import { ref, watch, computed } from 'vue'
import { ElMessage } from 'element-plus'

import { userApi } from '@/api/user'
import { useAuthStore } from '@/stores/auth'
import { resolveAvatarUrl } from '@/utils/resolveAvatarUrl'

const props = defineProps<{ modelValue: boolean }>()
const emit = defineEmits<{ 'update:modelValue': [boolean]; saved: [] }>()

const auth = useAuthStore()

const password = ref('')
const password2 = ref('')
const loading = ref(false)

const previewBlobUrl = ref<string | null>(null)
const pendingFile = ref<File | null>(null)
const fileInputRef = ref<HTMLInputElement | null>(null)

const avatarDisplay = computed(() => {
  if (previewBlobUrl.value) return previewBlobUrl.value
  return resolveAvatarUrl(auth.user?.avatar_url)
})

const userInitials = computed(() => {
  const n = auth.user?.username?.trim()
  if (!n) return '?'
  return n.length >= 2 ? n.slice(0, 2).toUpperCase() : n.charAt(0).toUpperCase()
})

function revokePreview() {
  if (previewBlobUrl.value) {
    URL.revokeObjectURL(previewBlobUrl.value)
    previewBlobUrl.value = null
  }
}

watch(
  () => props.modelValue,
  (open) => {
    if (open) {
      revokePreview()
      pendingFile.value = null
      password.value = ''
      password2.value = ''
    }
  },
)

function onPickFile(ev: Event) {
  const input = ev.target as HTMLInputElement
  const f = input.files?.[0]
  input.value = ''
  if (!f) return
  if (!/^image\/(jpeg|png|gif|webp)$/i.test(f.type)) {
    ElMessage.error('仅支持 JPG、PNG、GIF、WebP')
    return
  }
  if (f.size > 2 * 1024 * 1024) {
    ElMessage.error('图片不超过 2MB')
    return
  }
  revokePreview()
  pendingFile.value = f
  previewBlobUrl.value = URL.createObjectURL(f)
}

/** 取消未上传的本地预览，或请求后端移除已保存的头像 */
async function removeAvatarOrClearPreview() {
  if (pendingFile.value) {
    revokePreview()
    pendingFile.value = null
    return
  }
  if (!auth.user?.avatar_url) return
  loading.value = true
  try {
    await userApi.patchMe({ avatar_url: null })
    await auth.fetchUser()
    ElMessage.success('已移除头像')
  } catch {
    /* axios */
  } finally {
    loading.value = false
  }
}

async function submit() {
  const pwdChange = Boolean(password.value || password2.value)
  if (pwdChange) {
    if (password.value !== password2.value) {
      ElMessage.error('两次输入的密码不一致')
      return
    }
    if (password.value.length < 4 || password.value.length > 20) {
      ElMessage.error('新密码长度为 4～20 位')
      return
    }
  }

  const avatarChange = Boolean(pendingFile.value)
  if (!avatarChange && !pwdChange) {
    ElMessage.info('未修改任何内容')
    emit('update:modelValue', false)
    return
  }

  loading.value = true
  try {
    if (pendingFile.value) {
      await userApi.uploadAvatar(pendingFile.value)
      revokePreview()
      pendingFile.value = null
    }
    if (pwdChange) {
      await userApi.patchMe({ password: password.value })
      password.value = ''
      password2.value = ''
    }
    await auth.fetchUser()
    ElMessage.success('保存成功')
    emit('saved')
    emit('update:modelValue', false)
  } catch {
    /* axios 拦截器已提示 */
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <el-dialog
    :model-value="modelValue"
    title="修改个人信息"
    width="440px"
    destroy-on-close
    class="user-profile-dialog"
    @update:model-value="emit('update:modelValue', $event)"
  >
    <el-form label-position="top" class="profile-form">
      <el-form-item label="用户名">
        <el-input :model-value="auth.user?.username ?? ''" disabled />
      </el-form-item>
      <el-form-item label="角色">
        <el-input :model-value="auth.user?.role ?? ''" disabled />
      </el-form-item>
      <el-form-item label="头像">
        <div class="avatar-row">
          <el-avatar class="avatar-preview" :size="72" :src="avatarDisplay">
            {{ userInitials }}
          </el-avatar>
          <div class="avatar-actions">
            <input
              ref="fileInputRef"
              class="avatar-file-input"
              type="file"
              accept="image/jpeg,image/png,image/gif,image/webp"
              @change="onPickFile"
            />
            <el-button size="small" type="primary" plain @click="fileInputRef?.click()">选择图片</el-button>
            <el-button
              size="small"
              link
              type="danger"
              :disabled="loading || (!pendingFile && !auth.user?.avatar_url)"
              @click="removeAvatarOrClearPreview"
            >
              {{ pendingFile ? '取消预览' : '移除头像' }}
            </el-button>
          </div>
        </div>
        <p class="avatar-hint">支持 JPG / PNG / GIF / WebP，最大 2MB；点击保存后上传到服务器。</p>
      </el-form-item>
      <el-form-item label="新密码（可选）">
        <el-input v-model="password" type="password" show-password placeholder="不修改请留空" autocomplete="new-password" />
      </el-form-item>
      <el-form-item label="确认新密码">
        <el-input v-model="password2" type="password" show-password placeholder="再次输入新密码" autocomplete="new-password" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="emit('update:modelValue', false)">取消</el-button>
      <el-button type="primary" :loading="loading" @click="submit">保存</el-button>
    </template>
  </el-dialog>
</template>

<style scoped>
.profile-form :deep(.el-form-item__label) {
  font-weight: 600;
  color: var(--color-text-secondary, #6b7a99);
}

.avatar-row {
  display: flex;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
}

.avatar-preview {
  flex-shrink: 0;
  border: 1px solid var(--color-border, #e5e7eb);
}

.avatar-actions {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 8px;
  position: relative;
}

.avatar-file-input {
  position: absolute;
  width: 0;
  height: 0;
  opacity: 0;
  pointer-events: none;
}

.avatar-hint {
  margin: 8px 0 0;
  font-size: 12px;
  color: var(--color-text-muted, #94a3b8);
  line-height: 1.45;
}
</style>
