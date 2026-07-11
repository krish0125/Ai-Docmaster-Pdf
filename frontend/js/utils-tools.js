/**
 * utils-tools.js — Phase 5 (OCR/Scanner), Phase 8 (Utilities), Phase 9 (Cloud storage)
 */

'use strict';

(function () {
  function setupDz(dzId, inputId, infoId, optId) {
    const dz = document.getElementById(dzId);
    const inp = document.getElementById(inputId);
    const info = document.getElementById(infoId);
    const opt = document.getElementById(optId);
    if (!dz || !inp) return null;

    let selectedFile = null;

    dz.addEventListener('click', () => inp.click());
    dz.addEventListener('dragover', e => { e.preventDefault(); dz.classList.add('drag-over'); });
    dz.addEventListener('dragleave', () => dz.classList.remove('drag-over'));
    dz.addEventListener('drop', e => {
      e.preventDefault(); dz.classList.remove('drag-over');
      if (e.dataTransfer.files[0]) setFile(e.dataTransfer.files[0]);
    });
    inp.addEventListener('change', () => { if (inp.files[0]) setFile(inp.files[0]); });

    function setFile(f) {
      selectedFile = f;
      if (info) info.innerHTML = `<div class="file-selected-info">📄 <strong>${f.name}</strong></div>`;
      if (opt) opt.style.display = 'block';
    }
    return { getFile: () => selectedFile };
  }

  function showResult(resId, data, btnId) {
    const res = document.getElementById(resId);
    const btn = document.getElementById(btnId);
    if (btn) btn.disabled = false;
    if (!res) return;
    res.style.display = 'block';

    if (data.error) {
      res.innerHTML = `<div class="alert alert-error">❌ ${data.error}</div>`;
    } else {
      let dlHtml = '';
      if (data.download_url) {
        dlHtml = `<a href="${API_BASE_URL}${data.download_url}" class="btn btn-primary" download>Download File</a>`;
      } else if (data.images) {
        dlHtml = data.images.map((img, i) =>
          `<a href="${API_BASE_URL}${img.download_url}" class="btn btn-secondary" style="margin:4px" download>Page ${img.page} Image</a>`
        ).join('');
      }

      res.innerHTML = `
        <div class="result-card success">
          <h4>✅ Success!</h4>
          <p>${data.message || 'Operation completed successfully.'}</p>
          ${dlHtml}
          ${data.result && typeof data.result === 'string' ? `<pre style="white-space:pre-wrap;background:#f5f5f5;padding:1rem;margin-top:1rem;border-radius:4px">${data.result}</pre>` : ''}
          ${data.result && typeof data.result === 'object' && data.result.text ? `<pre style="white-space:pre-wrap;background:#f5f5f5;padding:1rem;margin-top:1rem;border-radius:4px">${data.result.text}</pre>` : ''}
          ${data.metadata ? `<pre style="white-space:pre-wrap;background:#f5f5f5;padding:1rem;margin-top:1rem;border-radius:4px">${JSON.stringify(data.metadata, null, 2)}</pre>` : ''}
          ${data.stats ? `<pre style="white-space:pre-wrap;background:#f5f5f5;padding:1rem;margin-top:1rem;border-radius:4px">${JSON.stringify(data.stats, null, 2)}</pre>` : ''}
          ${data.tables ? `<pre style="white-space:pre-wrap;background:#f5f5f5;padding:1rem;margin-top:1rem;border-radius:4px">${JSON.stringify(data.tables, null, 2)}</pre>` : ''}
        </div>`;
    }
  }

  async function callApi(prefix, endpoint, formData, resId, btnId) {
    const btn = document.getElementById(btnId);
    if (btn) btn.disabled = true;
    try {
      const token = localStorage.getItem('token');
      const headers = { Authorization: `Bearer ${token}` };
      const body = formData instanceof FormData ? formData : JSON.stringify(formData);
      if (!(formData instanceof FormData)) {
        headers['Content-Type'] = 'application/json';
      }
      const resp = await fetch(`${API_BASE_URL}/${prefix}/${endpoint}`, {
        method: 'POST',
        headers,
        body
      });
      const data = await resp.json();
      showResult(resId, data, btnId);
    } catch (e) {
      showResult(resId, { error: e.message }, btnId);
    }
  }

  // ── Phase 5: Handwriting OCR ──
  window.initHandwriting = function () {
    const dz = setupDz('hwDropzone', 'hwFileInput', 'hwFileInfo', 'hwOptions');
    window.handleHandwriting = async function () {
      const f = dz.getFile(); if (!f) return alert('Select an image first.');
      const fd = new FormData(); fd.append('file', f);
      await callApi('ocr', 'handwriting', fd, 'hwResult', 'hwBtn');
    };
  };

  // ── Phase 5: Extract Tables ──
  window.initExtractTables = function () {
    const dz = setupDz('tablesDropzone', 'tablesFileInput', 'tablesFileInfo', 'tablesOptions');
    window.handleExtractTables = async function () {
      const f = dz.getFile(); if (!f) return alert('Select a PDF first.');
      const fd = new FormData(); fd.append('file', f);
      await callApi('ocr', 'extract-tables', fd, 'tablesResult', 'tablesBtn');
    };
  };

  // ── Phase 5: Extract Images ──
  window.initExtractImages = function () {
    const dz = setupDz('imagesDropzone', 'imagesFileInput', 'imagesFileInfo', 'imagesOptions');
    window.handleExtractImages = async function () {
      const f = dz.getFile(); if (!f) return alert('Select a PDF first.');
      const fd = new FormData(); fd.append('file', f);
      await callApi('ocr', 'extract-images', fd, 'imagesResult', 'imagesBtn');
    };
  };

  // ── Phase 5: Multi-language OCR ──
  window.initMultilangOcr = function () {
    const dz = setupDz('mlDropzone', 'mlFileInput', 'mlFileInfo', 'mlOptions');
    window.handleMultilangOcr = async function () {
      const f = dz.getFile(); if (!f) return alert('Select a file first.');
      const fd = new FormData(); fd.append('file', f);
      fd.append('lang', document.getElementById('mlLang').value);
      await callApi('ocr', 'multilang-ocr', fd, 'mlResult', 'mlBtn');
    };
  };

  // ── Phase 8: QR Code ──
  window.handleGenerateQr = async function () {
    const data = document.getElementById('qrData').value;
    if (!data) return alert('Text/URL required.');
    const body = { data, size: parseInt(document.getElementById('qrSize').value) };
    await callApi('utils', 'qr', body, 'qrResult', 'qrBtn');
  };

  // ── Phase 8: Barcode ──
  window.handleGenerateBarcode = async function () {
    const data = document.getElementById('bcData').value;
    if (!data) return alert('Data required.');
    const body = { data, type: document.getElementById('bcType').value };
    await callApi('utils', 'barcode', body, 'bcResult', 'bcBtn');
  };

  // ── Phase 8: PDF Metadata ──
  window.initPdfMeta = function () {
    const dz = setupDz('metaViewDropzone', 'metaViewFileInput', 'metaViewFileInfo', 'metaViewOptions');
    window.handleViewMetadata = async function () {
      const f = dz.getFile(); if (!f) return alert('Select a PDF first.');
      const fd = new FormData(); fd.append('file', f);
      await callApi('utils', 'pdf-metadata', fd, 'metaViewResult', 'metaViewBtn');
    };
    window.handleSetMetadata = async function () {
      const f = dz.getFile(); if (!f) return alert('Select a PDF first.');
      const fd = new FormData(); fd.append('file', f);
      fd.append('title', document.getElementById('metaTitle').value);
      fd.append('author', document.getElementById('metaAuthor').value);
      fd.append('subject', document.getElementById('metaSubject').value);
      fd.append('keywords', document.getElementById('metaKeywords').value);
      await callApi('utils', 'set-metadata', fd, 'metaViewResult', 'metaViewSetBtn');
    };
  };

  // ── Phase 8: Password Generator ──
  window.handleGeneratePassword = async function () {
    const body = {
      length: parseInt(document.getElementById('passLength').value),
      upper: document.getElementById('passUpper').checked,
      lower: document.getElementById('passLower').checked,
      digits: document.getElementById('passDigits').checked,
      special: document.getElementById('passSpecial').checked
    };
    const btn = document.getElementById('passBtn');
    if (btn) btn.disabled = true;
    try {
      const token = localStorage.getItem('token');
      const resp = await fetch(`${API_BASE_URL}/utils/password`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
        body: JSON.stringify(body)
      });
      const resData = await resp.json();
      const res = document.getElementById('passResult');
      if (res) {
        res.style.display = 'block';
        res.innerHTML = `
          <div class="result-card success">
            <h4>Password Generated (${resData.result.strength}):</h4>
            <div style="font-family:monospace;font-size:1.2rem;background:#eee;padding:10px;border-radius:4px;word-break:break-all">${resData.result.password}</div>
          </div>`;
      }
    } catch (e) {
      alert(e.message);
    } finally {
      if (btn) btn.disabled = false;
    }
  };

  // ── Phase 8: Web to PDF ──
  window.handleWebToPdf = async function () {
    const url = document.getElementById('webUrl').value;
    if (!url) return alert('URL required.');
    await callApi('utils', 'web-to-pdf', { url }, 'webResult', 'webBtn');
  };

  // ── Phase 9: Cloud Integrations ──
  window.connectCloud = async function (provider) {
    try {
      const token = localStorage.getItem('token');
      const resp = await fetch(`${API_BASE_URL}/productivity/${provider}/auth`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      const data = await resp.json();
      if (data.auth_url) {
        window.open(data.auth_url, '_blank');
      } else {
        alert(data.error || 'Authentication error.');
      }
    } catch (e) {
      alert(e.message);
    }
  };

})();
