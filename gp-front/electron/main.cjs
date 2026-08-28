'use strict'

const { app, BrowserWindow } = require('electron')
const path = require('node:path')

// ============ 部署配置（只改这一处） ============
// 工作流：先启动后端（uvicorn 8000）和前端（npm run dev，vite 5173），
// 再启动 Electron，窗口即加载下面的地址连上前端。
// 默认指向本地前端开发服务器；若前端跑在别处（如 nginx/服务器），改成对应地址即可。
// 也可以用环境变量 APP_URL 覆盖（无需改代码）。
const APP_URL = process.env.APP_URL || 'http://localhost:5173/'

const DEV_SERVER_URL = process.env.VITE_DEV_SERVER_URL // 仅由 electron:dev 注入

const gotLock = app.requestSingleInstanceLock()
if (!gotLock) {
  app.quit()
} else {
  let mainWindow = null

  const createWindow = () => {
    mainWindow = new BrowserWindow({
      width: 1280,
      height: 800,
      minWidth: 960,
      minHeight: 640,
      autoHideMenuBar: true,
      backgroundColor: '#f5f7fa',
      icon: path.join(app.getAppPath(), 'build', 'icon.ico'),
      webPreferences: {
        preload: path.join(__dirname, 'preload.cjs'),
        contextIsolation: true,
        nodeIntegration: false,
        sandbox: true,
      },
    })

    mainWindow.once('ready-to-show', () => mainWindow.show())
    mainWindow.on('closed', () => {
      mainWindow = null
    })

    // 服务器连不上时显示友好提示，避免裸奔的 ERR_CONNECTION_REFUSED 页面
    mainWindow.webContents.on(
      'did-fail-load',
      (_event, errorCode, errorDescription, validatedURL, isMainFrame) => {
        if (!isMainFrame || errorCode === -3) return // -3 = 页面内跳转被中止，忽略
        mainWindow.loadURL(
          'data:text/html;charset=utf-8,' +
            encodeURIComponent(
              `<h3 style="font-family:sans-serif">无法连接服务器</h3>` +
                `<p style="font-family:sans-serif">${errorDescription}（${errorCode}）</p>` +
                `<p style="font-family:sans-serif">${validatedURL}</p>`,
            ),
        )
      },
    )

    mainWindow.loadURL(DEV_SERVER_URL || APP_URL)
  }

  app.whenReady().then(createWindow)

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow()
  })

  app.on('second-instance', () => {
    if (mainWindow) {
      if (mainWindow.isMinimized()) mainWindow.restore()
      mainWindow.focus()
    }
  })

  app.on('window-all-closed', () => app.quit())
}
