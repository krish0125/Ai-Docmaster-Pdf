/**
 * pdf-edit.js — Phase 3 (PDF Editing) & Phase 4 (PDF Security)
 * Handles PDF edits like text overlay, watermark, lock/unlock, sign, redact, etc.
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
      res.innerHTML = `
        <div class="result-card success">
          <h4>✅ Success!</h4>
          <p>${data.message || 'Operation completed successfully.'}</p>
          ${data.download_url ? `<a href="${API_BASE_URL}${data.download_url}" class="btn btn-primary" download>Download PDF</a>` : ''}
        </div>`;
    }
  }

  async function callApi(prefix, endpoint, formData, resId, btnId) {
    const btn = document.getElementById(btnId);
    if (btn) btn.disabled = true;
    try {
      const token = localStorage.getItem('token');
      const resp = await fetch(`${API_BASE_URL}/${prefix}/${endpoint}`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
        body: formData
      });
      const data = await resp.json();
      showResult(resId, data, btnId);
    } catch (e) {
      showResult(resId, { error: e.message }, btnId);
    }
  }

  // ── Phase 3: Add Text ──
  window.initAddText = function () {
    const dz = setupDz('addTextDropzone', 'addTextFileInput', 'addTextFileInfo', 'addTextOptions');
    window.handleAddText = async function () {
      const f = dz.getFile(); if (!f) return alert('Select a PDF first.');
      const fd = new FormData(); fd.append('file', f);
      fd.append('text', document.getElementById('addTextInput').value);
      fd.append('x', document.getElementById('addTextX').value);
      fd.append('y', document.getElementById('addTextY').value);
      fd.append('font_size', document.getElementById('addTextSize').value);
      fd.append('color', document.getElementById('addTextColor').value);
      fd.append('pages', document.getElementById('addTextPages').value);
      await callApi('edit', 'add-text', fd, 'addTextResult', 'addTextBtn');
    };
  };

  // ── Phase 3: Add Image ──
  window.initAddImage = function () {
    const dz = setupDz('addImageDropzone', 'addImageFileInput', 'addImageFileInfo', 'addImageOptions');
    window.handleAddImage = async function () {
      const f = dz.getFile(); if (!f) return alert('Select a PDF first.');
      const imgInp = document.getElementById('addImageInput');
      if (!imgInp.files[0]) return alert('Please select a stamp image to overlay.');
      const fd = new FormData();
      fd.append('file', f);
      fd.append('image', imgInp.files[0]);
      fd.append('x', document.getElementById('addImageX').value);
      fd.append('y', document.getElementById('addImageY').value);
      fd.append('width', document.getElementById('addImageW').value);
      fd.append('pages', document.getElementById('addImagePages').value);
      await callApi('edit', 'add-image', fd, 'addImageResult', 'addImageBtn');
    };
  };

  // ── Phase 3: Highlight ──
  window.initHighlight = function () {
    const dz = setupDz('highlightDropzone', 'highlightFileInput', 'highlightFileInfo', 'highlightOptions');
    window.handleHighlight = async function () {
      const f = dz.getFile(); if (!f) return alert('Select a PDF first.');
      const fd = new FormData(); fd.append('file', f);
      fd.append('x', document.getElementById('highlightX').value);
      fd.append('y', document.getElementById('highlightY').value);
      fd.append('width', document.getElementById('highlightW').value);
      fd.append('height', document.getElementById('highlightH').value);
      fd.append('color', document.getElementById('highlightColor').value);
      fd.append('opacity', document.getElementById('highlightOpacity').value);
      fd.append('pages', document.getElementById('highlightPages').value);
      await callApi('edit', 'highlight', fd, 'highlightResult', 'highlightBtn');
    };
  };

  // ── Phase 3: Header/Footer ──
  window.initHeaderFooter = function () {
    const dz = setupDz('hfDropzone', 'hfFileInput', 'hfFileInfo', 'hfOptions');
    window.handleHeaderFooter = async function () {
      const f = dz.getFile(); if (!f) return alert('Select a PDF first.');
      const fd = new FormData(); fd.append('file', f);
      fd.append('header', document.getElementById('hfHeader').value);
      fd.append('footer', document.getElementById('hfFooter').value);
      fd.append('font_size', document.getElementById('hfSize').value);
      await callApi('edit', 'header-footer', fd, 'hfResult', 'hfBtn');
    };
  };

  // ── Phase 3: Page Numbers ──
  window.initPageNumbers = function () {
    const dz = setupDz('pnumDropzone', 'pnumFileInput', 'pnumFileInfo', 'pnumOptions');
    window.handlePageNumbers = async function () {
      const f = dz.getFile(); if (!f) return alert('Select a PDF first.');
      const fd = new FormData(); fd.append('file', f);
      fd.append('position', document.getElementById('pnumPos').value);
      fd.append('font_size', document.getElementById('pnumSize').value);
      fd.append('start', document.getElementById('pnumStart').value);
      await callApi('edit', 'page-numbers', fd, 'pnumResult', 'pnumBtn');
    };
  };

  // ── Phase 4: Lock PDF ──
  window.initLockPdf = function () {
    const dz = setupDz('lockDropzone', 'lockFileInput', 'lockFileInfo', 'lockOptions');
    window.handleLockPdf = async function () {
      const f = dz.getFile(); if (!f) return alert('Select a PDF first.');
      const pass = document.getElementById('lockPassword').value;
      if (!pass) return alert('Password required.');
      const fd = new FormData(); fd.append('file', f); fd.append('password', pass);
      await callApi('security', 'lock', fd, 'lockResult', 'lockBtn');
    };
  };

  // ── Phase 4: Unlock PDF ──
  window.initUnlockPdf = function () {
    const dz = setupDz('unlockDropzone', 'unlockFileInput', 'unlockFileInfo', 'unlockOptions');
    window.handleUnlockPdf = async function () {
      const f = dz.getFile(); if (!f) return alert('Select a PDF first.');
      const pass = document.getElementById('unlockPassword').value;
      const fd = new FormData(); fd.append('file', f); fd.append('password', pass);
      await callApi('security', 'unlock', fd, 'unlockResult', 'unlockBtn');
    };
  };

  // ── Phase 4: Watermark ──
  window.initWatermark = function () {
    const dz = setupDz('watermarkDropzone', 'watermarkFileInput', 'watermarkFileInfo', 'watermarkOptions');
    window.handleWatermark = async function () {
      const f = dz.getFile(); if (!f) return alert('Select a PDF first.');
      const fd = new FormData(); fd.append('file', f);
      fd.append('text', document.getElementById('watermarkText').value);
      fd.append('opacity', document.getElementById('watermarkOpacity').value);
      fd.append('font_size', document.getElementById('watermarkSize').value);
      fd.append('color', document.getElementById('watermarkColor').value);
      await callApi('security', 'watermark', fd, 'watermarkResult', 'watermarkBtn');
    };
  };

  // ── Phase 4: Flatten ──
  window.initFlatten = function () {
    const dz = setupDz('flattenDropzone', 'flattenFileInput', 'flattenFileInfo', 'flattenOptions');
    window.handleFlatten = async function () {
      const f = dz.getFile(); if (!f) return alert('Select a PDF first.');
      const fd = new FormData(); fd.append('file', f);
      await callApi('security', 'flatten', fd, 'flattenResult', 'flattenBtn');
    };
  };

  // ── Phase 4: Remove Metadata ──
  window.initRemoveMeta = function () {
    const dz = setupDz('metaDropzone', 'metaFileInput', 'metaFileInfo', 'metaOptions');
    window.handleRemoveMeta = async function () {
      const f = dz.getFile(); if (!f) return alert('Select a PDF first.');
      const fd = new FormData(); fd.append('file', f);
      await callApi('security', 'remove-metadata', fd, 'metaResult', 'metaBtn');
    };
  };

  // ── Phase 4: Sign ──
  window.initSign = function () {
    const dz = setupDz('signDropzone', 'signFileInput', 'signFileInfo', 'signOptions');
    window.handleSign = async function () {
      const f = dz.getFile(); if (!f) return alert('Select a PDF first.');
      const fd = new FormData(); fd.append('file', f);
      fd.append('signer_name', document.getElementById('signSigner').value);
      fd.append('date', document.getElementById('signDate').value);
      fd.append('page', document.getElementById('signPage').value);
      await callApi('security', 'sign', fd, 'signResult', 'signBtn');
    };
  };

  // ── Phase 4: Redact ──
  window.initRedact = function () {
    const dz = setupDz('redactDropzone', 'redactFileInput', 'redactFileInfo', 'redactOptions');
    window.handleRedact = async function () {
      const f = dz.getFile(); if (!f) return alert('Select a PDF first.');
      const fd = new FormData(); fd.append('file', f);
      fd.append('x', document.getElementById('redactX').value);
      fd.append('y', document.getElementById('redactY').value);
      fd.append('width', document.getElementById('redactW').value);
      fd.append('height', document.getElementById('redactH').value);
      fd.append('pages', document.getElementById('redactPages').value);
      await callApi('security', 'redact', fd, 'redactResult', 'redactBtn');
    };
  };

  // ── Phase 3: Whiteout ──
  window.initWhiteout = function () {
    const dz = setupDz('whiteoutDropzone', 'whiteoutFileInput', 'whiteoutFileInfo', 'whiteoutOptions');
    window.handleWhiteout = async function () {
      const f = dz.getFile(); if (!f) return alert('Select a PDF first.');
      const fd = new FormData(); fd.append('file', f);
      fd.append('x', document.getElementById('whiteoutX').value);
      fd.append('y', document.getElementById('whiteoutY').value);
      fd.append('width', document.getElementById('whiteoutW').value);
      fd.append('height', document.getElementById('whiteoutH').value);
      fd.append('pages', document.getElementById('whiteoutPages').value);
      await callApi('edit', 'whiteout', fd, 'whiteoutResult', 'whiteoutBtn');
    };
  };

})();
