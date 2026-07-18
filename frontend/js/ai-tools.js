/**
 * ai-tools.js — Phase 6: Writing, QA, Quiz, Business, Student AI tools
 */
'use strict';

(function () {
  const API = '/api/ai';

  async function callAI(endpoint, formData, resultId, btnId, renderFn) {
    const btn = document.getElementById(btnId);
    const res = document.getElementById(resultId);
    if (btn) { btn.disabled = true; btn.textContent = 'Processing…'; }
    if (res) res.style.display = 'none';
    try {
      const token = localStorage.getItem('token');
      const headers = { Authorization: `Bearer ${token}` };
      const customKey = localStorage.getItem('user_gemini_key');
      if (customKey) {
        headers['X-Gemini-Key'] = customKey.trim();
      }
      const resp  = await window.safeFetch(`${API_BASE_URL}/ai/${endpoint}`, {
        method: 'POST',
        headers: headers,
        body: formData,
      });
      const data = await resp.json();
      if (res) {
        res.style.display = 'block';
        res.innerHTML = renderFn ? renderFn(data) : defaultRender(data);
      }
    } catch (err) {
      if (res) { res.style.display = 'block'; res.innerHTML = errCard(err.message); }
    } finally {
      if (btn) { btn.disabled = false; btn.textContent = btn.dataset.label || 'Run'; }
    }
  }

  function errCard(msg) {
    return `<div class="alert alert-error">❌ ${msg}</div>`;
  }

  function defaultRender(data) {
    if (data.error) return errCard(data.error);
    const r = data.result;
    if (typeof r === 'string') {
      return `<div class="result-card"><pre style="white-space:pre-wrap;font-family:inherit">${escHtml(r)}</pre></div>`;
    }
    if (Array.isArray(r)) {
      return `<div class="result-card"><ol>${r.map(x =>
        `<li>${escHtml(typeof x === 'string' ? x : JSON.stringify(x, null, 2))}</li>`
      ).join('')}</ol></div>`;
    }
    return `<div class="result-card"><pre style="white-space:pre-wrap;font-family:monospace;font-size:.85rem">${
      escHtml(JSON.stringify(r, null, 2))}</pre></div>`;
  }

  function escHtml(s) {
    return String(s)
      .replace(/&/g,'&amp;').replace(/</g,'&lt;')
      .replace(/>/g,'&gt;').replace(/"/g,'&quot;');
  }

  function setupDz(dzId, inputId, infoId, optId, multi) {
    const dz   = document.getElementById(dzId);
    const inp  = document.getElementById(inputId);
    const info = document.getElementById(infoId);
    const opt  = document.getElementById(optId);
    if (!dz || !inp) return null;
    let files = [];

    dz.addEventListener('click', () => inp.click());
    dz.addEventListener('dragover', e => { e.preventDefault(); dz.classList.add('drag-over'); });
    dz.addEventListener('dragleave', () => dz.classList.remove('drag-over'));
    dz.addEventListener('drop', e => {
      e.preventDefault(); dz.classList.remove('drag-over');
      setFiles(multi ? [...e.dataTransfer.files] : [e.dataTransfer.files[0]]);
    });
    inp.addEventListener('change', () => setFiles(multi ? [...inp.files] : [inp.files[0]]));

    function setFiles(fs) {
      files = fs.filter(Boolean);
      if (!files.length) return;
      const names = files.map(f => f.name).join(', ');
      if (info) info.innerHTML = `<div class="file-selected-info">📄 <strong>${names}</strong></div>`;
      if (opt)  opt.style.display = 'block';
    }
    return { getFile: () => files[0], getFiles: () => files };
  }

  // ── Explain PDF ─────────────────────────────────────────────────────────────
  window.initExplainTool = function () {
    const dz = setupDz('explainDz', 'explainInput', 'explainInfo', 'explainOptions');
    window.handleExplain = async () => {
      const f = dz?.getFile(); if (!f) return alert('Upload a PDF first.');
      const fd = new FormData(); fd.append('file', f);
      await callAI('explain', fd, 'explainResult', 'explainBtn');
    };
  };

  // ── Keywords ────────────────────────────────────────────────────────────────
  window.initKeywordsTool = function () {
    const dz = setupDz('keywordsDz', 'keywordsInput', 'keywordsInfo', 'keywordsOptions');
    window.handleKeywords = async () => {
      const f = dz?.getFile(); if (!f) return alert('Upload a PDF first.');
      const fd = new FormData(); fd.append('file', f);
      await callAI('keywords', fd, 'keywordsResult', 'keywordsBtn', data => {
        if (data.error) return errCard(data.error);
        const kws = Array.isArray(data.result) ? data.result : [];
        return `<div class="result-card">
          <div class="keywords-grid">${kws.map(k =>
            `<div class="keyword-item"><strong>${escHtml(k.term || k)}</strong>${k.definition
              ? `<p>${escHtml(k.definition)}</p>` : ''}</div>`
          ).join('')}</div></div>`;
      });
    };
  };

  // ── Quiz (T/F) ──────────────────────────────────────────────────────────────
  window.initQuizTool = function () {
    const dz = setupDz('quizDz', 'quizInput', 'quizInfo', 'quizOptions');
    window.handleQuiz = async () => {
      const f = dz?.getFile(); if (!f) return alert('Upload a PDF first.');
      const fd = new FormData(); fd.append('file', f);
      fd.append('count', document.getElementById('quizCount')?.value || '10');
      await callAI('quiz', fd, 'quizResult', 'quizBtn', data => {
        if (data.error) return errCard(data.error);
        const qs = Array.isArray(data.result) ? data.result : [];
        return `<div class="result-card"><ol class="quiz-list">${qs.map((q, i) => `
          <li class="quiz-item">
            <p><strong>Q${i+1}:</strong> ${escHtml(q.question || q)}</p>
            ${q.answer !== undefined ? `<p class="quiz-answer">Answer: <strong>${q.answer ? 'TRUE ✅' : 'FALSE ❌'}</strong></p>` : ''}
            ${q.explanation ? `<p class="quiz-explain"><em>${escHtml(q.explanation)}</em></p>` : ''}
          </li>`).join('')}</ol></div>`;
      });
    };
  };

  // ── MCQ ─────────────────────────────────────────────────────────────────────
  window.initMcqTool = function () {
    const dz = setupDz('mcqDz', 'mcqInput', 'mcqInfo', 'mcqOptions');
    window.handleMcq = async () => {
      const f = dz?.getFile(); if (!f) return alert('Upload a PDF first.');
      const fd = new FormData(); fd.append('file', f);
      fd.append('count', document.getElementById('mcqCount')?.value || '10');
      await callAI('mcq', fd, 'mcqResult', 'mcqBtn', data => {
        if (data.error) return errCard(data.error);
        const qs = Array.isArray(data.result) ? data.result : [];
        return `<div class="result-card"><ol class="quiz-list">${qs.map((q, i) => `
          <li class="quiz-item">
            <p><strong>Q${i+1}:</strong> ${escHtml(q.question || q)}</p>
            ${Array.isArray(q.options) ? `<ul>${q.options.map(o =>
              `<li ${q.correct && o.startsWith(q.correct) ? 'style="color:#6C63FF;font-weight:bold"' : ''}>${escHtml(o)}</li>`
            ).join('')}</ul>` : ''}
            ${q.explanation ? `<p class="quiz-explain"><em>${escHtml(q.explanation)}</em></p>` : ''}
          </li>`).join('')}</ol></div>`;
      });
    };
  };

  // ── Writing tools (Grammar, Improve, Proofread, Translate, Rewrite, Tone) ──

  function textToolHandler(endpoint, inputTextId, fileInputId, fileInfoId, fileOptId, resultId, btnId, extraFdFn) {
    const dz = setupDz(fileInputId + 'Dz', fileInputId, fileInfoId, fileOptId);
    return async function () {
      const rawText = document.getElementById(inputTextId)?.value?.trim() || '';
      const f       = dz?.getFile();
      if (!rawText && !f) return alert('Enter text or upload a PDF.');
      const fd = new FormData();
      if (rawText) fd.append('text', rawText);
      else         fd.append('file', f);
      if (extraFdFn) extraFdFn(fd);
      await callAI(endpoint, fd, resultId, btnId);
    };
  }

  window.handleGrammarCheck = textToolHandler('check-grammar', 'grammarText',
    'grammarFile', 'grammarFileInfo', 'grammarFileOpt', 'grammarResult', 'grammarBtn');
  window.handleImproveWriting = textToolHandler('improve-writing', 'improveText',
    'improveFile', 'improveFileInfo', 'improveFileOpt', 'improveResult', 'improveBtn');
  window.handleProofread = textToolHandler('proofread', 'proofreadText',
    'proofreadFile', 'proofreadFileInfo', 'proofreadFileOpt', 'proofreadResult', 'proofreadBtn');
  window.handleTranslate = textToolHandler('translate', 'translateText',
    'translateFile', 'translateFileInfo', 'translateFileOpt', 'translateResult', 'translateBtn',
    fd => fd.append('lang', document.getElementById('translateLang')?.value || 'Spanish'));
  window.handleRewrite = textToolHandler('rewrite', 'rewriteText',
    'rewriteFile', 'rewriteFileInfo', 'rewriteFileOpt', 'rewriteResult', 'rewriteBtn',
    fd => fd.append('style', document.getElementById('rewriteStyle')?.value || 'formal'));
  window.handleChangeTone = textToolHandler('change-tone', 'toneText',
    'toneFile', 'toneFileInfo', 'toneFileOpt', 'toneResult', 'toneBtn',
    fd => fd.append('tone', document.getElementById('toneSelect')?.value || 'professional'));

  // ── Business Tools ──────────────────────────────────────────────────────────
  function bizHandler(endpoint, dzPrefix, resultId, btnId) {
    const dz = setupDz(dzPrefix + 'Dz', dzPrefix + 'Input', dzPrefix + 'Info', dzPrefix + 'Options');
    return async function () {
      const f = dz?.getFile(); if (!f) return alert('Upload a PDF first.');
      const fd = new FormData(); fd.append('file', f);
      await callAI(endpoint, fd, resultId, btnId);
    };
  }

  window.handleAnalyzeContract  = bizHandler('analyze-contract',  'contract',  'contractResult',  'contractBtn');
  window.handleReadInvoice       = bizHandler('read-invoice',       'invoice',   'invoiceResult',   'invoiceBtn');
  window.handleAnalyzeFinancial  = bizHandler('analyze-financial',  'financial', 'financialResult', 'financialBtn');
  window.handleReviewLegal       = bizHandler('review-legal',       'legal',     'legalResult',     'legalBtn');

  // ── Student Tools ───────────────────────────────────────────────────────────
  window.initAssignmentTool = function () {
    const dz = setupDz('assignmentDz', 'assignmentInput', 'assignmentInfo', 'assignmentOptions');
    window.handleAssignment = async () => {
      const f    = dz?.getFile(); if (!f) return alert('Upload a PDF first.');
      const task = document.getElementById('assignmentTask')?.value || '';
      const fd   = new FormData(); fd.append('file', f); fd.append('task', task);
      await callAI('assignment-helper', fd, 'assignmentResult', 'assignmentBtn');
    };
  };

  window.initResearchTool = function () {
    const dz = setupDz('researchDz', 'researchInput', 'researchInfo', 'researchOptions');
    window.handleResearch = async () => {
      const f     = dz?.getFile(); if (!f) return alert('Upload a PDF first.');
      const topic = document.getElementById('researchTopic')?.value || '';
      const fd    = new FormData(); fd.append('file', f); fd.append('topic', topic);
      await callAI('research-assistant', fd, 'researchResult', 'researchBtn');
    };
  };

  window.initCoverLetterTool = function () {
    const dz = setupDz('coverLetterDz', 'coverLetterInput', 'coverLetterInfo', 'coverLetterOptions');
    window.handleCoverLetter = async () => {
      const f  = dz?.getFile(); if (!f) return alert('Upload resume PDF first.');
      const jd = document.getElementById('coverLetterJD')?.value || '';
      const fd = new FormData(); fd.append('file', f); fd.append('job_description', jd);
      await callAI('cover-letter', fd, 'coverLetterResult', 'coverLetterBtn');
    };
  };

  window.initInterviewTool = function () {
    const dz = setupDz('interviewDz', 'interviewInput', 'interviewInfo', 'interviewOptions');
    window.handleInterview = async () => {
      const f = dz?.getFile(); if (!f) return alert('Upload resume PDF first.');
      const fd = new FormData(); fd.append('file', f);
      await callAI('interview-questions', fd, 'interviewResult', 'interviewBtn');
    };
  };
})();
