/* ============================================
   AI DocMaster — Resume Analyzer Logic
   ============================================ */

let resumeFile = null;

function initResumeTool() {
    const dropzone = document.getElementById('resumeDropzone');
    const fileInput = document.getElementById('resumeFileInput');
    const targetRole = document.getElementById('targetRole');

    if (!dropzone) return;

    dropzone.addEventListener('click', () => fileInput.click());
    fileInput.addEventListener('click', (e) => e.stopPropagation());
    dropzone.addEventListener('dragover', (e) => { e.preventDefault(); dropzone.classList.add('drag-over'); });
    dropzone.addEventListener('dragleave', () => dropzone.classList.remove('drag-over'));
    dropzone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropzone.classList.remove('drag-over');
        setResumeFile(e.dataTransfer.files[0]);
    });
    fileInput.addEventListener('change', () => { setResumeFile(fileInput.files[0]); fileInput.value = ''; });

    if (targetRole) {
        targetRole.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                handleResumeAnalysis(e);
            }
        });
    }
}

function setResumeFile(file) {
    if (!file || !file.name.toLowerCase().endsWith('.pdf')) {
        showToast('Please select a PDF file', 'error');
        return;
    }
    resumeFile = file;
    const info = document.getElementById('resumeFileInfo');
    if (info) info.innerHTML = `<div class="file-item"><div class="file-icon"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#FF5252" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg></div><div class="file-info"><span class="file-name">${file.name}</span><span class="file-meta">${formatFileSize(file.size)}</span></div></div>`;
    document.getElementById('resumeOptions').style.display = 'block';
}

async function handleResumeAnalysis(e) {
    if (e) {
        e.preventDefault();
    }
    if (!resumeFile) { showToast('Please select a resume PDF first', 'warning'); return; }

    const targetRole = document.getElementById('targetRole')?.value.trim() || '';
    const btn = document.getElementById('resumeBtn');
    const resultDiv = document.getElementById('resumeResult');
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner-sm"></span> Analyzing resume...';

    const formData = new FormData();
    formData.append('file', resumeFile);
    if (targetRole) formData.append('target_role', targetRole);

    try {
        const data = await uploadFileWithProgress('/ai/resume-analyze', formData, () => {});
        if (data) {
            const analysisData = data.result || data;
            renderResumeResults(analysisData, resultDiv);
            resultDiv.style.display = 'block';
            showToast('Resume analysis complete!', 'success');
            if (typeof loadStats === 'function') loadStats();
        }
    } catch (err) {
        showToast('Analysis failed: ' + err.message, 'error');
    } finally {
        btn.disabled = false;
        btn.innerHTML = '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg> Analyze Resume';
    }
}

function renderResumeResults(data, container) {
    const atsScore = data.ats_score || 0;
    const skills = data.skills_found || [];
    const missingSkills = data.missing_skills || [];
    const suggestions = data.suggestions || [];
    const formatFeedback = data.format_feedback || '';
    const overallRating = data.overall_rating || '';

    // Determine score color
    let scoreColor = '#FF5252';
    let scoreLabel = 'Needs Work';
    if (atsScore >= 80) { scoreColor = '#00E676'; scoreLabel = 'Excellent'; }
    else if (atsScore >= 60) { scoreColor = '#00D4FF'; scoreLabel = 'Good'; }
    else if (atsScore >= 40) { scoreColor = '#FFD600'; scoreLabel = 'Fair'; }

    container.innerHTML = `
        <div class="resume-results">
            <!-- ATS Score -->
            <div class="ats-score-card">
                <div class="score-circle" style="--score: ${atsScore}; --color: ${scoreColor}">
                    <svg viewBox="0 0 120 120" class="score-svg">
                        <circle cx="60" cy="60" r="50" fill="none" stroke="rgba(255,255,255,0.1)" stroke-width="8"/>
                        <circle cx="60" cy="60" r="50" fill="none" stroke="${scoreColor}" stroke-width="8"
                            stroke-dasharray="${Math.PI * 100}" 
                            stroke-dashoffset="${Math.PI * 100 * (1 - atsScore / 100)}"
                            stroke-linecap="round" transform="rotate(-90 60 60)"/>
                    </svg>
                    <div class="score-value">
                        <span class="score-number">${atsScore}</span>
                        <span class="score-label">${scoreLabel}</span>
                    </div>
                </div>
                <h4>ATS Compatibility Score</h4>
            </div>

            <!-- Skills Found -->
            <div class="resume-section">
                <h4><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#00E676" stroke-width="2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg> Skills Detected</h4>
                <div class="skills-tags">
                    ${skills.map(s => `<span class="skill-tag found">${escapeHtml(s)}</span>`).join('')}
                    ${skills.length === 0 ? '<p class="text-muted">No specific skills detected</p>' : ''}
                </div>
            </div>

            <!-- Missing Skills -->
            ${missingSkills.length > 0 ? `
            <div class="resume-section">
                <h4><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#FF5252" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg> Missing Skills</h4>
                <div class="skills-tags">
                    ${missingSkills.map(s => `<span class="skill-tag missing">${escapeHtml(s)}</span>`).join('')}
                </div>
            </div>` : ''}

            <!-- Suggestions -->
            ${suggestions.length > 0 ? `
            <div class="resume-section">
                <h4><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#FFD600" stroke-width="2"><path d="M12 2L2 7l10 5 10-5-10-5z"/><path d="M2 17l10 5 10-5"/><path d="M2 12l10 5 10-5"/></svg> Improvement Suggestions</h4>
                <ul class="suggestions-list">
                    ${suggestions.map(s => `<li>${renderMarkdown(s)}</li>`).join('')}
                </ul>
            </div>` : ''}

            <!-- Format Feedback -->
            ${formatFeedback ? `
            <div class="resume-section">
                <h4><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#00D4FF" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="2"/><line x1="9" y1="3" x2="9" y2="21"/></svg> Format & Structure</h4>
                <div class="resume-markdown-content">${renderMarkdown(formatFeedback)}</div>
            </div>` : ''}

            <!-- Overall -->
            ${overallRating ? `
            <div class="resume-section overall">
                <h4>Overall Assessment</h4>
                <div class="resume-markdown-content">${renderMarkdown(overallRating)}</div>
            </div>` : ''}

            <div class="result-actions">
                <button class="btn btn-primary btn-sm" onclick="downloadResumeReport()">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
                    Download Report
                </button>
            </div>
        </div>
    `;
}

function downloadResumeReport() {
    const el = document.querySelector('.resume-results');
    if (el) {
        const text = el.textContent.replace(/\s+/g, ' ').trim();
        const blob = new Blob([text], { type: 'text/plain' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'resume_analysis_report.txt';
        document.body.appendChild(a); a.click(); a.remove();
        URL.revokeObjectURL(url);
    }
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initResumeTool);
} else {
    initResumeTool();
}
