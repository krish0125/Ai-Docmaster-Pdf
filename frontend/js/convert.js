/**
 * convert.js — Phase 2: PDF Conversion tools
 * Handles all convert-tool dropzones and API calls.
 */

'use strict';

(function () {
  // ── Generic single-file dropzone setup ─────────────────────────────────────
  function setupDropzone(dzId, inputId, infoId, optionsId, multi = false) {
    const dz    = document.getElementById(dzId);
    const inp   = document.getElementById(inputId);
    const info  = document.getElementById(infoId);
    const opts  = document.getElementById(optionsId);
    if (!dz || !inp) return null;

    let selectedFiles = [];

    dz.addEventListener('click', () => inp.click());
    dz.addEventListener('dragover', e => { e.preventDefault(); dz.classList.add('drag-over'); });
    dz.addEventListener('dragleave', () => dz.classList.remove('drag-over'));
    dz.addEventListener('drop', e => {
      e.preventDefault(); dz.classList.remove('drag-over');
      const files = multi ? [...e.dataTransfer.files] : [e.dataTransfer.files[0]];
      setFiles(files);
    });
    inp.addEventListener('change', () => { setFiles([...inp.files]); });

    function setFiles(files) {
      selectedFiles = files.filter(Boolean);
      if (selectedFiles.length === 0) return;
      if (info) {
        if (multi) {
          const names = selectedFiles.map(f => f.name).join(', ');
          info.innerHTML = `
            <div class="file-selected-info">
              📄 <span><strong>${selectedFiles.length} file(s) selected:</strong> ${names}</span>
            </div>`;
        } else {
          const f = selectedFiles[0];
          const size = (f.size / 1024 / 1024).toFixed(2);
          info.innerHTML = `
            <div class="file-selected-info">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#6C63FF" stroke-width="2">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                <polyline points="14 2 14 8 20 8"/></svg>
              <span><strong>${f.name}</strong> &nbsp;(${size} MB)</span>
            </div>`;
        }
      }
      if (opts) opts.style.display = 'block';
    }

    return { getFile: () => selectedFiles[0], getFiles: () => selectedFiles };
  }

  // ── Generic result renderer ─────────────────────────────────────────────────
  function showResult(resultId, data, btnId) {
    const res = document.getElementById(resultId);
    const btn = document.getElementById(btnId);
    if (!res) return;
    res.style.display = 'block';

    if (data.error) {
      res.innerHTML = `<div class="alert alert-error">❌ ${data.error}</div>`;
    } else {
      const dlUrl = data.download_url || (data.download_urls && data.download_urls[0]);
      res.innerHTML = `
        <div class="result-card success">
          <div class="result-icon">✅</div>
          <div class="result-body">
            <h4>${data.message || 'Done!'}</h4>
            ${dlUrl ? `<a href="${API_BASE_URL}${dlUrl}" class="btn btn-primary" download>
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                <polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
              Download File</a>` : ''}
            ${data.download_urls ? data.download_urls.map((u, i) =>
              `<a href="${API_BASE_URL}${u}" class="btn btn-secondary" download style="margin:4px 4px 0 0">Download Page ${i + 1}</a>`
            ).join('') : ''}
          </div>
        </div>`;
    }
    if (btn) btn.disabled = false;
  }

  // ── API call ────────────────────────────────────────────────────────────────
  async function callConvert(endpoint, formData, resultId, btnId) {
    const btn = document.getElementById(btnId);
    if (btn) { btn.disabled = true; btn.textContent = 'Converting…'; }
    try {
      const token = localStorage.getItem('token');
      const resp  = await window.safeFetch(`${API_BASE_URL}/convert/${endpoint}`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
        body: formData,
      });
      const data = await resp.json();
      showResult(resultId, data, btnId);
    } catch (err) {
      showResult(resultId, { error: err.message }, btnId);
    }
  }

  // ── PDF → Word ──────────────────────────────────────────────────────────────
  window.initPdfToWord = function () {
    const dz = setupDropzone('pdfToWordDz', 'pdfToWordInput', 'pdfToWordInfo', 'pdfToWordOptions');
    window.handlePdfToWord = async function () {
      const f = dz.getFile();
      if (!f) return alert('Please select a PDF file first.');
      const fd = new FormData(); fd.append('file', f);
      await callConvert('pdf-to-word', fd, 'pdfToWordResult', 'pdfToWordBtn');
    };
  };

  // ── Word → PDF ──────────────────────────────────────────────────────────────
  window.initWordToPdf = function () {
    const dz = setupDropzone('wordToPdfDz', 'wordToPdfInput', 'wordToPdfInfo', 'wordToPdfOptions');
    window.handleWordToPdf = async function () {
      const f = dz.getFile();
      if (!f) return alert('Please select a Word file first.');
      const fd = new FormData(); fd.append('file', f);
      await callConvert('word-to-pdf', fd, 'wordToPdfResult', 'wordToPdfBtn');
    };
  };

  // ── PDF → Excel ─────────────────────────────────────────────────────────────
  window.initPdfToExcel = function () {
    const dz = setupDropzone('pdfToExcelDz', 'pdfToExcelInput', 'pdfToExcelInfo', 'pdfToExcelOptions');
    window.handlePdfToExcel = async function () {
      const f = dz.getFile();
      if (!f) return alert('Please select a PDF file first.');
      const fd = new FormData(); fd.append('file', f);
      await callConvert('pdf-to-excel', fd, 'pdfToExcelResult', 'pdfToExcelBtn');
    };
  };

  // ── Excel → PDF ─────────────────────────────────────────────────────────────
  window.initExcelToPdf = function () {
    const dz = setupDropzone('excelToPdfDz', 'excelToPdfInput', 'excelToPdfInfo', 'excelToPdfOptions');
    window.handleExcelToPdf = async function () {
      const f = dz.getFile();
      if (!f) return alert('Please select an Excel file first.');
      const fd = new FormData(); fd.append('file', f);
      await callConvert('excel-to-pdf', fd, 'excelToPdfResult', 'excelToPdfBtn');
    };
  };

  // ── PDF → PowerPoint ────────────────────────────────────────────────────────
  window.initPdfToPptx = function () {
    const dz = setupDropzone('pdfToPptxDz', 'pdfToPptxInput', 'pdfToPptxInfo', 'pdfToPptxOptions');
    window.handlePdfToPptx = async function () {
      const f = dz.getFile();
      if (!f) return alert('Please select a PDF file first.');
      const fd = new FormData(); fd.append('file', f);
      await callConvert('pdf-to-pptx', fd, 'pdfToPptxResult', 'pdfToPptxBtn');
    };
  };

  // ── PDF → Image ─────────────────────────────────────────────────────────────
  window.initPdfToImage = function () {
    const dz = setupDropzone('pdfToImageDz', 'pdfToImageInput', 'pdfToImageInfo', 'pdfToImageOptions');
    window.handlePdfToImage = async function () {
      const f = dz.getFile();
      if (!f) return alert('Please select a PDF file first.');
      const fd = new FormData(); fd.append('file', f);
      fd.append('format', document.getElementById('pdfToImageFmt')?.value || 'jpg');
      fd.append('dpi',    document.getElementById('pdfToImageDpi')?.value || '150');
      await callConvert('pdf-to-image', fd, 'pdfToImageResult', 'pdfToImageBtn');
    };
  };

  // ── PDF → HTML ──────────────────────────────────────────────────────────────
  window.initPdfToHtml = function () {
    const dz = setupDropzone('pdfToHtmlDz', 'pdfToHtmlInput', 'pdfToHtmlInfo', 'pdfToHtmlOptions');
    window.handlePdfToHtml = async function () {
      const f = dz.getFile();
      if (!f) return alert('Please select a PDF file first.');
      const fd = new FormData(); fd.append('file', f);
      await callConvert('pdf-to-html', fd, 'pdfToHtmlResult', 'pdfToHtmlBtn');
    };
  };

  // ── PDF → Text ──────────────────────────────────────────────────────────────
  window.initPdfToText = function () {
    const dz = setupDropzone('pdfToTextDz', 'pdfToTextInput', 'pdfToTextInfo', 'pdfToTextOptions');
    window.handlePdfToText = async function () {
      const f = dz.getFile();
      if (!f) return alert('Please select a PDF file first.');
      const fd = new FormData(); fd.append('file', f);
      await callConvert('pdf-to-text', fd, 'pdfToTextResult', 'pdfToTextBtn');
    };
  };

  // ── PDF → EPUB ──────────────────────────────────────────────────────────────
  window.initPdfToEpub = function () {
    const dz = setupDropzone('pdfToEpubDz', 'pdfToEpubInput', 'pdfToEpubInfo', 'pdfToEpubOptions');
    window.handlePdfToEpub = async function () {
      const f = dz.getFile();
      if (!f) return alert('Please select a PDF file first.');
      const fd = new FormData(); fd.append('file', f);
      await callConvert('pdf-to-epub', fd, 'pdfToEpubResult', 'pdfToEpubBtn');
    };
  };

  // ── PPTX → PDF ──────────────────────────────────────────────────────────────
  window.initPptxToPdf = function () {
    const dz = setupDropzone('pptxToPdfDz', 'pptxToPdfInput', 'pptxToPdfInfo', 'pptxToPdfOptions');
    window.handlePptxToPdf = async function () {
      const f = dz.getFile();
      if (!f) return alert('Please select a PowerPoint file first.');
      const fd = new FormData(); fd.append('file', f);
      await callConvert('pptx-to-pdf', fd, 'pptxToPdfResult', 'pptxToPdfBtn');
    };
  };

  // ── Image → PDF ──────────────────────────────────────────────────────────────
  window.initImageToPdf = function () {
    const dz = setupDropzone('imageToPdfDz', 'imageToPdfInput', 'imageToPdfInfo', 'imageToPdfOptions', true);
    window.handleImageToPdf = async function () {
      const fs = dz.getFiles();
      if (!fs || fs.length === 0) return alert('Please select image file(s) first.');
      const fd = new FormData();
      fs.forEach(f => fd.append('files', f));
      await callConvert('image-to-pdf', fd, 'imageToPdfResult', 'imageToPdfBtn');
    };
  };

  // ── HTML → PDF ──────────────────────────────────────────────────────────────
  window.initHtmlToPdf = function () {
    const dz = setupDropzone('htmlToPdfDz', 'htmlToPdfInput', 'htmlToPdfInfo', 'htmlToPdfOptions');
    window.handleHtmlToPdf = async function () {
      const f = dz.getFile();
      if (!f) return alert('Please select an HTML file first.');
      const fd = new FormData(); fd.append('file', f);
      await callConvert('html-to-pdf', fd, 'htmlToPdfResult', 'htmlToPdfBtn');
    };
  };

  // ── Text → PDF ──────────────────────────────────────────────────────────────
  window.initTextToPdf = function () {
    const dz = setupDropzone('textToPdfDz', 'textToPdfInput', 'textToPdfInfo', 'textToPdfOptions');
    window.handleTextToPdf = async function () {
      const f = dz.getFile();
      if (!f) return alert('Please select a TXT file first.');
      const fd = new FormData(); fd.append('file', f);
      await callConvert('text-to-pdf', fd, 'textToPdfResult', 'textToPdfBtn');
    };
  };

  // ── EPUB → PDF ──────────────────────────────────────────────────────────────
  window.initEpubToPdf = function () {
    const dz = setupDropzone('epubToPdfDz', 'epubToPdfInput', 'epubToPdfInfo', 'epubToPdfOptions');
    window.handleEpubToPdf = async function () {
      const f = dz.getFile();
      if (!f) return alert('Please select an EPUB file first.');
      const fd = new FormData(); fd.append('file', f);
      await callConvert('epub-to-pdf', fd, 'epubToPdfResult', 'epubToPdfBtn');
    };
  };
})();
