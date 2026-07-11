/* ============================================
   AI DocMaster — PDF Management Tools (Phase 1)
   Handles: organize, rotate, delete-pages, extract-pages,
            duplicate-pages, crop, rearrange
   ============================================ */

console.log('🔧 [AI DocMaster] pdf-manage.js loaded');

// ─────────────────────────────────────────────
// Generic single-file dropzone initializer
// ─────────────────────────────────────────────
function initSingleDropzone(dropzoneId, inputId, accept, onFile) {
    const dropzone = document.getElementById(dropzoneId);
    const input    = document.getElementById(inputId);
    if (!dropzone || !input) return;

    dropzone.addEventListener('click', () => input.click());
    input.addEventListener('click', e => e.stopPropagation());
    dropzone.addEventListener('dragover', e => { e.preventDefault(); dropzone.classList.add('drag-over'); });
    dropzone.addEventListener('dragleave', () => dropzone.classList.remove('drag-over'));
    dropzone.addEventListener('drop', e => {
        e.preventDefault();
        dropzone.classList.remove('drag-over');
        const f = e.dataTransfer.files[0];
        if (f) onFile(f);
    });
    input.addEventListener('change', () => {
        if (input.files[0]) onFile(input.files[0]);
        input.value = '';
    });
}

// Render a "file selected" badge under the dropzone
function showSelectedFile(containerId, file) {
    const el = document.getElementById(containerId);
    if (!el) return;
    el.innerHTML = `
        <div class="file-item" style="margin-top:1rem">
            <div class="file-icon">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#FF5252" stroke-width="2">
                    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                    <polyline points="14 2 14 8 20 8"/>
                </svg>
            </div>
            <div class="file-info">
                <span class="file-name">${file.name}</span>
                <span class="file-meta">${formatFileSize(file.size)}</span>
            </div>
        </div>`;
}

// Render a download result card (same pattern as pdf-tools.js)
function showDownloadResult(containerId, data, label) {
    const el = document.getElementById(containerId);
    if (!el) return;
    el.style.display = 'block';
    el.innerHTML = `
        <div class="result-card success">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#00E676" stroke-width="2">
                <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/>
                <polyline points="22 4 12 14.01 9 11.01"/>
            </svg>
            <div>
                <h4>${label}</h4>
                <p>${formatFileSize(data.size || 0)} · ${data.page_count ? data.page_count + ' pages' : ''}</p>
            </div>
            <a href="${API_BASE}${data.download_url}" class="btn btn-primary" download>
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                    <polyline points="7 10 12 15 17 10"/>
                    <line x1="12" y1="15" x2="12" y2="3"/>
                </svg>
                Download
            </a>
        </div>`;
}

// Generic button loading state helpers (mirrors pdf-tools.js)
function setBtnLoading(btn, text) {
    btn.disabled = true;
    btn._origHTML = btn.innerHTML;
    btn.innerHTML = `<span class="spinner-sm"></span> ${text}`;
}
function setBtnReset(btn) {
    btn.disabled = false;
    btn.innerHTML = btn._origHTML || 'Go';
}


// ─────────────────────────────────────────────
// 1. ORGANIZE — reorder pages
// ─────────────────────────────────────────────
let organizeFile = null;

function initOrganizeTool() {
    initSingleDropzone('organizeDropzone', 'organizeFileInput', '.pdf', f => {
        organizeFile = f;
        showSelectedFile('organizeFileInfo', f);
        const opts = document.getElementById('organizeOptions');
        if (opts) opts.style.display = 'block';
    });
}

async function handleOrganize(e) {
    if (e) e.preventDefault();
    if (!organizeFile) { showToast('Please select a PDF first', 'warning'); return; }

    const orderInput = document.getElementById('organizeOrder');
    if (!orderInput || !orderInput.value.trim()) {
        showToast('Enter the page order (e.g. 3,1,2)', 'warning'); return;
    }

    const btn = document.getElementById('organizeBtn');
    setBtnLoading(btn, 'Organizing...');

    const fd = new FormData();
    fd.append('file', organizeFile);
    fd.append('page_order', orderInput.value.trim());

    try {
        const data = await uploadFileWithProgress('/pdf/organize', fd, () => {});
        showDownloadResult('organizeResult', data, 'Pages Reordered!');
        showToast('Pages organized successfully', 'success');
    } catch (err) {
        showToast(err.message || 'Organize failed', 'error');
    } finally {
        setBtnReset(btn);
    }
}


// ─────────────────────────────────────────────
// 2. ROTATE — rotate pages
// ─────────────────────────────────────────────
let rotateFile = null;

function initRotateTool() {
    initSingleDropzone('rotateDropzone', 'rotateFileInput', '.pdf', f => {
        rotateFile = f;
        showSelectedFile('rotateFileInfo', f);
        const opts = document.getElementById('rotateOptions');
        if (opts) opts.style.display = 'block';
    });
}

async function handleRotate(e) {
    if (e) e.preventDefault();
    if (!rotateFile) { showToast('Please select a PDF first', 'warning'); return; }

    const rotation = document.getElementById('rotateAngle')?.value || '90';
    const pages    = document.getElementById('rotatePages')?.value.trim() || '';

    const btn = document.getElementById('rotateBtn');
    setBtnLoading(btn, 'Rotating...');

    const fd = new FormData();
    fd.append('file', rotateFile);
    fd.append('rotation', rotation);
    if (pages) fd.append('pages', pages);

    try {
        const data = await uploadFileWithProgress('/pdf/rotate', fd, () => {});
        showDownloadResult('rotateResult', data, `Rotated ${rotation}° Successfully!`);
        showToast('PDF rotated successfully', 'success');
    } catch (err) {
        showToast(err.message || 'Rotation failed', 'error');
    } finally {
        setBtnReset(btn);
    }
}


// ─────────────────────────────────────────────
// 3. DELETE PAGES
// ─────────────────────────────────────────────
let deleteFile = null;

function initDeletePagesTool() {
    initSingleDropzone('deletePagesDropzone', 'deletePagesFileInput', '.pdf', f => {
        deleteFile = f;
        showSelectedFile('deletePagesFileInfo', f);
        const opts = document.getElementById('deletePagesOptions');
        if (opts) opts.style.display = 'block';
    });
}

async function handleDeletePages(e) {
    if (e) e.preventDefault();
    if (!deleteFile) { showToast('Please select a PDF first', 'warning'); return; }

    const pages = document.getElementById('deletePagesInput')?.value.trim();
    if (!pages) { showToast('Enter page numbers to delete (e.g. 2,4)', 'warning'); return; }

    const btn = document.getElementById('deletePagesBtn');
    setBtnLoading(btn, 'Deleting...');

    const fd = new FormData();
    fd.append('file', deleteFile);
    fd.append('pages', pages);

    try {
        const data = await uploadFileWithProgress('/pdf/delete-pages', fd, () => {});
        showDownloadResult('deletePagesResult', data, 'Pages Deleted Successfully!');
        showToast('Pages deleted', 'success');
    } catch (err) {
        showToast(err.message || 'Delete failed', 'error');
    } finally {
        setBtnReset(btn);
    }
}


// ─────────────────────────────────────────────
// 4. EXTRACT PAGES
// ─────────────────────────────────────────────
let extractFile = null;

function initExtractPagesTool() {
    initSingleDropzone('extractPagesDropzone', 'extractPagesFileInput', '.pdf', f => {
        extractFile = f;
        showSelectedFile('extractPagesFileInfo', f);
        const opts = document.getElementById('extractPagesOptions');
        if (opts) opts.style.display = 'block';
    });
}

async function handleExtractPages(e) {
    if (e) e.preventDefault();
    if (!extractFile) { showToast('Please select a PDF first', 'warning'); return; }

    const pages = document.getElementById('extractPagesInput')?.value.trim();
    if (!pages) { showToast('Enter page numbers to extract (e.g. 1,3,5)', 'warning'); return; }

    const btn = document.getElementById('extractPagesBtn');
    setBtnLoading(btn, 'Extracting...');

    const fd = new FormData();
    fd.append('file', extractFile);
    fd.append('pages', pages);

    try {
        const data = await uploadFileWithProgress('/pdf/extract-pages', fd, () => {});
        showDownloadResult('extractPagesResult', data, 'Pages Extracted!');
        showToast('Pages extracted successfully', 'success');
    } catch (err) {
        showToast(err.message || 'Extract failed', 'error');
    } finally {
        setBtnReset(btn);
    }
}


// ─────────────────────────────────────────────
// 5. DUPLICATE PAGES
// ─────────────────────────────────────────────
let duplicateFile = null;

function initDuplicatePagesTool() {
    initSingleDropzone('duplicatePagesDropzone', 'duplicatePagesFileInput', '.pdf', f => {
        duplicateFile = f;
        showSelectedFile('duplicatePagesFileInfo', f);
        const opts = document.getElementById('duplicatePagesOptions');
        if (opts) opts.style.display = 'block';
    });
}

async function handleDuplicatePages(e) {
    if (e) e.preventDefault();
    if (!duplicateFile) { showToast('Please select a PDF first', 'warning'); return; }

    const pages = document.getElementById('duplicatePagesInput')?.value.trim();
    if (!pages) { showToast('Enter page numbers to duplicate (e.g. 1,2)', 'warning'); return; }

    const btn = document.getElementById('duplicatePagesBtn');
    setBtnLoading(btn, 'Duplicating...');

    const fd = new FormData();
    fd.append('file', duplicateFile);
    fd.append('pages', pages);

    try {
        const data = await uploadFileWithProgress('/pdf/duplicate-pages', fd, () => {});
        showDownloadResult('duplicatePagesResult', data, 'Pages Duplicated!');
        showToast('Pages duplicated', 'success');
    } catch (err) {
        showToast(err.message || 'Duplicate failed', 'error');
    } finally {
        setBtnReset(btn);
    }
}


// ─────────────────────────────────────────────
// 6. CROP PDF
// ─────────────────────────────────────────────
let cropFile = null;

function initCropTool() {
    initSingleDropzone('cropDropzone', 'cropFileInput', '.pdf', f => {
        cropFile = f;
        showSelectedFile('cropFileInfo', f);
        const opts = document.getElementById('cropOptions');
        if (opts) opts.style.display = 'block';
    });

    // Live update preview labels
    ['cropLeft','cropBottom','cropRight','cropTop'].forEach(id => {
        const el = document.getElementById(id);
        const lbl = document.getElementById(id + 'Val');
        if (el && lbl) el.addEventListener('input', () => { lbl.textContent = el.value + '%'; });
    });
}

async function handleCrop(e) {
    if (e) e.preventDefault();
    if (!cropFile) { showToast('Please select a PDF first', 'warning'); return; }

    const left   = document.getElementById('cropLeft')?.value   || 0;
    const bottom = document.getElementById('cropBottom')?.value || 0;
    const right  = document.getElementById('cropRight')?.value  || 100;
    const top    = document.getElementById('cropTop')?.value    || 100;
    const pages  = document.getElementById('cropPages')?.value.trim() || '';

    const btn = document.getElementById('cropBtn');
    setBtnLoading(btn, 'Cropping...');

    const fd = new FormData();
    fd.append('file', cropFile);
    fd.append('left',   left);
    fd.append('bottom', bottom);
    fd.append('right',  right);
    fd.append('top',    top);
    if (pages) fd.append('pages', pages);

    try {
        const data = await uploadFileWithProgress('/pdf/crop', fd, () => {});
        showDownloadResult('cropResult', data, 'PDF Cropped Successfully!');
        showToast('PDF cropped', 'success');
    } catch (err) {
        showToast(err.message || 'Crop failed', 'error');
    } finally {
        setBtnReset(btn);
    }
}


// ─────────────────────────────────────────────
// 7. REARRANGE — full drag-and-drop permutation
// ─────────────────────────────────────────────
let rearrangeFile = null;

function initRearrangeTool() {
    initSingleDropzone('rearrangeDropzone', 'rearrangeFileInput', '.pdf', f => {
        rearrangeFile = f;
        showSelectedFile('rearrangeFileInfo', f);
        const opts = document.getElementById('rearrangeOptions');
        if (opts) opts.style.display = 'block';
    });
}

async function handleRearrange(e) {
    if (e) e.preventDefault();
    if (!rearrangeFile) { showToast('Please select a PDF first', 'warning'); return; }

    const orderInput = document.getElementById('rearrangeOrder');
    if (!orderInput || !orderInput.value.trim()) {
        showToast('Enter the complete new page order (e.g. 3,1,2 for a 3-page PDF)', 'warning'); return;
    }

    const btn = document.getElementById('rearrangeBtn');
    setBtnLoading(btn, 'Rearranging...');

    const fd = new FormData();
    fd.append('file', rearrangeFile);
    fd.append('new_order', orderInput.value.trim());

    try {
        const data = await uploadFileWithProgress('/pdf/rearrange', fd, () => {});
        showDownloadResult('rearrangeResult', data, 'Pages Rearranged!');
        showToast('PDF pages rearranged', 'success');
    } catch (err) {
        showToast(err.message || 'Rearrange failed', 'error');
    } finally {
        setBtnReset(btn);
    }
}


// ─────────────────────────────────────────────
// Auto-init all tools on DOMContentLoaded
// ─────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    initOrganizeTool();
    initRotateTool();
    initDeletePagesTool();
    initExtractPagesTool();
    initDuplicatePagesTool();
    initCropTool();
    initRearrangeTool();
});
