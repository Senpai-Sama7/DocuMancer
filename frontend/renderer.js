// renderer.js - DocuMancer Frontend Application
// Complete UI management and conversion workflow

/**
 * Application State Management
 */
const AppState = {
    files: [],
    convertedFiles: [],
    isConverting: false,
    progress: 0,
    currentFile: null,
    outputDir: null,
    appInfo: null,
    theme: 'dark'
};

/**
 * DOM Element References
 */
const DOM = {
    // Will be populated after DOMContentLoaded
    titleBar: null,
    closeBtn: null,
    minimizeBtn: null,
    maximizeBtn: null,
    glassPanel: null,
    selectBtn: null,
    dropZone: null,
    fileList: null,
    progressContainer: null,
    progressBar: null,
    progressText: null,
    statusMessage: null,
    convertBtn: null,
    cancelBtn: null,
    outputSection: null,
    resultsList: null,
    openOutputBtn: null
};

/**
 * Initialize DOM references
 */
function initializeDOMReferences() {
    DOM.titleBar = document.querySelector('.title-bar');
    DOM.closeBtn = document.querySelector('.btn.close');
    DOM.minimizeBtn = document.querySelector('.btn.minimize');
    DOM.maximizeBtn = document.querySelector('.btn.maximize');
    DOM.glassPanel = document.querySelector('.glass-panel');
    DOM.selectBtn = document.querySelector('.action');
    DOM.dropZone = document.querySelector('.drop-zone');
    DOM.fileList = document.querySelector('.file-list');
    DOM.progressContainer = document.querySelector('.progress-container');
    DOM.progressBar = document.querySelector('.progress-bar');
    DOM.progressFill = document.querySelector('.progress-fill');
    DOM.progressText = document.querySelector('.progress-text');
    DOM.statusMessage = document.querySelector('.status-message');
    DOM.convertBtn = document.querySelector('.convert-btn');
    DOM.cancelBtn = document.querySelector('.cancel-btn');
    DOM.outputSection = document.querySelector('.output-section');
    DOM.resultsList = document.querySelector('.results-list');
    DOM.openOutputBtn = document.querySelector('.open-output-btn');
}

/**
 * Format file size for display
 * @param {number} bytes - File size in bytes
 * @returns {string} Formatted file size
 */
function formatFileSize(bytes) {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
}

/**
 * Get file type icon based on extension
 * @param {string} filename - File name
 * @returns {string} Icon character
 */
function getFileIcon(filename) {
    const ext = filename.split('.').pop().toLowerCase();
    const icons = {
        'pdf': '\uD83D\uDCC4',
        'docx': '\uD83D\uDCC3',
        'doc': '\uD83D\uDCC3',
        'txt': '\uD83D\uDCDD',
        'epub': '\uD83D\uDCD6',
        'png': '\uD83D\uDDBC',
        'jpg': '\uD83D\uDDBC',
        'jpeg': '\uD83D\uDDBC',
        'tiff': '\uD83D\uDDBC',
        'bmp': '\uD83D\uDDBC',
        'gif': '\uD83D\uDDBC'
    };
    return icons[ext] || '\uD83D\uDCC1';
}

/**
 * Extract filename from path
 * @param {string} filePath - Full file path
 * @returns {string} File name
 */
function getFileName(filePath) {
    return filePath.split(/[/\\]/).pop();
}

/**
 * Update the file list display
 */
function updateFileList() {
    if (!DOM.fileList) return;

    if (AppState.files.length === 0) {
        DOM.fileList.innerHTML = '<div class="empty-state">No files selected</div>';
        if (DOM.convertBtn) DOM.convertBtn.disabled = true;
        return;
    }

    DOM.fileList.innerHTML = AppState.files.map((file, index) => `
        <div class="file-item" data-index="${index}">
            <span class="file-icon">${getFileIcon(file.name || file)}</span>
            <span class="file-name">${file.name || getFileName(file)}</span>
            <span class="file-status ${file.status || 'pending'}">${file.statusText || 'Pending'}</span>
            <button class="file-remove" data-index="${index}" title="Remove file">x</button>
        </div>
    `).join('');

    // Add remove handlers
    DOM.fileList.querySelectorAll('.file-remove').forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.stopPropagation();
            const index = parseInt(btn.dataset.index);
            removeFile(index);
        });
    });

    if (DOM.convertBtn) DOM.convertBtn.disabled = false;
}

/**
 * Add files to the queue
 * @param {string[]} filePaths - Array of file paths
 */
function addFiles(filePaths) {
    const newFiles = filePaths.map(path => ({
        path: path,
        name: getFileName(path),
        status: 'pending',
        statusText: 'Pending'
    }));

    // Filter duplicates
    const existingPaths = new Set(AppState.files.map(f => f.path));
    const uniqueNewFiles = newFiles.filter(f => !existingPaths.has(f.path));

    AppState.files = [...AppState.files, ...uniqueNewFiles];
    updateFileList();
    showStatus(`Added ${uniqueNewFiles.length} file(s)`, 'info');
}

/**
 * Remove a file from the queue
 * @param {number} index - File index
 */
function removeFile(index) {
    AppState.files.splice(index, 1);
    updateFileList();
}

/**
 * Clear all files
 */
function clearFiles() {
    AppState.files = [];
    AppState.convertedFiles = [];
    updateFileList();
    hideProgress();
    hideOutput();
}

/**
 * Show status message
 * @param {string} message - Status message
 * @param {string} type - Message type (info, success, warning, error)
 */
function showStatus(message, type = 'info') {
    if (!DOM.statusMessage) return;

    DOM.statusMessage.textContent = message;
    DOM.statusMessage.className = `status-message ${type}`;
    DOM.statusMessage.style.display = 'block';

    // Auto-hide for info messages
    if (type === 'info' || type === 'success') {
        setTimeout(() => {
            if (DOM.statusMessage.textContent === message) {
                DOM.statusMessage.style.display = 'none';
            }
        }, 5000);
    }
}

/**
 * Show progress bar
 */
function showProgress() {
    if (DOM.progressContainer) {
        DOM.progressContainer.style.display = 'block';
    }
    if (DOM.convertBtn) {
        DOM.convertBtn.style.display = 'none';
    }
    if (DOM.cancelBtn) {
        DOM.cancelBtn.style.display = 'inline-block';
    }
}

/**
 * Hide progress bar
 */
function hideProgress() {
    if (DOM.progressContainer) {
        DOM.progressContainer.style.display = 'none';
    }
    if (DOM.convertBtn) {
        DOM.convertBtn.style.display = 'inline-block';
    }
    if (DOM.cancelBtn) {
        DOM.cancelBtn.style.display = 'none';
    }
    updateProgress(0, 'Ready');
}

/**
 * Update progress display
 * @param {number} percentage - Progress percentage (0-100)
 * @param {string} message - Progress message
 */
function updateProgress(percentage, message = '') {
    AppState.progress = percentage;

    if (DOM.progressFill) {
        DOM.progressFill.style.width = `${percentage}%`;
    }
    if (DOM.progressText) {
        DOM.progressText.textContent = message || `${percentage}%`;
    }
}

/**
 * Show output section with results
 */
function showOutput() {
    if (DOM.outputSection) {
        DOM.outputSection.style.display = 'block';
    }
}

/**
 * Hide output section
 */
function hideOutput() {
    if (DOM.outputSection) {
        DOM.outputSection.style.display = 'none';
    }
    if (DOM.resultsList) {
        DOM.resultsList.innerHTML = '';
    }
}

/**
 * Update results list
 */
function updateResultsList() {
    if (!DOM.resultsList) return;

    DOM.resultsList.innerHTML = AppState.convertedFiles.map(file => `
        <div class="result-item">
            <span class="result-icon">\u2705</span>
            <span class="result-name">${getFileName(file.input)}</span>
            <span class="result-arrow">\u2192</span>
            <span class="result-output" data-path="${file.output}" title="Click to reveal">${getFileName(file.output)}</span>
        </div>
    `).join('');

    // Add click handlers for output files
    DOM.resultsList.querySelectorAll('.result-output').forEach(el => {
        el.addEventListener('click', () => {
            window.fileOps.revealFile(el.dataset.path);
        });
    });
}

/**
 * Start file conversion
 */
async function startConversion() {
    if (AppState.files.length === 0) {
        showStatus('No files to convert', 'warning');
        return;
    }

    if (AppState.isConverting) {
        showStatus('Conversion already in progress', 'warning');
        return;
    }

    AppState.isConverting = true;
    AppState.convertedFiles = [];
    showProgress();
    showStatus('Starting conversion...', 'info');

    // Update file statuses
    AppState.files.forEach(file => {
        file.status = 'pending';
        file.statusText = 'Queued';
    });
    updateFileList();

    // Get file paths
    const filePaths = AppState.files.map(f => f.path);

    // Start conversion via IPC
    window.fileOps.convert(filePaths);
}

/**
 * Cancel ongoing conversion
 */
function cancelConversion() {
    if (!AppState.isConverting) return;

    window.fileOps.cancelConversion();
    showStatus('Cancelling...', 'warning');
}

/**
 * Handle file selection via dialog
 */
async function selectFiles() {
    try {
        const files = await window.fileOps.openDialog();
        if (files && files.length > 0) {
            addFiles(files);
        }
    } catch (error) {
        showStatus(`Error selecting files: ${error.message}`, 'error');
    }
}

/**
 * Setup drag and drop handlers
 */
function setupDragAndDrop() {
    const dropTarget = DOM.dropZone || DOM.glassPanel;
    if (!dropTarget) return;

    // Prevent default drag behaviors
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        dropTarget.addEventListener(eventName, (e) => {
            e.preventDefault();
            e.stopPropagation();
        });
        document.body.addEventListener(eventName, (e) => {
            e.preventDefault();
            e.stopPropagation();
        });
    });

    // Highlight drop zone on drag
    ['dragenter', 'dragover'].forEach(eventName => {
        dropTarget.addEventListener(eventName, () => {
            dropTarget.classList.add('drag-over');
        });
    });

    ['dragleave', 'drop'].forEach(eventName => {
        dropTarget.addEventListener(eventName, () => {
            dropTarget.classList.remove('drag-over');
        });
    });

    // Handle dropped files
    dropTarget.addEventListener('drop', (e) => {
        const files = Array.from(e.dataTransfer.files);
        const filePaths = files.map(f => f.path).filter(Boolean);

        if (filePaths.length > 0) {
            addFiles(filePaths);
        } else {
            showStatus('Unable to read dropped files', 'warning');
        }
    });
}

/**
 * Setup window controls
 */
function setupWindowControls() {
    if (DOM.closeBtn) {
        DOM.closeBtn.addEventListener('click', () => {
            window.windowControls.close();
        });
    }

    if (DOM.minimizeBtn) {
        DOM.minimizeBtn.addEventListener('click', () => {
            window.windowControls.minimize();
        });
    }

    if (DOM.maximizeBtn) {
        DOM.maximizeBtn.addEventListener('click', () => {
            window.windowControls.maximize();
        });
    }
}

/**
 * Setup IPC event listeners
 */
function setupIPCListeners() {
    // Conversion started
    window.api.on('conversion-started', (data) => {
        AppState.isConverting = true;
        AppState.outputDir = data.outputDir;
        showStatus(`Converting ${data.total} file(s)...`, 'info');
        updateProgress(0, 'Starting...');
    });

    // Progress updates
    window.api.on('conversion-progress', (data) => {
        if (data.percentage !== undefined) {
            updateProgress(data.percentage, `${data.percentage}% (${data.current}/${data.total})`);
        }
        if (data.message) {
            showStatus(data.message, 'info');
        }
    });

    // File converted
    window.api.on('file-converted', (data) => {
        AppState.convertedFiles.push(data);

        // Update file status
        const fileIndex = AppState.files.findIndex(f => f.path === data.input || f.name === getFileName(data.input));
        if (fileIndex !== -1) {
            AppState.files[fileIndex].status = 'completed';
            AppState.files[fileIndex].statusText = 'Done';
            updateFileList();
        }

        updateResultsList();
    });

    // Conversion complete
    window.api.on('conversion-complete', (data) => {
        AppState.isConverting = false;
        hideProgress();
        showOutput();
        showStatus(data.message, 'success');
        updateProgress(100, 'Complete!');

        // Mark all remaining files as complete
        AppState.files.forEach(file => {
            if (file.status !== 'completed') {
                file.status = 'completed';
                file.statusText = 'Done';
            }
        });
        updateFileList();
    });

    // Conversion error
    window.api.on('conversion-error', (data) => {
        AppState.isConverting = false;
        hideProgress();
        showStatus(`Error: ${data.message}`, 'error');
        console.error('Conversion error:', data);

        // Mark files as failed
        AppState.files.forEach(file => {
            if (file.status !== 'completed') {
                file.status = 'error';
                file.statusText = 'Failed';
            }
        });
        updateFileList();
    });

    // Conversion warning
    window.api.on('conversion-warning', (data) => {
        console.warn('Conversion warning:', data.message);
    });

    // Conversion cancelled
    window.api.on('conversion-cancelled', (data) => {
        AppState.isConverting = false;
        hideProgress();
        showStatus('Conversion cancelled', 'warning');

        // Mark pending files as cancelled
        AppState.files.forEach(file => {
            if (file.status === 'pending' || file.status === 'processing') {
                file.status = 'cancelled';
                file.statusText = 'Cancelled';
            }
        });
        updateFileList();
    });

    // Files selected (from menu or other sources)
    window.api.on('files-selected', (files) => {
        addFiles(files);
    });
}

/**
 * Setup button event listeners
 */
function setupButtonListeners() {
    // Select files button
    if (DOM.selectBtn) {
        DOM.selectBtn.addEventListener('click', selectFiles);
    }

    // Convert button
    if (DOM.convertBtn) {
        DOM.convertBtn.addEventListener('click', startConversion);
    }

    // Cancel button
    if (DOM.cancelBtn) {
        DOM.cancelBtn.addEventListener('click', cancelConversion);
    }

    // Open output folder button
    if (DOM.openOutputBtn) {
        DOM.openOutputBtn.addEventListener('click', () => {
            window.fileOps.openOutputFolder();
        });
    }
}

/**
 * Setup keyboard shortcuts
 */
function setupKeyboardShortcuts() {
    document.addEventListener('keydown', (e) => {
        // Cmd/Ctrl + O - Open files
        if ((e.metaKey || e.ctrlKey) && e.key === 'o') {
            e.preventDefault();
            selectFiles();
        }

        // Cmd/Ctrl + Enter - Start conversion
        if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') {
            e.preventDefault();
            if (!AppState.isConverting && AppState.files.length > 0) {
                startConversion();
            }
        }

        // Escape - Cancel conversion
        if (e.key === 'Escape' && AppState.isConverting) {
            cancelConversion();
        }

        // Cmd/Ctrl + Backspace - Clear files
        if ((e.metaKey || e.ctrlKey) && e.key === 'Backspace') {
            e.preventDefault();
            if (!AppState.isConverting) {
                clearFiles();
            }
        }
    });
}

/**
 * Load application info
 */
async function loadAppInfo() {
    try {
        AppState.appInfo = await window.appInfo.get();
        AppState.outputDir = AppState.appInfo.outputDir;

        // Update title if element exists
        const titleEl = document.querySelector('.app-title');
        if (titleEl) {
            titleEl.textContent = `${AppState.appInfo.name} v${AppState.appInfo.version}`;
        }
    } catch (error) {
        console.error('Failed to load app info:', error);
    }
}

/**
 * Apply system theme
 */
async function applySystemTheme() {
    try {
        AppState.theme = await window.appInfo.getTheme();
        document.body.dataset.theme = AppState.theme;
    } catch (error) {
        console.error('Failed to get system theme:', error);
    }
}

/**
 * Initialize the application
 */
async function initialize() {
    console.log('[Renderer] Initializing DocuMancer...');

    // Initialize DOM references
    initializeDOMReferences();

    // Setup event listeners
    setupWindowControls();
    setupDragAndDrop();
    setupIPCListeners();
    setupButtonListeners();
    setupKeyboardShortcuts();

    // Load app info and theme
    await loadAppInfo();
    await applySystemTheme();

    // Initial UI state
    hideProgress();
    hideOutput();
    updateFileList();

    console.log('[Renderer] DocuMancer initialized successfully');
}

// Initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initialize);
} else {
    initialize();
}

// Export for potential testing
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        AppState,
        addFiles,
        removeFile,
        clearFiles,
        startConversion,
        cancelConversion
    };
}
