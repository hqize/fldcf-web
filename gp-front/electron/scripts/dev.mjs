/**
 * electron:dev —— 同时拉起 Vite 开发服务器与 Electron（零新增依赖，替代 concurrently+wait-on）。
 *
 *  1. 用系统 Node 启动 vite（--strictPort 固定 5173，被占用则快速失败）
 *  2. 轮询等待 Vite 就绪
 *  3. 以 VITE_DEV_SERVER_URL=http://localhost:5173 启动 Electron（主进程据此加载 dev server，不启用代理）
 *  4. 任一进程退出时清理另一方
 */
import { spawn } from 'node:child_process'
import { createRequire } from 'node:module'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const require = createRequire(import.meta.url)
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', '..')

const VITE_PORT = 5173
const DEV_URL = `http://localhost:${VITE_PORT}`

const viteBin = path.join(root, 'node_modules', 'vite', 'bin', 'vite.js')
const vite = spawn(process.execPath, [viteBin, '--port', String(VITE_PORT), '--strictPort'], {
  cwd: root,
  stdio: 'inherit',
})

let electronProc = null
let done = false

function cleanup(code = 0) {
  if (done) return
  done = true
  if (electronProc && !electronProc.killed) electronProc.kill()
  if (!vite.killed) vite.kill()
  process.exit(code)
}

process.on('SIGINT', () => cleanup(0))
process.on('SIGTERM', () => cleanup(0))

// Vite 在 Electron 启动前就退出（如端口被占）——直接报错收尾
vite.on('exit', (code, signal) => {
  if (!electronProc) {
    console.error(`Vite 开发服务器提前退出（code=${code} signal=${signal}），端口 ${VITE_PORT} 是否被占用？`)
    cleanup(1)
  }
})

// 从普通 Node 中 require('electron') 返回的是 electron 可执行文件路径
const electronBin = require('electron')

async function waitForReady(url, timeoutMs = 30000) {
  const start = Date.now()
  while (Date.now() - start < timeoutMs) {
    try {
      const res = await fetch(url)
      if (res.status < 500) return
    } catch {
      /* 尚未就绪 */
    }
    await new Promise((r) => setTimeout(r, 200))
  }
  throw new Error(`Vite 开发服务器未在 ${url} 按时启动`)
}

// 防御：某些机器全局设置了 ELECTRON_RUN_AS_NODE=1，会让 electron.exe 以纯 Node 模式启动、
// 不再加载 GUI。开发脚本里显式剔除，保证 electron:dev 可用。
const childEnv = { ...process.env, VITE_DEV_SERVER_URL: DEV_URL }
delete childEnv.ELECTRON_RUN_AS_NODE

waitForReady(DEV_URL)
  .then(() => {
    electronProc = spawn(electronBin, ['.'], {
      cwd: root,
      stdio: 'inherit',
      env: childEnv,
    })
    electronProc.on('exit', (code) => cleanup(code ?? 0))
    electronProc.on('error', (err) => {
      console.error('Electron 启动失败:', err)
      cleanup(1)
    })
  })
  .catch((err) => {
    console.error(err.message)
    cleanup(1)
  })
