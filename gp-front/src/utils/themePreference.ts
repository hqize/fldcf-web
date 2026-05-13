/** 与 Pinia `theme` store、顶部开关、系统设置共用 */
const STORAGE_KEY = 'fldcf-ui-theme'

export type StoredTheme = 'dark' | 'light'

export function readStoredDark(): boolean | null {
  try {
    const v = localStorage.getItem(STORAGE_KEY)
    if (v === 'dark') return true
    if (v === 'light') return false
  } catch {
    /* ignore */
  }
  return null
}

export function saveDark(isDark: boolean) {
  try {
    localStorage.setItem(STORAGE_KEY, isDark ? 'dark' : 'light')
  } catch {
    /* ignore */
  }
}

export function applyDomTheme(isDark: boolean) {
  document.documentElement.setAttribute('data-theme', isDark ? 'dark' : '')
}
