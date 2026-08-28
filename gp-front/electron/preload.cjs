'use strict'

/**
 * 最小 preload：仅暴露只读的版本/平台信息。
 * 渲染层不需要 Node/Electron 能力；未来确需 IPC 时再在此扩展。
 */
const { contextBridge } = require('electron')

contextBridge.exposeInMainWorld('fldcfApp', {
  versions: {
    electron: process.versions.electron,
    chrome: process.versions.chrome,
    node: process.versions.node,
  },
  platform: process.platform,
})
