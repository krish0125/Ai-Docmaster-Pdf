/**
 * image-tools.js — Phase 7 (Image Tools)
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
          ${data.download_url ? `<a href="${API_BASE_URL}${data.download_url}" class="btn btn-primary" download>Download Image</a>` : ''}
        </div>`;
    }
  }

  async function callApi(endpoint, formData, resId, btnId) {
    const btn = document.getElementById(btnId);
    if (btn) btn.disabled = true;
    try {
      const token = localStorage.getItem('token');
      const resp = await window.safeFetch(`${API_BASE_URL}/image/${endpoint}`, {
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

  // ── Resize ──
  window.initResizeImg = function () {
    const dz = setupDz('resizeImgDz', 'resizeImgInput', 'resizeImgInfo', 'resizeImgOptions');
    window.handleResizeImg = async function () {
      const f = dz.getFile(); if (!f) return alert('Select an image first.');
      const fd = new FormData(); fd.append('file', f);
      fd.append('width', document.getElementById('resizeImgW').value);
      fd.append('height', document.getElementById('resizeImgH').value);
      fd.append('keep_ratio', document.getElementById('resizeImgRatio').checked);
      await callApi('resize', fd, 'resizeImgResult', 'resizeImgBtn');
    };
  };

  // ── Convert Format ──
  window.initConvertImg = function () {
    const dz = setupDz('convertImgDz', 'convertImgInput', 'convertImgInfo', 'convertImgOptions');
    window.handleConvertImg = async function () {
      const f = dz.getFile(); if (!f) return alert('Select an image first.');
      const fd = new FormData(); fd.append('file', f);
      fd.append('format', document.getElementById('convertImgFmt').value);
      await callApi('convert-format', fd, 'convertImgResult', 'convertImgBtn');
    };
  };

  // ── Filters ──
  window.initFilterImg = function () {
    const dz = setupDz('filterImgDz', 'filterImgInput', 'filterImgInfo', 'filterImgOptions');
    window.handleFilterImg = async function () {
      const f = dz.getFile(); if (!f) return alert('Select an image first.');
      const fd = new FormData(); fd.append('file', f);
      fd.append('filter', document.getElementById('filterImgSelect').value);
      await callApi('filter', fd, 'filterImgResult', 'filterImgBtn');
    };
  };

  // ── Background Removal ──
  window.initNoBgImg = function () {
    const dz = setupDz('nobgImgDz', 'nobgImgInput', 'nobgImgInfo', 'nobgImgOptions');
    window.handleNoBgImg = async function () {
      const f = dz.getFile(); if (!f) return alert('Select an image first.');
      const fd = new FormData(); fd.append('file', f);
      await callApi('remove-background', fd, 'nobgImgResult', 'nobgImgBtn');
    };
  };

  // ── Crop ──
  window.initCropImg = function () {
    const dz = setupDz('cropImgDz', 'cropImgInput', 'cropImgInfo', 'cropImgOptions');
    window.handleCropImg = async function () {
      const f = dz.getFile(); if (!f) return alert('Select an image first.');
      const fd = new FormData(); fd.append('file', f);
      fd.append('left', document.getElementById('cropImgL').value);
      fd.append('top', document.getElementById('cropImgT').value);
      fd.append('right', document.getElementById('cropImgR').value);
      fd.append('bottom', document.getElementById('cropImgB').value);
      await callApi('crop', fd, 'cropImgResult', 'cropImgBtn');
    };
  };

  // ── Rotate/Flip ──
  window.initRotateImg = function () {
    const dz = setupDz('rotateImgDz', 'rotateImgInput', 'rotateImgInfo', 'rotateImgOptions');
    window.handleRotateImg = async function () {
      const f = dz.getFile(); if (!f) return alert('Select an image first.');
      const fd = new FormData(); fd.append('file', f);
      fd.append('angle', document.getElementById('rotateImgAngle').value);
      await callApi('rotate', fd, 'rotateImgResult', 'rotateImgBtn');
    };
  };

  window.initFlipImg = function () {
    const dz = setupDz('flipImgDz', 'flipImgInput', 'flipImgInfo', 'flipImgOptions');
    window.handleFlipImg = async function () {
      const f = dz.getFile(); if (!f) return alert('Select an image first.');
      const fd = new FormData(); fd.append('file', f);
      fd.append('direction', document.getElementById('flipImgDir').value);
      await callApi('flip', fd, 'flipImgResult', 'flipImgBtn');
    };
  };

  // ── Watermark ──
  window.initWatermarkImg = function () {
    const dz = setupDz('wmImgDz', 'wmImgInput', 'wmImgFileInfo', 'wmImgOptions');
    window.handleWatermarkImg = async function () {
      const f = dz.getFile(); if (!f) return alert('Select an image first.');
      const fd = new FormData(); fd.append('file', f);
      fd.append('text', document.getElementById('wmImgText').value);
      fd.append('opacity', document.getElementById('wmImgOpacity').value);
      await callApi('watermark', fd, 'wmImgResult', 'wmImgBtn');
    };
  };

  // ── Thumbnail ──
  window.initThumbnailImg = function () {
    const dz = setupDz('thumbImgDz', 'thumbImgInput', 'thumbImgFileInfo', 'thumbImgOptions');
    window.handleThumbnailImg = async function () {
      const f = dz.getFile(); if (!f) return alert('Select an image first.');
      const fd = new FormData(); fd.append('file', f);
      fd.append('size', document.getElementById('thumbImgSize').value);
      await callApi('thumbnail', fd, 'thumbImgResult', 'thumbImgBtn');
    };
  };

  // ── Upscale ──
  window.initUpscaleImg = function () {
    const dz = setupDz('upscaleImgDz', 'upscaleImgInput', 'upscaleImgFileInfo', 'upscaleImgOptions');
    window.handleUpscaleImg = async function () {
      const f = dz.getFile(); if (!f) return alert('Select an image first.');
      const fd = new FormData(); fd.append('file', f);
      fd.append('scale', document.getElementById('upscaleImgScale').value);
      await callApi('upscale', fd, 'upscaleImgResult', 'upscaleImgBtn');
    };
  };

})();
