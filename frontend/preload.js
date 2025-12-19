// preload.js
const { contextBridge, ipcRenderer } = require('electron')

contextBridge.exposeInMainWorld('api', {
  selectFiles: () => ipcRenderer.invoke('open-file-dialog'),
  convertFiles: (files) => ipcRenderer.invoke('convert-files', files),
  windowAction: (action) => ipcRenderer.send('window-action', action)
})
