// electron-main.js - DocuMancer Main Process
// Secure, production-ready Electron application with full IPC communication

const { app, BrowserWindow, ipcMain, dialog, shell, Menu, nativeTheme } = require('electron');
const path = require('path');
const { spawn } = require('child_process');
const fs = require('fs');
const os = require('os');

// Application constants
const APP_NAME = 'DocuMancer';
const APP_VERSION = '2.1.0';
const IS_DEV = process.env.NODE_ENV === 'development';
const IS_MAC = process.platform === 'darwin';
const IS_WIN = process.platform === 'win32';

// Path configuration
const BACKEND_DIR = path.join(__dirname, '..', 'backend');
const CONVERTER_SCRIPT = path.join(BACKEND_DIR, 'converter.py');
const OUTPUT_DIR = path.join(os.homedir(), 'DocuMancer_Output');

// Window state
let mainWindow = null;
let converterProcess = null;

/**
 * Get the appropriate Python executable path
 * @returns {string} Path to Python executable
 */
function getPythonPath() {
    const pythonPaths = IS_WIN
        ? ['python', 'python3', 'py']
        : ['python3', 'python'];

    for (const pythonPath of pythonPaths) {
        try {
            const result = require('child_process').spawnSync(pythonPath, ['--version']);
            if (result.status === 0) {
                return pythonPath;
            }
        } catch (e) {
            continue;
        }
    }
    return 'python3'; // Fallback
}

/**
 * Ensure output directory exists
 */
function ensureOutputDir() {
    if (!fs.existsSync(OUTPUT_DIR)) {
        fs.mkdirSync(OUTPUT_DIR, { recursive: true });
    }
    return OUTPUT_DIR;
}

/**
 * Create the main application window with security best practices
 */
function createWindow() {
    // Get display dimensions for proper sizing
    const { screen } = require('electron');
    const primaryDisplay = screen.getPrimaryDisplay();
    const { width: screenWidth, height: screenHeight } = primaryDisplay.workAreaSize;

    // Calculate optimal window size (80% of screen, capped)
    const windowWidth = Math.min(1200, Math.floor(screenWidth * 0.8));
    const windowHeight = Math.min(800, Math.floor(screenHeight * 0.8));

    mainWindow = new BrowserWindow({
        width: windowWidth,
        height: windowHeight,
        minWidth: 600,
        minHeight: 500,
        transparent: true,
        frame: false,
        show: false,
        backgroundColor: '#00000000',
        titleBarStyle: 'hiddenInset',
        trafficLightPosition: { x: 15, y: 15 },
        webPreferences: {
            preload: path.join(__dirname, 'preload.js'),
            nodeIntegration: false,           // Security: Disabled
            contextIsolation: true,           // Security: Enabled
            enableRemoteModule: false,        // Security: Disabled
            sandbox: true,                    // Security: Sandboxed renderer
            webSecurity: true,                // Security: Web security enabled
            allowRunningInsecureContent: false,
            experimentalFeatures: false
        }
    });

    // Load the main HTML file
    mainWindow.loadFile(path.join(__dirname, 'index.html'));

    // Show window when ready to prevent visual flash
    mainWindow.once('ready-to-show', () => {
        mainWindow.show();
        if (IS_DEV) {
            mainWindow.webContents.openDevTools({ mode: 'detach' });
        }
    });

    // Handle window closed
    mainWindow.on('closed', () => {
        mainWindow = null;
        // Clean up any running converter process
        if (converterProcess) {
            converterProcess.kill();
            converterProcess = null;
        }
    });

    // Prevent navigation to external URLs
    mainWindow.webContents.on('will-navigate', (event, url) => {
        if (!url.startsWith('file://')) {
            event.preventDefault();
            shell.openExternal(url);
        }
    });

    // Prevent new window creation
    mainWindow.webContents.setWindowOpenHandler(({ url }) => {
        shell.openExternal(url);
        return { action: 'deny' };
    });

    // Create application menu
    createApplicationMenu();
}

/**
 * Create the application menu
 */
function createApplicationMenu() {
    const template = [
        ...(IS_MAC ? [{
            label: APP_NAME,
            submenu: [
                { role: 'about' },
                { type: 'separator' },
                { role: 'services' },
                { type: 'separator' },
                { role: 'hide' },
                { role: 'hideOthers' },
                { role: 'unhide' },
                { type: 'separator' },
                { role: 'quit' }
            ]
        }] : []),
        {
            label: 'File',
            submenu: [
                {
                    label: 'Open Files...',
                    accelerator: 'CmdOrCtrl+O',
                    click: async () => {
                        const result = await openFileDialog();
                        if (result.length > 0 && mainWindow) {
                            mainWindow.webContents.send('files-selected', result);
                        }
                    }
                },
                {
                    label: 'Open Output Folder',
                    accelerator: 'CmdOrCtrl+Shift+O',
                    click: () => {
                        ensureOutputDir();
                        shell.openPath(OUTPUT_DIR);
                    }
                },
                { type: 'separator' },
                IS_MAC ? { role: 'close' } : { role: 'quit' }
            ]
        },
        {
            label: 'Edit',
            submenu: [
                { role: 'undo' },
                { role: 'redo' },
                { type: 'separator' },
                { role: 'cut' },
                { role: 'copy' },
                { role: 'paste' },
                { role: 'selectAll' }
            ]
        },
        {
            label: 'View',
            submenu: [
                { role: 'reload' },
                { role: 'forceReload' },
                { role: 'toggleDevTools' },
                { type: 'separator' },
                { role: 'resetZoom' },
                { role: 'zoomIn' },
                { role: 'zoomOut' },
                { type: 'separator' },
                { role: 'togglefullscreen' }
            ]
        },
        {
            label: 'Window',
            submenu: [
                { role: 'minimize' },
                { role: 'zoom' },
                ...(IS_MAC ? [
                    { type: 'separator' },
                    { role: 'front' },
                    { type: 'separator' },
                    { role: 'window' }
                ] : [
                    { role: 'close' }
                ])
            ]
        },
        {
            label: 'Help',
            submenu: [
                {
                    label: 'About DocuMancer',
                    click: () => {
                        dialog.showMessageBox(mainWindow, {
                            type: 'info',
                            title: 'About DocuMancer',
                            message: `DocuMancer v${APP_VERSION}`,
                            detail: 'Advanced Document to AI-Optimized JSON Converter\n\nSupported formats: PDF, DOCX, TXT, EPUB, Images\n\n© 2024 DocuMancer'
                        });
                    }
                },
                {
                    label: 'Check for Updates...',
                    click: () => {
                        shell.openExternal('https://github.com/documancer/releases');
                    }
                }
            ]
        }
    ];

    const menu = Menu.buildFromTemplate(template);
    Menu.setApplicationMenu(menu);
}

/**
 * Open file dialog and return selected file paths
 * @returns {Promise<string[]>} Array of selected file paths
 */
async function openFileDialog() {
    const result = await dialog.showOpenDialog(mainWindow, {
        title: 'Select Documents to Convert',
        properties: ['openFile', 'multiSelections'],
        filters: [
            { name: 'All Supported', extensions: ['pdf', 'docx', 'doc', 'txt', 'epub', 'png', 'jpg', 'jpeg', 'tiff', 'bmp', 'gif'] },
            { name: 'PDF Documents', extensions: ['pdf'] },
            { name: 'Word Documents', extensions: ['docx', 'doc'] },
            { name: 'Text Files', extensions: ['txt'] },
            { name: 'EPUB Books', extensions: ['epub'] },
            { name: 'Images (OCR)', extensions: ['png', 'jpg', 'jpeg', 'tiff', 'bmp', 'gif'] }
        ]
    });

    return result.canceled ? [] : result.filePaths;
}

/**
 * Convert files using the Python backend
 * @param {string[]} filePaths - Array of file paths to convert
 */
async function convertFiles(filePaths) {
    if (!filePaths || filePaths.length === 0) {
        mainWindow.webContents.send('conversion-error', {
            message: 'No files selected for conversion',
            code: 'NO_FILES'
        });
        return;
    }

    // Verify converter script exists
    if (!fs.existsSync(CONVERTER_SCRIPT)) {
        mainWindow.webContents.send('conversion-error', {
            message: `Converter script not found at: ${CONVERTER_SCRIPT}`,
            code: 'CONVERTER_NOT_FOUND'
        });
        return;
    }

    // Ensure output directory exists
    const outputDir = ensureOutputDir();

    // Get Python path
    const pythonPath = getPythonPath();

    // Build arguments
    const args = [
        CONVERTER_SCRIPT,
        '--output-dir', outputDir,
        '--format', 'json',
        ...filePaths
    ];

    // Notify renderer that conversion is starting
    mainWindow.webContents.send('conversion-started', {
        files: filePaths,
        total: filePaths.length,
        outputDir: outputDir
    });

    try {
        converterProcess = spawn(pythonPath, args, {
            cwd: BACKEND_DIR,
            env: { ...process.env, PYTHONUNBUFFERED: '1' }
        });

        let stdout = '';
        let stderr = '';

        converterProcess.stdout.on('data', (data) => {
            const text = data.toString();
            stdout += text;

            // Parse progress updates from Python output
            const lines = text.split('\n');
            for (const line of lines) {
                if (line.includes('Processing:')) {
                    const match = line.match(/Processing:\s*(\d+)%\s*\((\d+)\/(\d+)\)/);
                    if (match) {
                        mainWindow.webContents.send('conversion-progress', {
                            percentage: parseInt(match[1]),
                            current: parseInt(match[2]),
                            total: parseInt(match[3]),
                            message: line
                        });
                    }
                } else if (line.includes('INFO -')) {
                    mainWindow.webContents.send('conversion-progress', {
                        message: line.replace(/.*INFO - /, '')
                    });
                } else if (line.includes('Converted:')) {
                    const match = line.match(/Converted:\s*(.+?)\s*->\s*(.+)/);
                    if (match) {
                        mainWindow.webContents.send('file-converted', {
                            input: match[1].trim(),
                            output: match[2].trim()
                        });
                    }
                }
            }
        });

        converterProcess.stderr.on('data', (data) => {
            const text = data.toString();
            stderr += text;

            // Log warnings but don't treat all stderr as errors
            if (text.includes('WARNING')) {
                mainWindow.webContents.send('conversion-warning', {
                    message: text
                });
            }
        });

        converterProcess.on('close', (code) => {
            converterProcess = null;

            if (code === 0) {
                mainWindow.webContents.send('conversion-complete', {
                    success: true,
                    outputDir: outputDir,
                    message: `Successfully converted ${filePaths.length} file(s)`,
                    files: filePaths
                });
            } else {
                mainWindow.webContents.send('conversion-error', {
                    message: `Conversion failed with exit code ${code}`,
                    code: 'CONVERSION_FAILED',
                    details: stderr || stdout
                });
            }
        });

        converterProcess.on('error', (error) => {
            converterProcess = null;
            mainWindow.webContents.send('conversion-error', {
                message: `Failed to start converter: ${error.message}`,
                code: 'SPAWN_ERROR',
                details: error.toString()
            });
        });

    } catch (error) {
        mainWindow.webContents.send('conversion-error', {
            message: `Conversion error: ${error.message}`,
            code: 'UNKNOWN_ERROR',
            details: error.stack
        });
    }
}

/**
 * Cancel an ongoing conversion
 */
function cancelConversion() {
    if (converterProcess) {
        converterProcess.kill('SIGTERM');
        converterProcess = null;
        mainWindow.webContents.send('conversion-cancelled', {
            message: 'Conversion cancelled by user'
        });
        return true;
    }
    return false;
}

// ==================== IPC HANDLERS ====================

// Handle file dialog request
ipcMain.handle('open-file-dialog', async () => {
    return await openFileDialog();
});

// Handle file conversion request
ipcMain.on('convert-files', (event, filePaths) => {
    convertFiles(filePaths);
});

// Handle select files (alias for file dialog + convert)
ipcMain.on('select-files', async (event) => {
    const files = await openFileDialog();
    if (files.length > 0) {
        event.reply('files-selected', files);
    }
});

// Handle conversion cancellation
ipcMain.on('cancel-conversion', () => {
    cancelConversion();
});

// Handle window control requests
ipcMain.on('window-minimize', () => {
    if (mainWindow) mainWindow.minimize();
});

ipcMain.on('window-maximize', () => {
    if (mainWindow) {
        if (mainWindow.isMaximized()) {
            mainWindow.unmaximize();
        } else {
            mainWindow.maximize();
        }
    }
});

ipcMain.on('window-close', () => {
    if (mainWindow) mainWindow.close();
});

// Handle open output folder request
ipcMain.on('open-output-folder', () => {
    const dir = ensureOutputDir();
    shell.openPath(dir);
});

// Handle open file in default application
ipcMain.on('open-file', (event, filePath) => {
    if (fs.existsSync(filePath)) {
        shell.openPath(filePath);
    }
});

// Handle reveal file in file manager
ipcMain.on('reveal-file', (event, filePath) => {
    if (fs.existsSync(filePath)) {
        shell.showItemInFolder(filePath);
    }
});

// Get application info
ipcMain.handle('get-app-info', () => {
    return {
        name: APP_NAME,
        version: APP_VERSION,
        outputDir: OUTPUT_DIR,
        platform: process.platform,
        arch: process.arch
    };
});

// Get system theme
ipcMain.handle('get-system-theme', () => {
    return nativeTheme.shouldUseDarkColors ? 'dark' : 'light';
});

// ==================== APPLICATION LIFECYCLE ====================

// App ready
app.whenReady().then(() => {
    createWindow();

    // macOS: Re-create window when dock icon clicked and no windows exist
    app.on('activate', () => {
        if (BrowserWindow.getAllWindows().length === 0) {
            createWindow();
        }
    });
});

// Quit when all windows are closed (except on macOS)
app.on('window-all-closed', () => {
    if (!IS_MAC) {
        app.quit();
    }
});

// Clean up before quit
app.on('before-quit', () => {
    if (converterProcess) {
        converterProcess.kill();
    }
});

// Handle certificate errors in production
app.on('certificate-error', (event, webContents, url, error, certificate, callback) => {
    event.preventDefault();
    // In production, reject untrusted certificates
    callback(false);
});

// Disable navigation to remote URLs for security
app.on('web-contents-created', (event, contents) => {
    contents.on('will-navigate', (event, navigationUrl) => {
        const parsedUrl = new URL(navigationUrl);
        if (parsedUrl.protocol !== 'file:') {
            event.preventDefault();
        }
    });
});

// Export for testing
module.exports = {
    createWindow,
    openFileDialog,
    convertFiles,
    cancelConversion
};
