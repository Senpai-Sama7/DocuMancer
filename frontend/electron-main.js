const { app, BrowserWindow, dialog, ipcMain } = require('electron')
const { spawn } = require('child_process')
const path = require('path')
const fetch = require('node-fetch')

let mainWindow
let backendProcess
const BACKEND_PORT = process.env.DOCUMANCER_BACKEND_PORT || 8000
const BACKEND_URL = `http://127.0.0.1:${BACKEND_PORT}`

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    transparent: true,
    frame: false,
    titleBarStyle: 'hiddenInset',
    show: false,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      nodeIntegration: false,
      contextIsolation: true,
      sandbox: true,
      enableRemoteModule: false
    }
  })

  mainWindow.on('closed', () => {
    mainWindow = null
  })

  mainWindow.loadFile(path.join(__dirname, 'index.html'))
  mainWindow.once('ready-to-show', () => {
    mainWindow.show()
  })
}

async function ensureBackendReady() {
  if (!backendProcess || backendProcess.killed) {
    startBackend()
  }

  const maxAttempts = 25
  const delay = 200
  for (let i = 0; i < maxAttempts; i += 1) {
    try {
      const response = await fetch(`${BACKEND_URL}/health`)
      if (response.ok) return
    } catch (err) {
      console.log(`Backend health check failed (attempt ${i + 1}/${maxAttempts}): ${err.message}`)
      // continue retrying until healthy
    }
    await new Promise(resolve => setTimeout(resolve, delay))
  }
  throw new Error('Backend service did not become ready in time')
}

function startBackend() {
  const appPath = app.getAppPath()
  const backendEntry = path.join(appPath, 'backend', 'server.py')
  
  // Determine the path to the bundled Python executable based on the platform
  const pythonExecName = process.platform === 'win32' ? 'python.exe' : 'python'
  // Assuming Python is bundled in a 'python' directory within the app resources
  const pythonExec = path.join(app.getAppPath(), '..', 'python', pythonExecName)

  // Fallback for development environment, but production should use the bundled Python
  const finalPythonExec = (app.isPackaged && require('fs').existsSync(pythonExec))
    ? pythonExec
    : 'python3'

  backendProcess = spawn(finalPythonExec, [backendEntry], {
    cwd: appPath,
    stdio: ['ignore', 'pipe', 'pipe']
  })

  backendProcess.stdout.on('data', data => {
    console.log(`[backend] ${data}`.trim())
  })

  backendProcess.stderr.on('data', data => {
    console.error(`[backend] ${data}`.trim())
  })

  backendProcess.on('exit', code => {
    console.log(`Backend process exited with code ${code}`)
  })
}

function stopBackend() {
  if (backendProcess && !backendProcess.killed) {
    backendProcess.kill('SIGTERM')
    backendProcess = null
  }
}

function registerIpcHandlers() {
  ipcMain.handle('open-file-dialog', async () => {
    const result = await dialog.showOpenDialog(mainWindow, {
      properties: ['openFile', 'multiSelections'],
      filters: [
        { name: 'Documents', extensions: ['pdf', 'docx', 'txt', 'md', 'epub'] },
        { name: 'Images', extensions: ['png', 'jpg', 'jpeg', 'tiff', 'bmp'] }
      ]
    })
    if (result.canceled) {
      return []
    }
    return result.filePaths
  })

  ipcMain.handle('convert-files', async (_event, files) => {
    if (!files || !files.length) return { results: [] }
    await ensureBackendReady()

    const response = await fetch(`${BACKEND_URL}/convert`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ files })
    })

    if (!response.ok) {
      throw new Error(`Conversion failed with status ${response.status}`)
    }

    return response.json()
  })

  ipcMain.on('window-control', (_event, action) => {
    if (!mainWindow) return
    switch (action) {
      case 'close':
        mainWindow.close()
        break
      case 'minimize':
        mainWindow.minimize()
        break
      case 'toggle-maximize':
        if (mainWindow.isMaximized()) {
          mainWindow.unmaximize()
        } else {
          mainWindow.maximize()
        }
        break
      default:
        break
    }
  })
}

function registerLifecycle() {
  app.on('before-quit', stopBackend)

  app.on('window-all-closed', () => {
    if (process.platform !== 'darwin') {
      app.quit()
    }
  })

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow()
    }
  })
}

function bootstrap() {
  const gotLock = app.requestSingleInstanceLock()
  if (!gotLock) {
    app.quit()
    return
  }

  process.on('unhandledRejection', reason => {
    console.error('Unhandled rejection:', reason)
  })
  process.on('uncaughtException', err => {
    console.error('Uncaught exception:', err)
  })

  app.whenReady().then(() => {
    createWindow()
    registerIpcHandlers()
    registerLifecycle()
  })
}

bootstrap()
