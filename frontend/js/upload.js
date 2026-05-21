/* ============================================
   AI DocMaster — File Upload Logic
   ============================================ */

const uploadedFiles = [];

document.addEventListener('DOMContentLoaded', () => {
    initUploadPage();
});

function initUploadPage() {
    const dropzone = document.getElementById('uploadDropzone');
    const fileInput = document.getElementById('uploadFileInput');
    const fileList = document.getElementById('uploadFileList');
    const uploadAllBtn = document.getElementById('uploadAllBtn');

    if (!dropzone) return;

    // Click to browse
    dropzone.addEventListener('click', () => fileInput.click());

    // Drag events
    dropzone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropzone.classList.add('drag-over');
    });

    dropzone.addEventListener('dragleave', (e) => {
        e.preventDefault();
        dropzone.classList.remove('drag-over');
    });

    dropzone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropzone.classList.remove('drag-over');
        handleFiles(Array.from(e.dataTransfer.files));
    });

    // File input change
    fileInput.addEventListener('change', () => {
        handleFiles(Array.from(fileInput.files));
        fileInput.value = '';
    });

    // Upload all button
    if (uploadAllBtn) {
        uploadAllBtn.addEventListener('click', uploadAllFiles);
    }
}

function handleFiles(files) {
    const allowedTypes = ['application/pdf', 'image/png', 'image/jpeg', 'image/jpg'];
    const maxSize = 50 * 1024 * 1024; // 50MB

    files.forEach(file => {
        if (!allowedTypes.includes(file.type) && !file.name.match(/\.(pdf|png|jpg|jpeg)$/i)) {
            showToast(`${file.name}: Invalid file type. Only PDF, PNG, JPG allowed.`, 'error');
            return;
        }
        if (file.size > maxSize) {
            showToast(`${file.name}: File too large (max 50MB)`, 'error');
            return;
        }
        // Prevent duplicates
        if (uploadedFiles.find(f => f.name === file.name && f.size === file.size)) return;

        uploadedFiles.push(file);
    });

    renderFileList();
}

function renderFileList() {
    const fileList = document.getElementById('uploadFileList');
    const uploadAllBtn = document.getElementById('uploadAllBtn');

    if (!fileList) return;

    if (uploadedFiles.length === 0) {
        fileList.innerHTML = '<div class="empty-state"><p>No files selected</p></div>';
        if (uploadAllBtn) uploadAllBtn.style.display = 'none';
        return;
    }

    if (uploadAllBtn) uploadAllBtn.style.display = 'flex';

    fileList.innerHTML = uploadedFiles.map((file, index) => `
        <div class="upload-file-item" id="uploadItem-${index}">
            <div class="file-icon">${getFileIcon(file.type)}</div>
            <div class="file-details">
                <span class="file-name">${file.name}</span>
                <span class="file-size">${formatFileSize(file.size)}</span>
                <div class="progress-bar" id="progress-${index}" style="display:none;">
                    <div class="progress-fill" id="progressFill-${index}"></div>
                </div>
                <span class="upload-status" id="status-${index}"></span>
            </div>
            <button class="btn-icon remove-btn" onclick="removeFile(${index})" title="Remove">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
            </button>
        </div>
    `).join('');
}

function removeFile(index) {
    uploadedFiles.splice(index, 1);
    renderFileList();
}

async function uploadAllFiles() {
    const uploadAllBtn = document.getElementById('uploadAllBtn');
    if (uploadAllBtn) {
        uploadAllBtn.disabled = true;
        uploadAllBtn.innerHTML = '<span class="spinner-sm"></span> Uploading...';
    }

    for (let i = 0; i < uploadedFiles.length; i++) {
        const file = uploadedFiles[i];
        const progressBar = document.getElementById(`progress-${i}`);
        const progressFill = document.getElementById(`progressFill-${i}`);
        const statusEl = document.getElementById(`status-${i}`);
        const itemEl = document.getElementById(`uploadItem-${i}`);

        if (progressBar) progressBar.style.display = 'block';

        try {
            const formData = new FormData();
            formData.append('file', file);

            await uploadFileWithProgress('/pdf/upload', formData, (percent) => {
                if (progressFill) progressFill.style.width = percent + '%';
            });

            if (statusEl) {
                statusEl.textContent = '✓ Uploaded';
                statusEl.className = 'upload-status success';
            }
            if (itemEl) itemEl.classList.add('uploaded');
        } catch (err) {
            if (statusEl) {
                statusEl.textContent = '✗ ' + (err.message || 'Upload failed');
                statusEl.className = 'upload-status error';
            }
            if (itemEl) itemEl.classList.add('failed');
        }
    }

    showToast('Upload complete!', 'success');
    if (uploadAllBtn) {
        uploadAllBtn.disabled = false;
        uploadAllBtn.innerHTML = '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg> Upload All';
    }

    // Refresh recent files if on dashboard
    if (typeof loadRecentFiles === 'function') loadRecentFiles();
    if (typeof loadStats === 'function') loadStats();
}

function getFileIcon(type) {
    if (type === 'application/pdf' || type === 'pdf') {
        return '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#FF5252" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>';
    }
    return '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#00D4FF" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="8.5" cy="8.5" r="1.5"/><polyline points="21 15 16 10 5 21"/></svg>';
}
