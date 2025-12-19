const dropTarget = document.getElementById('drop-target')
const statusList = document.getElementById('status-list')
const selectButton = document.getElementById('select-files')
const titleButtons = document.querySelectorAll('.title-bar .btn')

const renderStatus = entries => {
  statusList.innerHTML = ''
  entries.forEach(entry => {
    const item = document.createElement('li')
    item.className = `status ${entry.status}`
    const name = document.createElement('div')
    name.className = 'file-name'
    name.textContent = entry.file

    const detail = document.createElement('div')
    detail.className = 'file-status'
    detail.textContent = entry.status === 'ok' ? 'Converted' : entry.message

    item.appendChild(name)
    item.appendChild(detail)
    statusList.appendChild(item)
  })
}

async function convertFiles(files) {
  if (!files || !files.length) return
  renderStatus(files.map(file => ({ file, status: 'processing', message: 'Processing…' })))
  try {
    const result = await window.api.convertFiles(files)
    if (result && result.results) {
      renderStatus(result.results)
    }
  } catch (err) {
    renderStatus(files.map(file => ({ file, status: 'error', message: err.message })))
  }
}

selectButton.addEventListener('click', async () => {
  const files = await window.api.selectFiles()
  await convertFiles(files)
})

dropTarget.addEventListener('dragover', e => {
  e.preventDefault()
  dropTarget.classList.add('dragging')
})

dropTarget.addEventListener('dragleave', () => {
  dropTarget.classList.remove('dragging')
})

dropTarget.addEventListener('drop', e => {
  e.preventDefault()
  dropTarget.classList.remove('dragging')
  const files = Array.from(e.dataTransfer.files).map(f => f.path)
  convertFiles(files)
})

titleButtons.forEach(button => {
  button.addEventListener('click', () => {
    const action = button.getAttribute('data-action')
    window.api.windowControl(action)
  })
})
