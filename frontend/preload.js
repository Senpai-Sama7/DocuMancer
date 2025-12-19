const { contextBridge, ipcRenderer } = require('electron')

const invokeSafely = (channel, data) => ipcRenderer.invoke(channel, data)
const sendSafely = (channel, data) => ipcRenderer.send(channel, data)
const onSafely = (channel, handler) => ipcRenderer.on(channel, handler)

contextBridge.exposeInMainWorld('api', {
  selectFiles: () => invokeSafely('open-file-dialog'),
  convertFiles: files => invokeSafely('convert-files', files),
  on: (channel, callback) => {
    const validChannels = ['conversion-progress', 'conversion-complete', 'conversion-error']
    if (validChannels.includes(channel)) {
      onSafely(channel, (_event, ...args) => callback(...args))
    }
  },
  windowControl: action => {
    const validActions = ['close', 'minimize', 'toggle-maximize']
    if (validActions.includes(action)) {
      sendSafely('window-control', action)
    }
  }
})
