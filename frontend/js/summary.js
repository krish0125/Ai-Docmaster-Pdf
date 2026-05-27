/* ============================================
   AI DocMaster — AI Summary Logic
   ============================================ */

let summaryFile = null;

function initSummaryTool() {
    const dropzone = document.getElementById('summaryDropzone');
    const fileInput = document.getElementById('summaryFileInput');

    if (!dropzone) return;

    dropzone.addEventListener('click', () => fileInput.click());
    dropzone.addEventListener('dragover', (e) => { e.preventDefault(); dropzone.classList.add('drag-over'); });
    dropzone.addEventListener('dragleave', () => dropzone.classList.remove('drag-over'));
    dropzone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropzone.classList.remove('drag-over');
        setSummaryFile(e.dataTransfer.files[0]);
    });
    fileInput.addEventListener('change', () => { setSummaryFile(fileInput.files[0]); fileInput.value = ''; });
}

function setSummaryFile(file) {
    if (!file || !file.name.toLowerCase().endsWith('.pdf')) {
        showToast('Please select a PDF file', 'error');
        return;
    }
    summaryFile = file;
    const info = document.getElementById('summaryFileInfo');
    if (info) info.innerHTML = `<div class="file-item"><div class="file-icon"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#FF5252" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg></div><div class="file-info"><span class="file-name">${file.name}</span><span class="file-meta">${formatFileSize(file.size)}</span></div></div>`;
    document.getElementById('summaryOptions').style.display = 'block';
}

async function handleSummary() {
    if (!summaryFile) { showToast('Please select a PDF first', 'warning'); return; }

    const mode = document.getElementById('summaryMode')?.value || 'brief';
    const btn = document.getElementById('summaryBtn');
    const resultDiv = document.getElementById('summaryResult');
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner-sm"></span> Generating summary...';

    const formData = new FormData();
    formData.append('file', summaryFile);
    formData.append('mode', mode);

    try {
        const data = await uploadFileWithProgress('/ai/summary', formData, () => {});
        if (data) {
            const resData = data.result || data;
            let displayContent = '';
            const summary = resData.summary || resData.text || 'No summary generated';

            if (mode === 'bullets' && resData.bullets) {
                displayContent = `<ul class="bullet-list">${resData.bullets.map(b => `<li>${escapeHtml(b)}</li>`).join('')}</ul>`;
            } else if (mode === 'bullets' && summary && summary.includes('•')) {
                // Backend returns bullets embedded in summary string with • characters
                const bulletLines = summary.split('\n').filter(l => l.trim());
                displayContent = `<ul class="bullet-list">${bulletLines.map(b => `<li>${escapeHtml(b.replace(/^[•\-\*]\s*/, '').trim())}</li>`).join('')}</ul>`;
            } else if (mode === 'exam_notes' && resData.notes) {
                displayContent = `<div class="exam-notes">${formatExamNotes(resData.notes)}</div>`;
            } else if (mode === 'exam_notes') {
                // Backend returns exam notes embedded in summary string with newlines
                const lines = summary.split('\n');
                let html = '<div class="exam-notes">';
                for (const line of lines) {
                    const trimmed = line.trim();
                    if (!trimmed) continue;
                    if (trimmed.startsWith('📚') || trimmed.startsWith('=')) {
                        html += `<h4 style="margin:1rem 0 0.5rem;color:var(--primary,#6C63FF)">${escapeHtml(trimmed)}</h4>`;
                    } else if (trimmed.startsWith('📌') || trimmed.startsWith('📝') || trimmed.startsWith('📊')) {
                        html += `<h5 style="margin:0.75rem 0 0.25rem;color:var(--text-secondary)">${escapeHtml(trimmed)}</h5>`;
                    } else {
                        html += `<p style="margin:0.25rem 0 0.25rem 1rem">${escapeHtml(trimmed)}</p>`;
                    }
                }
                html += '</div>';
                displayContent = html;
            } else {
                displayContent = `<p class="summary-text">${escapeHtml(summary)}</p>`;
            }

            const modeLabels = { brief: 'Brief Summary', detailed: 'Detailed Summary', bullets: 'Bullet Points', exam_notes: 'Exam Notes' };

            resultDiv.innerHTML = `
                <div class="result-header">
                    <h4>${modeLabels[mode] || 'Summary'}</h4>
                    <div class="result-meta">
                        <span class="badge badge-primary">${mode}</span>
                        <span class="badge badge-info">${resData.word_count || '—'} words</span>
                    </div>
                </div>
                <div class="result-text-area" id="summaryTextOutput">
                    ${displayContent}
                </div>
                <div class="result-actions">
                    <button class="btn btn-primary btn-sm" onclick="copySummary()">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>
                        Copy
                    </button>
                    <button class="btn btn-outline btn-sm" onclick="downloadSummary()">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
                        Download
                    </button>
                </div>
            `;
            resultDiv.style.display = 'block';
            showToast('Summary generated!', 'success');
        }
    } catch (err) {
        showToast('Summary failed: ' + err.message, 'error');
    } finally {
        btn.disabled = false;
        btn.innerHTML = '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/></svg> Generate Summary';
    }
}

function formatExamNotes(notes) {
    if (typeof notes === 'string') return `<p>${escapeHtml(notes)}</p>`;
    if (typeof notes === 'object') {
        let html = '';
        if (notes.key_points) html += `<h5>Key Points</h5><ul>${notes.key_points.map(p => `<li>${escapeHtml(p)}</li>`).join('')}</ul>`;
        if (notes.definitions) html += `<h5>Definitions</h5><ul>${notes.definitions.map(d => `<li>${escapeHtml(d)}</li>`).join('')}</ul>`;
        if (notes.summary) html += `<h5>Summary</h5><p>${escapeHtml(notes.summary)}</p>`;
        return html || `<pre>${JSON.stringify(notes, null, 2)}</pre>`;
    }
    return '';
}

function copySummary() {
    const el = document.getElementById('summaryTextOutput');
    if (el) {
        navigator.clipboard.writeText(el.textContent).then(() => showToast('Summary copied!', 'success'));
    }
}

function downloadSummary() {
    const el = document.getElementById('summaryTextOutput');
    if (el) {
        const blob = new Blob([el.textContent], { type: 'text/plain' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = (summaryFile?.name?.replace(/\.[^.]+$/, '') || 'summary') + '_summary.txt';
        document.body.appendChild(a); a.click(); a.remove();
        URL.revokeObjectURL(url);
    }
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initSummaryTool);
} else {
    initSummaryTool();
}
