// electron-main.js
const path = require('path')
const { app, BrowserWindow, ipcMain, dialog } = require('electron')
const { spawn } = require('child_process')

app.setName('DocuMancer')
app.setAppUserModelId('com.yourcompany.documancer')

let mainWindow
let pythonProcess

function httpRequest(pathname, { method = 'GET', headers = {}, body } = {}) {
  return new Promise((resolve, reject) => {
    const request = require('http').request(
      {
        hostname: '127.0.0.1',
        port: BACKEND_PORT,
        path: pathname,
        method,
        headers
      },
      (res) => {
        let data = ''
        res.on('data', (chunk) => {
          data += chunk
        })
        res.on('end', () => {
          resolve({ status: res.statusCode, body: data, headers: res.headers })
        })
      }
    )
    request.on('error', reject)
    if (body) {
      request.write(body)
    }
    request.end()
  })
}

process.on('unhandledRejection', (reason) => {
  console.error('Unhandled Promise rejection', reason)
})

process.on('uncaughtException', (error) => {
  console.error('Uncaught exception', error)
})

const FRONTEND_DIR = __dirname
const BACKEND_ENTRY = path.join(__dirname, '..', 'backend', 'server.py')
const BACKEND_PORT = process.env.DOCUMANCER_PORT || 4949

async function waitForHealth(retries = 20, delay = 500) {
  for (let i = 0; i < retries; i += 1) {
    try {
      const response = await httpRequest('/health')
      if (response.status === 200) return true
    } catch (err) {
      await new Promise((resolve) => setTimeout(resolve, delay))
    }
  }
  throw new Error('Backend failed health check')
}

async function ensureBackend() {
  if (pythonProcess) return
  pythonProcess = spawn('python3', [BACKEND_ENTRY], {
    env: { ...process.env, DOCUMANCER_PORT: BACKEND_PORT },
    stdio: 'inherit'
  })

  pythonProcess.on('exit', (code, signal) => {
    console.error(`Backend exited with code ${code} signal ${signal}`)
  })

  await waitForHealth()
}

async function createWindow() {
  await ensureBackend()
  mainWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    titleBarStyle: 'hiddenInset',
    frame: false,
    show: false,
    webPreferences: {
      preload: path.join(FRONTEND_DIR, 'preload.js'),
      nodeIntegration: false,
      contextIsolation: true,
      sandbox: true,
      enableRemoteModule: false
    }
  })

  mainWindow.loadFile(path.join(FRONTEND_DIR, 'index.html'))
  mainWindow.once('ready-to-show', () => {
    mainWindow.show()
  })
}

function registerIpcHandlers() {
  ipcMain.handle('open-file-dialog', async () => {
    const result = await dialog.showOpenDialog(mainWindow, {
      properties: ['openFile', 'multiSelections'],
      filters: [
        { name: 'Documents', extensions: ['pdf', 'docx', 'txt', 'epub', 'png', 'jpg', 'jpeg'] }
      ]
    })
    return result.canceled ? [] : result.filePaths
  })

  ipcMain.on('window-action', (_event, action) => {
    if (!mainWindow) return
    switch (action) {
      case 'close':
        mainWindow.close()
        break
      case 'minimize':
        mainWindow.minimize()
        break
      case 'maximize':
        if (mainWindow.isMaximized()) mainWindow.unmaximize()
        else mainWindow.maximize()
        break
      default:
        break
    }
  })

  ipcMain.handle('convert-files', async (_event, files) => {
    const payload = JSON.stringify({ files })
    const response = await httpRequest('/convert', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Content-Length': Buffer.byteLength(payload) },
      body: payload
    })

    if (response.status !== 200) {
      throw new Error(response.body || 'Conversion failed')
    }
    return JSON.parse(response.body)
  })
}

const gotTheLock = app.requestSingleInstanceLock()
if (!gotTheLock) {
  app.quit()
} else {
  app.on('second-instance', () => {
    if (mainWindow) {
      if (mainWindow.isMinimized()) mainWindow.restore()
      mainWindow.focus()
    }
  })

  app.whenReady().then(async () => {
    registerIpcHandlers()
    await createWindow()
  })
}

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit()
  }
})

app.on('before-quit', () => {
  if (pythonProcess) {
    pythonProcess.kill()
  }
})

app.on('activate', async () => {
  if (BrowserWindow.getAllWindows().length === 0) {
    await createWindow()
  }
})
