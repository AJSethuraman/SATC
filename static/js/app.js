const form = document.getElementById('sorter-form');
const runButton = document.getElementById('run-button');
const processingMessage = document.getElementById('processing-message');
const useDefault = document.getElementById('use-default');
const folderPath = document.getElementById('folder-path');

if (form) {
  form.addEventListener('submit', () => {
    runButton.disabled = true;
    runButton.textContent = 'Processing...';
    processingMessage.hidden = false;
  });
}

if (useDefault && folderPath) {
  const syncFolderInput = () => {
    folderPath.disabled = useDefault.checked;
  };
  useDefault.addEventListener('change', syncFolderInput);
  syncFolderInput();
}
