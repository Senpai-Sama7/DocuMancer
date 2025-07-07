// renderer.js
document.querySelector('.glass-panel').addEventListener('click', () => {
  // open file dialog via Electron ipcRenderer...
});
document.body.addEventListener('dragover', e => e.preventDefault());
document.body.addEventListener('drop', e => {
  e.preventDefault();
  const files = Array.from(e.dataTransfer.files).map(f => f.path);
  console.log('Dropped files:', files);
  // trigger your conversion pipeline...
});