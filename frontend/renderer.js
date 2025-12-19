// renderer.js
const selectButton = document.querySelector('.action')
const glassPanel = document.querySelector('.glass-panel')
const messageEl = document.getElementById('message')
const statusList = document.getElementById('status-list')

const queue = new Map()

function setMessage(text, tone = 'info') {
  messageEl.textContent = text
  messageEl.setAttribute('data-tone', tone)
}

function renderStatuses() {
  statusList.innerHTML = ''
  queue.forEach((status, file) => {
    const li = document.createElement('li')
    li.innerHTML = `<span class="file">${file}</span><span class="pill ${status.state}">${status.state}</span>`
    if (status.preview) {
      const pre = document.createElement('pre')
      pre.textContent = status.preview
      li.appendChild(pre)
    }
    statusList.appendChild(li)
  })
}

async function convert(files) {
  if (!files.length) {
    setMessage('No files selected', 'warning')
    return
  }
  files.forEach((file) => queue.set(file, { state: 'pending' }))
  renderStatuses()

  try {
    setMessage('Converting documents…', 'info')
    const result = await window.api.convertFiles(files)
    result.results.forEach((item) => {
      queue.set(item.path, {
        state: 'complete',
        preview: item.content.slice(0, 280)
      })
    })
    setMessage('Conversion finished', 'success')
  } catch (err) {
    console.error(err)
    files.forEach((file) => queue.set(file, { state: 'error' }))
    setMessage(`Conversion failed: ${err.message}`, 'error')
  } finally {
    renderStatuses()
  }
}

async function selectFiles() {
  const files = await window.api.selectFiles()
  if (files?.length) {
    await convert(files)
  }
}

glassPanel.addEventListener('click', selectFiles)
selectButton.addEventListener('click', (event) => {
  event.stopPropagation()
  selectFiles()
})

document.body.addEventListener('dragover', (e) => e.preventDefault())
document.body.addEventListener('drop', (e) => {
  e.preventDefault()
  const files = Array.from(e.dataTransfer.files).map((f) => f.path)
  convert(files)
})

document.querySelector('.btn.close').addEventListener('click', () => window.api.windowAction('close'))
document.querySelector('.btn.minimize').addEventListener('click', () => window.api.windowAction('minimize'))
document.querySelector('.btn.maximize').addEventListener('click', () => window.api.windowAction('maximize'))