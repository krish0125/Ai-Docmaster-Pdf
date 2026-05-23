/* ============================================
   AI DocMaster — OCR Logic
   ============================================ */

let ocrFile = null;

function initOcrTool() {
    const dropzone = document.getElementById('ocrDropzone');
    const fileInput = document.getElementById('ocrFileInput');

    if (!dropzone) return;

    dropzone.addEventListener('click', () => fileInput.click());
    dropzone.addEventListener('dragover', (e) => { e.preventDefault(); dropzone.classList.add('drag-over'); });
    dropzone.addEventListener('dragleave', () => dropzone.classList.remove('drag-over'));
    dropzone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropzone.classList.remove('drag-over');
        setOcrFile(e.dataTransfer.files[0]);
    });
    fileInput.addEventListener('change', () => { setOcrFile(fileInput.files[0]); fileInput.value = ''; });
}

function setOcrFile(file) {
    if (!file) return;
    const allowed = ['image/png', 'image/jpeg', 'image/jpg', 'application/pdf'];
    if (!allowed.includes(file.type) && !file.name.match(/\.(png|jpg|jpeg|pdf)$/i)) {
        showToast('Please select an image (PNG, JPG) or PDF file', 'error');
        return;
    }

    ocrFile = file;

    const preview = document.getElementById('ocrPreview');
    const info = document.getElementById('ocrFileInfo');

    if (info) {
        info.innerHTML = `<div class="file-item"><div class="file-info"><span class="file-name">${file.name}</span><span class="file-meta">${formatFileSize(file.size)}</span></div></div>`;
    }

    // Show image preview
    if (preview && file.type.startsWith('image/')) {
        const reader = new FileReader();
        reader.onload = (e) => {
            preview.innerHTML = `<img src="${e.target.result}" alt="Preview" style="max-width:100%;max-height:300px;border-radius:8px;">`;
            preview.style.display = 'block';
        };
        reader.readAsDataURL(file);
    } else if (preview) {
        preview.innerHTML = `<div class="pdf-preview-placeholder"><svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="#FF5252" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg><p>PDF file selected</p></div>`;
        preview.style.display = 'block';
    }

    document.getElementById('ocrBtn').disabled = false;
}

async function handleOcr() {
    if (!ocrFile) { showToast('Please select a file first', 'warning'); return; }

    const btn = document.getElementById('ocrBtn');
    const resultDiv = document.getElementById('ocrResult');
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner-sm"></span> Extracting text...';

    const formData = new FormData();
    formData.append('file', ocrFile);

    const endpoint = ocrFile.type === 'application/pdf' ? '/ocr/pdf-ocr' : '/ocr/extract';

    try {
        const data = await uploadFileWithProgress(endpoint, formData, () => {});
        if (data) {
            const resData = data.result || data;
            const text = resData.text || resData.extracted_text || 'No text found';
            const confidence = resData.confidence || 'N/A';
            const wordCount = resData.word_count || text.split(/\s+/).filter(w => w).length;

            resultDiv.innerHTML = `
                <div class="result-header">
                    <h4>Extracted Text</h4>
                    <div class="result-meta">
                        <span class="badge badge-info">${wordCount} words</span>
                        <span class="badge badge-success">Confidence: ${typeof confidence === 'number' ? confidence.toFixed(1) + '%' : confidence}</span>
                    </div>
                </div>
                <div class="result-text-area">
                    <pre id="ocrTextOutput">${escapeHtml(text)}</pre>
                </div>
                <div class="result-actions">
                    <button class="btn btn-primary btn-sm" onclick="copyOcrText()">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>
                        Copy Text
                    </button>
                    <button class="btn btn-outline btn-sm" onclick="downloadOcrText()">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
                        Download .txt
                    </button>
                </div>
            `;
            resultDiv.style.display = 'block';
            showToast('Text extracted successfully!', 'success');
        }
    } catch (err) {
        showToast('OCR failed: ' + err.message, 'error');
    } finally {
        btn.disabled = false;
        btn.innerHTML = '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="2"/><path d="M7 7h4v4H7z"/><path d="M7 13h10"/><path d="M7 17h10"/></svg> Extract Text';
    }
}

function copyOcrText() {
    const text = document.getElementById('ocrTextOutput')?.textContent;
    if (text) {
        navigator.clipboard.writeText(text).then(() => showToast('Text copied to clipboard!', 'success'));
    }
}

function downloadOcrText() {
    const text = document.getElementById('ocrTextOutput')?.textContent;
    if (text) {
        const blob = new Blob([text], { type: 'text/plain' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = (ocrFile?.name?.replace(/\.[^.]+$/, '') || 'ocr_result') + '.txt';
        document.body.appendChild(a); a.click(); a.remove();
        URL.revokeObjectURL(url);
        showToast('Text file downloaded!', 'success');
    }
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initOcrTool);
} else {
    initOcrTool();
}
