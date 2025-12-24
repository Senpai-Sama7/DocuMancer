// preload.js - DocuMancer Secure Context Bridge
// Exposes controlled IPC methods to the renderer process

const { contextBridge, ipcRenderer } = require('electron');

/**
 * Valid IPC channels for sending messages to main process
 * @type {Set<string>}
 */
const SEND_CHANNELS = new Set([
    'convert-files',
    'select-files',
    'cancel-conversion',
    'window-minimize',
    'window-maximize',
    'window-close',
    'open-output-folder',
    'open-file',
    'reveal-file'
]);

/**
 * Valid IPC channels for receiving messages from main process
 * @type {Set<string>}
 */
const RECEIVE_CHANNELS = new Set([
    'conversion-started',
    'conversion-progress',
    'conversion-complete',
    'conversion-error',
    'conversion-warning',
    'conversion-cancelled',
    'file-converted',
    'files-selected'
]);

/**
 * Valid IPC channels for invoke (async request-response)
 * @type {Set<string>}
 */
const INVOKE_CHANNELS = new Set([
    'open-file-dialog',
    'get-app-info',
    'get-system-theme'
]);

/**
 * Listener cleanup registry to prevent memory leaks
 * @type {Map<string, Map<Function, Function>>}
 */
const listenerRegistry = new Map();

/**
 * Safely expose protected APIs to the renderer
 */
contextBridge.exposeInMainWorld('api', {
    /**
     * Send a message to the main process (fire-and-forget)
     * @param {string} channel - The IPC channel name
     * @param {any} data - The data to send
     * @returns {boolean} Whether the message was sent
     */
    send: (channel, data) => {
        if (SEND_CHANNELS.has(channel)) {
            ipcRenderer.send(channel, data);
            return true;
        }
        console.warn(`[Preload] Blocked send to invalid channel: ${channel}`);
        return false;
    },

    /**
     * Invoke an async IPC call and wait for response
     * @param {string} channel - The IPC channel name
     * @param {any} data - The data to send
     * @returns {Promise<any>} The response from main process
     */
    invoke: async (channel, data) => {
        if (INVOKE_CHANNELS.has(channel)) {
            try {
                return await ipcRenderer.invoke(channel, data);
            } catch (error) {
                console.error(`[Preload] Invoke error on ${channel}:`, error);
                throw new Error(`IPC invoke failed: ${error.message}`);
            }
        }
        console.warn(`[Preload] Blocked invoke to invalid channel: ${channel}`);
        return Promise.reject(new Error(`Invalid channel: ${channel}`));
    },

    /**
     * Register a listener for messages from main process
     * @param {string} channel - The IPC channel name
     * @param {Function} callback - The callback function
     * @returns {Function} Unsubscribe function
     */
    on: (channel, callback) => {
        if (!RECEIVE_CHANNELS.has(channel)) {
            console.warn(`[Preload] Blocked listener on invalid channel: ${channel}`);
            return () => {};
        }

        // Create wrapper that strips the event object for security
        const wrapper = (event, ...args) => {
            try {
                callback(...args);
            } catch (error) {
                console.error(`[Preload] Callback error on ${channel}:`, error);
            }
        };

        // Register the wrapper for cleanup
        if (!listenerRegistry.has(channel)) {
            listenerRegistry.set(channel, new Map());
        }
        listenerRegistry.get(channel).set(callback, wrapper);

        // Add the listener
        ipcRenderer.on(channel, wrapper);

        // Return unsubscribe function
        return () => {
            const channelListeners = listenerRegistry.get(channel);
            if (channelListeners && channelListeners.has(callback)) {
                const registeredWrapper = channelListeners.get(callback);
                ipcRenderer.removeListener(channel, registeredWrapper);
                channelListeners.delete(callback);
            }
        };
    },

    /**
     * Register a one-time listener for messages from main process
     * @param {string} channel - The IPC channel name
     * @param {Function} callback - The callback function
     */
    once: (channel, callback) => {
        if (!RECEIVE_CHANNELS.has(channel)) {
            console.warn(`[Preload] Blocked once listener on invalid channel: ${channel}`);
            return;
        }

        // Create wrapper that strips the event object and removes itself
        const wrapper = (event, ...args) => {
            try {
                callback(...args);
            } catch (error) {
                console.error(`[Preload] Callback error on ${channel}:`, error);
            } finally {
                ipcRenderer.removeListener(channel, wrapper);
            }
        };

        ipcRenderer.on(channel, wrapper);
    },

    /**
     * Remove a specific listener from a channel
     * @param {string} channel - The IPC channel name
     * @param {Function} callback - The original callback function
     */
    off: (channel, callback) => {
        if (!RECEIVE_CHANNELS.has(channel)) {
            return;
        }

        const channelListeners = listenerRegistry.get(channel);
        if (channelListeners && channelListeners.has(callback)) {
            const wrapper = channelListeners.get(callback);
            ipcRenderer.removeListener(channel, wrapper);
            channelListeners.delete(callback);
        }
    },

    /**
     * Remove all listeners from a channel
     * @param {string} channel - The IPC channel name
     */
    removeAllListeners: (channel) => {
        if (!RECEIVE_CHANNELS.has(channel)) {
            return;
        }

        ipcRenderer.removeAllListeners(channel);
        listenerRegistry.delete(channel);
    }
});

/**
 * Expose window control APIs
 */
contextBridge.exposeInMainWorld('windowControls', {
    minimize: () => ipcRenderer.send('window-minimize'),
    maximize: () => ipcRenderer.send('window-maximize'),
    close: () => ipcRenderer.send('window-close')
});

/**
 * Expose file operation APIs
 */
contextBridge.exposeInMainWorld('fileOps', {
    /**
     * Open file dialog and return selected paths
     * @returns {Promise<string[]>}
     */
    openDialog: () => ipcRenderer.invoke('open-file-dialog'),

    /**
     * Convert files to AI-optimized JSON
     * @param {string[]} filePaths
     */
    convert: (filePaths) => ipcRenderer.send('convert-files', filePaths),

    /**
     * Cancel ongoing conversion
     */
    cancelConversion: () => ipcRenderer.send('cancel-conversion'),

    /**
     * Open the output folder
     */
    openOutputFolder: () => ipcRenderer.send('open-output-folder'),

    /**
     * Open a file in default application
     * @param {string} filePath
     */
    openFile: (filePath) => ipcRenderer.send('open-file', filePath),

    /**
     * Reveal file in file manager
     * @param {string} filePath
     */
    revealFile: (filePath) => ipcRenderer.send('reveal-file', filePath)
});

/**
 * Expose application info APIs
 */
contextBridge.exposeInMainWorld('appInfo', {
    /**
     * Get application information
     * @returns {Promise<{name: string, version: string, outputDir: string, platform: string, arch: string}>}
     */
    get: () => ipcRenderer.invoke('get-app-info'),

    /**
     * Get system theme preference
     * @returns {Promise<'light'|'dark'>}
     */
    getTheme: () => ipcRenderer.invoke('get-system-theme')
});

/**
 * Expose platform detection
 */
contextBridge.exposeInMainWorld('platform', {
    isMac: process.platform === 'darwin',
    isWindows: process.platform === 'win32',
    isLinux: process.platform === 'linux',
    os: process.platform
});

// Log preload completion
console.log('[Preload] Context bridge initialized successfully');
