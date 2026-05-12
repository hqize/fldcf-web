/**
 * 将后端返回的 avatar_url 转为可在 <img> / el-avatar 中使用的绝对地址。
 * 绝对 URL、data: URL 原样返回；以 / 开头的路径相对 VITE_API_BASE_URL（默认与 .env.development 一致）。
 */
export function resolveAvatarUrl(avatarUrl: string | null | undefined): string | undefined {
  if (!avatarUrl) return undefined
  if (
    avatarUrl.startsWith('http://') ||
    avatarUrl.startsWith('https://') ||
    avatarUrl.startsWith('data:')
  ) {
    return avatarUrl
  }
  const base = import.meta.env.VITE_API_BASE_URL || '/api'
  if (avatarUrl.startsWith('/')) {
    try {
      return new URL(avatarUrl, base.endsWith('/') ? base : `${base}/`).href
    } catch {
      return avatarUrl
    }
  }
  return avatarUrl
}
