/* ============================================
   AI DocMaster — PDF Tools Logic
   ============================================ */

// ── PDF Merge ──
let mergeFiles = [];

function initMergeTool() {
    const dropzone = document.getElementById('mergeDropzone');
    const fileInput = document.getElementById('mergeFileInput');

    if (!dropzone) return;

    dropzone.addEventListener('click', () => fileInput.click());
    dropzone.addEventListener('dragover', (e) => { e.preventDefault(); dropzone.classList.add('drag-over'); });
    dropzone.addEventListener('dragleave', () => dropzone.classList.remove('drag-over'));
    dropzone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropzone.classList.remove('drag-over');
        addMergeFiles(Array.from(e.dataTransfer.files));
    });
    fileInput.addEventListener('change', () => { addMergeFiles(Array.from(fileInput.files)); fileInput.value = ''; });
}

function addMergeFiles(files) {
    files.forEach(file => {
        if (!file.name.toLowerCase().endsWith('.pdf')) {
            showToast(`${file.name}: Only PDF files are accepted`, 'error');
            return;
        }
        if (!mergeFiles.find(f => f.name === file.name)) {
            mergeFiles.push(file);
        }
    });
    renderMergeFileList();
}

function renderMergeFileList() {
    const list = document.getElementById('mergeFileList');
    const btn = document.getElementById('mergeBtn');
    if (!list) return;

    if (mergeFiles.length === 0) {
        list.innerHTML = '<p class="text-muted">No files selected. Add at least 2 PDFs to merge.</p>';
        if (btn) btn.disabled = true;
        return;
    }

    if (btn) btn.disabled = mergeFiles.length < 2;

    list.innerHTML = mergeFiles.map((f, i) => `
        <div class="file-item">
            <span class="file-order">${i + 1}</span>
            <div class="file-icon"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#FF5252" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg></div>
            <div class="file-info">
                <span class="file-name">${f.name}</span>
                <span class="file-meta">${formatFileSize(f.size)}</span>
            </div>
            <button class="btn-icon" onclick="removeMergeFile(${i})" title="Remove">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
            </button>
        </div>
    `).join('');
}

function removeMergeFile(index) {
    mergeFiles.splice(index, 1);
    renderMergeFileList();
}

async function handleMerge(e) {
    if (e) {
        e.preventDefault();
    }
    if (mergeFiles.length < 2) { showToast('Please add at least 2 PDFs to merge', 'warning'); return; }

    const btn = document.getElementById('mergeBtn');
    const resultDiv = document.getElementById('mergeResult');
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner-sm"></span> Merging...';

    const formData = new FormData();
    mergeFiles.forEach(f => formData.append('files', f));

    try {
        const data = await uploadFileWithProgress('/pdf/merge', formData, () => {});
        if (data && data.download_url) {
            resultDiv.innerHTML = `
                <div class="result-card success">
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#00E676" stroke-width="2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>
                    <div>
                        <h4>PDFs Merged Successfully!</h4>
                        <p>${mergeFiles.length} files combined into one PDF</p>
                    </div>
                    <a href="${API_BASE}${data.download_url}" class="btn btn-primary" download>
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
                        Download Merged PDF
                    </a>
                </div>
            `;
            resultDiv.style.display = 'block';
            showToast('PDFs merged successfully!', 'success');
            
            // Refresh stores & dashboard stats
            if (typeof loadStats === 'function') loadStats();
            if (typeof loadRecentFiles === 'function') loadRecentFiles();
            if (typeof loadAllFiles === 'function') loadAllFiles();
            if (typeof loadSectionStores === 'function') loadSectionStores();
            mergeFiles = [];
            renderMergeFileList();
        }
    } catch (err) {
        showToast('Merge failed: ' + err.message, 'error');
    } finally {
        btn.disabled = false;
        btn.innerHTML = '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M16 16v1a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V7a2 2 0 0 1 2-2h2m5.66 0H14a2 2 0 0 1 2 2v3.34"/></svg> Merge PDFs';
    }
}

// ── PDF Split ──
let splitFile = null;

function initSplitTool() {
    const dropzone = document.getElementById('splitDropzone');
    const fileInput = document.getElementById('splitFileInput');
    const splitPages = document.getElementById('splitPages');

    if (!dropzone) return;

    dropzone.addEventListener('click', () => fileInput.click());
    dropzone.addEventListener('dragover', (e) => { e.preventDefault(); dropzone.classList.add('drag-over'); });
    dropzone.addEventListener('dragleave', () => dropzone.classList.remove('drag-over'));
    dropzone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropzone.classList.remove('drag-over');
        setSplitFile(e.dataTransfer.files[0]);
    });
    fileInput.addEventListener('change', () => { setSplitFile(fileInput.files[0]); fileInput.value = ''; });

    if (splitPages) {
        splitPages.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                handleSplit(e);
            }
        });
    }
}

function setSplitFile(file) {
    if (!file || !file.name.toLowerCase().endsWith('.pdf')) {
        showToast('Please select a PDF file', 'error');
        return;
    }
    splitFile = file;
    const info = document.getElementById('splitFileInfo');
    const options = document.getElementById('splitOptions');
    if (info) info.innerHTML = `<div class="file-item"><div class="file-icon"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#FF5252" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg></div><div class="file-info"><span class="file-name">${file.name}</span><span class="file-meta">${formatFileSize(file.size)}</span></div></div>`;
    if (options) options.style.display = 'block';
}

async function handleSplit(e) {
    if (e) {
        e.preventDefault();
    }
    if (!splitFile) { showToast('Please select a PDF first', 'warning'); return; }

    const pages = document.getElementById('splitPages').value.trim();
    if (!pages) { showToast('Enter page ranges (e.g., 1-3, 5, 7-10)', 'warning'); return; }

    const btn = document.getElementById('splitBtn');
    const resultDiv = document.getElementById('splitResult');
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner-sm"></span> Splitting...';

    const formData = new FormData();
    formData.append('file', splitFile);
    formData.append('pages', pages);

    try {
        const data = await uploadFileWithProgress('/pdf/split', formData, () => {});
        const parts = data && (data.parts || data.files);
        if (data && parts) {
            resultDiv.innerHTML = `
                <div class="result-card success">
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#00E676" stroke-width="2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>
                    <div>
                        <h4>PDF Split Successfully!</h4>
                        <p>Created ${parts.length} file(s)</p>
                    </div>
                </div>
                <div class="download-list">
                    ${parts.map((f, i) => `
                        <a href="${API_BASE}${f.download_url}" class="btn btn-outline btn-sm" download>
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
                            Part ${i + 1}
                        </a>
                    `).join('')}
                </div>
            `;
            resultDiv.style.display = 'block';
            showToast('PDF split successfully!', 'success');

            // Refresh stores & dashboard stats
            if (typeof loadStats === 'function') loadStats();
            if (typeof loadRecentFiles === 'function') loadRecentFiles();
            if (typeof loadAllFiles === 'function') loadAllFiles();
            if (typeof loadSectionStores === 'function') loadSectionStores();
            splitFile = null;
            const info = document.getElementById('splitFileInfo');
            const options = document.getElementById('splitOptions');
            if (info) info.innerHTML = '';
            if (options) options.style.display = 'none';
        }
    } catch (err) {
        showToast('Split failed: ' + err.message, 'error');
    } finally {
        btn.disabled = false;
        btn.innerHTML = '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="15 3 21 3 21 9"/><polyline points="9 21 3 21 3 15"/><line x1="21" y1="3" x2="14" y2="10"/><line x1="3" y1="21" x2="10" y2="14"/></svg> Split PDF';
    }
}

// ── PDF Compress ──
let compressFile = null;

function initCompressTool() {
    const dropzone = document.getElementById('compressDropzone');
    const fileInput = document.getElementById('compressFileInput');

    if (!dropzone) return;

    dropzone.addEventListener('click', () => fileInput.click());
    dropzone.addEventListener('dragover', (e) => { e.preventDefault(); dropzone.classList.add('drag-over'); });
    dropzone.addEventListener('dragleave', () => dropzone.classList.remove('drag-over'));
    dropzone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropzone.classList.remove('drag-over');
        setCompressFile(e.dataTransfer.files[0]);
    });
    fileInput.addEventListener('change', () => { setCompressFile(fileInput.files[0]); fileInput.value = ''; });
}

function setCompressFile(file) {
    if (!file || !file.name.toLowerCase().endsWith('.pdf')) {
        showToast('Please select a PDF file', 'error');
        return;
    }
    compressFile = file;
    const info = document.getElementById('compressFileInfo');
    if (info) info.innerHTML = `<div class="file-item"><div class="file-icon"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#FF5252" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg></div><div class="file-info"><span class="file-name">${file.name}</span><span class="file-meta">${formatFileSize(file.size)}</span></div></div>`;
    document.getElementById('compressBtn').disabled = false;
}

async function handleCompress(e) {
    if (e) {
        e.preventDefault();
    }
    if (!compressFile) { showToast('Please select a PDF first', 'warning'); return; }

    const btn = document.getElementById('compressBtn');
    const resultDiv = document.getElementById('compressResult');
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner-sm"></span> Compressing...';

    const formData = new FormData();
    formData.append('file', compressFile);

    try {
        const data = await uploadFileWithProgress('/pdf/compress', formData, () => {});
        if (data) {
            const stats = data.stats || data;
            const reduction = stats.reduction_percent || 0;
            resultDiv.innerHTML = `
                <div class="result-card success">
                    <div class="compress-stats">
                        <div class="stat-item">
                            <span class="stat-label">Original</span>
                            <span class="stat-value">${formatFileSize(stats.original_size)}</span>
                        </div>
                        <div class="stat-arrow">→</div>
                        <div class="stat-item">
                            <span class="stat-label">Compressed</span>
                            <span class="stat-value">${formatFileSize(stats.compressed_size)}</span>
                        </div>
                        <div class="stat-item highlight">
                            <span class="stat-label">Reduced</span>
                            <span class="stat-value">${reduction.toFixed(1)}%</span>
                        </div>
                    </div>
                    <a href="${API_BASE}${data.download_url}" class="btn btn-primary" download>
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
                        Download Compressed PDF
                    </a>
                </div>
            `;
            resultDiv.style.display = 'block';
            showToast(`PDF compressed by ${reduction.toFixed(1)}%!`, 'success');

            // Refresh stores & dashboard stats
            if (typeof loadStats === 'function') loadStats();
            if (typeof loadRecentFiles === 'function') loadRecentFiles();
            if (typeof loadAllFiles === 'function') loadAllFiles();
            if (typeof loadSectionStores === 'function') loadSectionStores();
            compressFile = null;
            const info = document.getElementById('compressFileInfo');
            if (info) info.innerHTML = '';
            btn.disabled = true;
        }
    } catch (err) {
        showToast('Compression failed: ' + err.message, 'error');
    } finally {
        btn.disabled = false;
        btn.innerHTML = '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="4 14 10 14 10 20"/><polyline points="20 10 14 10 14 4"/><line x1="14" y1="10" x2="21" y2="3"/><line x1="3" y1="21" x2="10" y2="14"/></svg> Compress PDF';
    }
}

// ── Section-Specific Stores ──

async function loadSectionStores() {
    try {
        const data = await apiFetch('/files/list');
        if (!data || !data.files) return;

        const allFiles = data.files;

        // 1. Render Merge Store
        const mergeContainer = document.getElementById('mergeStoreList');
        if (mergeContainer) {
            const merges = allFiles.filter(f => f.original_name === 'merged.pdf' || f.filename.startsWith('merged_'));
            renderStoreItems(mergeContainer, merges, 'merge');
        }

        // 2. Render Split Store
        const splitContainer = document.getElementById('splitStoreList');
        if (splitContainer) {
            const splits = allFiles.filter(f => f.filename.startsWith('split_') || f.original_name.startsWith('split_'));
            renderStoreItems(splitContainer, splits, 'split');
        }

        // 3. Render Compress Store
        const compressContainer = document.getElementById('compressStoreList');
        if (compressContainer) {
            const compressions = allFiles.filter(f => f.filename.startsWith('compressed_') || f.original_name.startsWith('compressed_'));
            renderStoreItems(compressContainer, compressions, 'compress');
        }
    } catch (e) {
        console.error("Failed to load section stores", e);
    }
}

function renderStoreItems(container, files, section) {
    if (files.length === 0) {
        container.innerHTML = `<div class="empty-state"><p>No saved files found for this tool</p></div>`;
        return;
    }

    container.innerHTML = files.map(f => `
        <div class="file-item">
            <div class="file-icon">${getFileIcon(f.file_type)}</div>
            <div class="file-info">
                <span class="file-name">${f.original_name || f.filename}</span>
                <span class="file-meta">${formatFileSize(f.size)} • ${formatDate(f.created_at)}</span>
            </div>
            <div class="file-actions">
                <button class="btn-icon" onclick="downloadFile('${f.id}')" title="Download">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
                </button>
                <button class="btn-icon danger" onclick="deleteSectionFile('${f.id}')" title="Delete">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>
                </button>
            </div>
        </div>
    `).join('');
}

async function deleteSectionFile(fileId) {
    if (!confirm('Delete this file permanently?')) return;
    try {
        await apiFetch(`/files/${fileId}`, { method: 'DELETE' });
        showToast('File deleted', 'success');
        
        // Refresh everything
        loadSectionStores();
        if (typeof loadStats === 'function') loadStats();
        if (typeof loadRecentFiles === 'function') loadRecentFiles();
        if (typeof loadAllFiles === 'function') loadAllFiles();
    } catch (e) {
        showToast('Delete failed', 'error');
    }
}

// ── Initialize all PDF tools ──
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        initMergeTool();
        initSplitTool();
        initCompressTool();
    });
} else {
    initMergeTool();
    initSplitTool();
    initCompressTool();
}
