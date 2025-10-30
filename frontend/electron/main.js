/**
 * Electron主进程
 */
const { app, BrowserWindow, ipcMain } = require('electron')
const path = require('path')

// 保持对窗口对象的全局引用
let mainWindow = null

function createWindow() {
  // 创建浏览器窗口
  mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    minWidth: 1000,
    minHeight: 700,
    backgroundColor: '#f5f7fa',
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, 'preload.js')
    },
    // 使用自定义标题栏
    frame: true,
    titleBarStyle: 'default',
    show: false
  })

  // 窗口准备好后再显示，避免闪烁
  mainWindow.once('ready-to-show', () => {
    mainWindow.show()
  })

  // 加载应用
  if (process.env.VITE_DEV_SERVER_URL) {
    // 开发模式
    mainWindow.loadURL(process.env.VITE_DEV_SERVER_URL)
    // 打开开发者工具
    mainWindow.webContents.openDevTools()
  } else {
    // 生产模式
    mainWindow.loadFile(path.join(__dirname, '../dist/index.html'))
  }

  // 窗口关闭时触发
  mainWindow.on('closed', () => {
    mainWindow = null
  })
}

// 应用准备就绪时创建窗口
app.whenReady().then(() => {
  createWindow()

  app.on('activate', () => {
    // 在macOS上，当点击dock图标且没有其他窗口打开时，
    // 通常会重新创建一个窗口
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow()
    }
  })
})

// 当所有窗口都关闭时退出应用
app.on('window-all-closed', () => {
  // 在macOS上，应用通常会保持活动状态，
  // 直到用户使用Cmd + Q明确退出
  if (process.platform !== 'darwin') {
    app.quit()
  }
})

// IPC通信处理
ipcMain.handle('get-app-version', () => {
  return app.getVersion()
})

ipcMain.handle('get-app-path', () => {
  return app.getPath('userData')
})

// 最小化窗口
ipcMain.on('minimize-window', () => {
  if (mainWindow) {
    mainWindow.minimize()
  }
})

// 最大化/还原窗口
ipcMain.on('maximize-window', () => {
  if (mainWindow) {
    if (mainWindow.isMaximized()) {
      mainWindow.unmaximize()
    } else {
      mainWindow.maximize()
    }
  }
})

// 关闭窗口
ipcMain.on('close-window', () => {
  if (mainWindow) {
    mainWindow.close()
  }
})

