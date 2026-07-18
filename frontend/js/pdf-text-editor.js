// Edit PDF Text Tool JavaScript Controller
// Uses pdf.js for rendering and text-layer coordinates discovery

let editPdfDoc = null;
let editCurrentPage = 1;
let editCurrentFile = null;
let editMode = 'edit'; // 'edit' or 'add'
let editActiveNode = null;
let editList = []; // stores all applied edits { id, page_index, type, x, y, width, height, text, font_family, font_size, color, bold, italic, align }
let editHistory = []; // stack of previous editList states for undo

// Set pdf.js worker URL
if (typeof pdfjsLib !== 'undefined') {
    pdfjsLib.GlobalWorkerOptions.workerSrc = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/2.16.105/pdf.worker.min.js';
}

function initEditPdfText() {
    const dz = document.getElementById('editPdfTextDz');
    const fileInput = document.getElementById('editPdfTextFileInput');

    if (!dz || !fileInput) return;

    dz.addEventListener('click', () => fileInput.click());

    dz.addEventListener('dragover', (e) => {
        e.preventDefault();
        dz.classList.add('dragover');
    });

    dz.addEventListener('dragleave', () => dz.classList.remove('dragover'));

    dz.addEventListener('drop', (e) => {
        e.preventDefault();
        dz.classList.remove('dragover');
        if (e.dataTransfer.files.length > 0) {
            handleSelectedEditFile(e.dataTransfer.files[0]);
        }
    });

    fileInput.addEventListener('change', () => {
        if (fileInput.files.length > 0) {
            handleSelectedEditFile(fileInput.files[0]);
        }
    });

    // ── Attach overlay click for "Add Text" mode ──
    const overlay = document.getElementById('editPdfTextOverlay');
    if (overlay) {
        overlay.addEventListener('click', (e) => {
            if (editMode !== 'add') return;
            const rect = overlay.getBoundingClientRect();
            const x = e.clientX - rect.left;
            const y = e.clientY - rect.top;

            const canvas = document.getElementById('editPdfTextCanvas');
            if (!canvas || canvas.width === 0) return;

            const leftPct = x / canvas.width;
            const topPct = y / canvas.height;

            const width = 150;
            const height = 30;
            const widthPct = width / canvas.width;
            const heightPct = height / canvas.height;

            const id = `added-node-${Date.now()}`;

            const node = document.createElement('div');
            node.id = id;
            node.className = 'edit-text-node added-node';
            node.style.position = 'absolute';
            node.style.left = `${x}px`;
            node.style.top = `${y}px`;
            node.style.width = `${width}px`;
            node.style.height = `${height}px`;
            node.style.fontSize = '14px';
            node.style.fontFamily = 'Helvetica';
            node.style.color = '#000000';
            node.style.border = '1px dashed #3B82F6';
            node.style.padding = '2px';
            node.style.background = '#FFFFFF';

            node.dataset.leftPct = leftPct.toString();
            node.dataset.topPct = topPct.toString();
            node.dataset.widthPct = widthPct.toString();
            node.dataset.heightPct = heightPct.toString();
            node.dataset.fontSizePts = '12';
            node.innerText = 'New Text Box';

            overlay.appendChild(node);
            setupDragAndDrop(node, canvas.width, canvas.height);

            // Add to editList
            saveHistoryState();
            editList.push({
                id: id,
                page_index: editCurrentPage - 1,
                type: 'add',
                x: leftPct,
                y: topPct,
                width: widthPct,
                height: heightPct,
                text: 'New Text Box',
                font_family: 'Helvetica',
                font_size: 12,
                color: '#000000',
                bold: false,
                italic: false,
                align: 'left'
            });

            // Focus automatically
            selectTextNode(node);
        });
    }

    // ── Formatting toolbar listeners ──
    const fontFamilyEl = document.getElementById('editPdfTextFontFamily');
    if (fontFamilyEl) {
        fontFamilyEl.addEventListener('change', (e) => {
            if (editActiveNode) {
                editActiveNode.style.fontFamily = e.target.value;
            }
        });
    }

    const fontSizeEl = document.getElementById('editPdfTextFontSize');
    if (fontSizeEl) {
        fontSizeEl.addEventListener('input', (e) => {
            if (editActiveNode) {
                const pts = parseFloat(e.target.value) || 12;
                editActiveNode.dataset.fontSizePts = pts.toString();
                editActiveNode.style.fontSize = `${pts * 1.3}px`;
            }
        });
    }

    const colorEl = document.getElementById('editPdfTextColor');
    if (colorEl) {
        colorEl.addEventListener('input', (e) => {
            if (editActiveNode) {
                editActiveNode.style.color = e.target.value;
            }
        });
    }

    const alignEl = document.getElementById('editPdfTextAlign');
    if (alignEl) {
        alignEl.addEventListener('change', (e) => {
            if (editActiveNode) {
                editActiveNode.style.textAlign = e.target.value;
            }
        });
    }
}

function handleSelectedEditFile(file) {
    if (file.type !== 'application/pdf' && !file.name.endsWith('.pdf')) {
        alert('Please upload a PDF file.');
        return;
    }

    editCurrentFile = file;
    editList = [];
    editHistory = [];
    editActiveNode = null;
    editCurrentPage = 1;

    document.getElementById('editPdfTextFileInfo').innerHTML = `
        <div class="file-info-card" style="margin-top:1rem; padding:0.75rem 1rem; border:1px solid #E5E7EB; border-radius:6px; background:#F9FAFB; display:flex; justify-content:space-between; align-items:center;">
            <span>📄 <strong>${file.name}</strong> (${(file.size / 1024 / 1024).toFixed(2)} MB)</span>
            <button class="btn btn-sm btn-outline-danger" onclick="cancelEditPdfText()">Remove</button>
        </div>
    `;

    // Load PDF
    const reader = new FileReader();
    reader.onload = function(e) {
        const arrayBuffer = e.target.result;

        pdfjsLib.getDocument({ data: arrayBuffer }).promise.then(pdf => {
            editPdfDoc = pdf;
            document.getElementById('editPdfTextPageCount').innerText = pdf.numPages;
            document.getElementById('editPdfTextPageNum').innerText = editCurrentPage;

            // Show Workspace
            document.getElementById('editPdfTextDz').style.display = 'none';
            document.getElementById('editPdfTextWorkspace').style.display = 'block';

            renderEditPage(1);
        }).catch(err => {
            alert('Failed to load PDF: ' + err.message);
        });
    };
    reader.readAsArrayBuffer(file);
}

function cancelEditPdfText() {
    editPdfDoc = null;
    editCurrentFile = null;
    editList = [];
    editHistory = [];
    editActiveNode = null;
    document.getElementById('editPdfTextFileInfo').innerHTML = '';
    document.getElementById('editPdfTextWorkspace').style.display = 'none';
    document.getElementById('editPdfTextDz').style.display = 'block';
    document.getElementById('editPdfTextResult').style.display = 'none';
    document.getElementById('editPdfTextFileInput').value = '';
}

function setEditMode(mode) {
    editMode = mode;
    const modeEditBtn = document.getElementById('editPdfTextModeEdit');
    const modeAddBtn = document.getElementById('editPdfTextModeAdd');
    if (modeEditBtn) modeEditBtn.classList.toggle('active', mode === 'edit');
    if (modeAddBtn) modeAddBtn.classList.toggle('active', mode === 'add');

    const overlay = document.getElementById('editPdfTextOverlay');
    if (overlay) {
        if (mode === 'add') {
            overlay.style.cursor = 'crosshair';
            deselectActiveNode();
        } else {
            overlay.style.cursor = 'default';
        }
    }
}

function renderEditPage(num) {
    if (!editPdfDoc) return;
    editCurrentPage = num;
    const pageNumEl = document.getElementById('editPdfTextPageNum');
    if (pageNumEl) pageNumEl.innerText = num;

    // Hide formatting toolbar until focused
    const formattingToolbar = document.getElementById('editPdfTextFormattingToolbar');
    if (formattingToolbar) {
        formattingToolbar.style.opacity = '0.5';
        formattingToolbar.style.pointerEvents = 'none';
    }

    editActiveNode = null;

    editPdfDoc.getPage(num).then(page => {
        const canvas = document.getElementById('editPdfTextCanvas');
        if (!canvas) return;
        const ctx = canvas.getContext('2d');
        const overlay = document.getElementById('editPdfTextOverlay');

        // Auto-scale to fit work area container width
        const container = document.getElementById('editPdfTextWorkArea');
        const containerWidth = container.clientWidth - 48; // padding

        const originalViewport = page.getViewport({ scale: 1.0 });
        const scale = containerWidth / originalViewport.width;
        const viewport = page.getViewport({ scale: Math.min(scale, 1.5) }); // cap scale at 1.5

        canvas.width = viewport.width;
        canvas.height = viewport.height;

        const wrapper = document.getElementById('editPdfTextPageWrapper');
        wrapper.style.width = `${viewport.width}px`;
        wrapper.style.height = `${viewport.height}px`;

        // Render Canvas
        const renderContext = {
            canvasContext: ctx,
            viewport: viewport
        };

        page.render(renderContext).promise.then(() => {
            // Render Text Overlay Nodes
            overlay.innerHTML = '';

            // Render existing edit runs for this page first
            const pageEdits = editList.filter(e => e.page_index === (editCurrentPage - 1));

            page.getTextContent().then(textContent => {
                const textItems = textContent.items;

                // Flag scanned document warning
                if (textItems.length === 0 && pageEdits.length === 0) {
                    overlay.innerHTML = `
                        <div style="position:absolute; top:20px; left:20px; right:20px; background:rgba(239, 68, 68, 0.9); color:white; padding:10px; border-radius:6px; text-align:center; font-size:13px; z-index:100;">
                            ⚠️ Warning: This page appears to be scanned or image-only. No text layer could be found. Editing existing text is not possible.
                        </div>
                    `;
                }

                textItems.forEach((item, index) => {
                    if (!item.str.trim()) return;

                    const transform = item.transform;
                    // convert to viewport coords
                    const [vx, vy] = viewport.convertToViewportPoint(transform[4], transform[5]);

                    const fontSize = Math.abs(transform[3]) * viewport.scale;
                    const width = item.width * viewport.scale;
                    const height = fontSize;
                    const top = vy - fontSize;
                    const left = vx;

                    const node_id = `text-node-${index}`;

                    // Check if there is already an edit for this node
                    const existingEdit = pageEdits.find(e => e.id === node_id);

                    const node = document.createElement('div');
                    node.id = node_id;
                    node.className = 'edit-text-node';
                    node.style.position = 'absolute';
                    node.style.left = `${left}px`;
                    node.style.top = `${top}px`;
                    node.style.width = `${width}px`;
                    node.style.height = `${height}px`;
                    node.style.fontSize = `${fontSize}px`;
                    node.style.fontFamily = 'Helvetica, Arial, sans-serif';
                    node.style.lineHeight = '1.0';
                    node.style.cursor = 'text';
                    node.style.whiteSpace = 'nowrap';
                    node.style.overflow = 'hidden';

                    // store percentages and baseline point info
                    node.dataset.leftPct = (left / canvas.width).toString();
                    node.dataset.topPct = (top / canvas.height).toString();
                    node.dataset.widthPct = (width / canvas.width).toString();
                    node.dataset.heightPct = (height / canvas.height).toString();
                    node.dataset.original = item.str;
                    node.dataset.fontSizePts = Math.abs(transform[3]).toString();

                    if (existingEdit) {
                        node.innerText = existingEdit.text;
                        node.style.color = existingEdit.color;
                        node.style.fontFamily = existingEdit.font_family;
                        node.style.fontWeight = existingEdit.bold ? 'bold' : 'normal';
                        node.style.fontStyle = existingEdit.italic ? 'italic' : 'normal';
                        node.style.textAlign = existingEdit.align;
                        node.style.background = '#FFFFFF'; // Whites out the background original text
                    } else {
                        node.innerText = item.str;
                        node.style.color = 'transparent'; // Hide on screen so PDF canvas text is seen until edited
                    }

                    node.addEventListener('click', (e) => {
                        if (editMode !== 'edit') return;
                        e.stopPropagation();
                        selectTextNode(node);
                    });

                    overlay.appendChild(node);
                });

                // Draw added text items
                pageEdits.forEach(e => {
                    if (e.type !== 'add') return;

                    const left = e.x * canvas.width;
                    const top = e.y * canvas.height;
                    const width = e.width * canvas.width;
                    const height = e.height * canvas.height;
                    const fontSize = e.font_size * viewport.scale;

                    const node = document.createElement('div');
                    node.id = e.id;
                    node.className = 'edit-text-node added-node';
                    node.style.position = 'absolute';
                    node.style.left = `${left}px`;
                    node.style.top = `${top}px`;
                    node.style.width = `${width}px`;
                    node.style.height = `${height}px`;
                    node.style.fontSize = `${fontSize}px`;
                    node.style.fontFamily = e.font_family;
                    node.style.color = e.color;
                    node.style.fontWeight = e.bold ? 'bold' : 'normal';
                    node.style.fontStyle = e.italic ? 'italic' : 'normal';
                    node.style.textAlign = e.align;
                    node.style.border = '1px dashed #3B82F6';
                    node.style.padding = '2px';
                    node.style.whiteSpace = 'normal';
                    node.style.wordBreak = 'break-word';

                    node.dataset.leftPct = e.x.toString();
                    node.dataset.topPct = e.y.toString();
                    node.dataset.widthPct = e.width.toString();
                    node.dataset.heightPct = e.height.toString();
                    node.dataset.fontSizePts = e.font_size.toString();

                    node.innerText = e.text;

                    node.addEventListener('click', (ev) => {
                        ev.stopPropagation();
                        selectTextNode(node);
                    });

                    setupDragAndDrop(node, canvas.width, canvas.height);
                    overlay.appendChild(node);
                });
            });
        });
    });
}

function selectTextNode(node) {
    deselectActiveNode();
    editActiveNode = node;
    node.classList.add('focused');
    node.setAttribute('contenteditable', 'true');
    node.focus();

    // If it was transparent (unedited original), set color to visible text
    if (node.style.color === 'transparent') {
        node.style.color = '#000000';
        node.style.background = '#FFFFFF'; // Hide canvas original text
    }

    // Enable formatting toolbar
    const toolbar = document.getElementById('editPdfTextFormattingToolbar');
    if (toolbar) {
        toolbar.style.opacity = '1.0';
        toolbar.style.pointerEvents = 'auto';
    }

    // Sync toolbar values
    const colorEl = document.getElementById('editPdfTextColor');
    if (colorEl) colorEl.value = rgbToHex(node.style.color) || '#000000';

    const fontSizeEl = document.getElementById('editPdfTextFontSize');
    if (fontSizeEl) fontSizeEl.value = Math.round(parseFloat(node.dataset.fontSizePts) || 12);

    const fontFamilyEl = document.getElementById('editPdfTextFontFamily');
    if (fontFamilyEl) fontFamilyEl.value = node.style.fontFamily.split(',')[0].replace(/['"]/g, '') || 'Helvetica';

    const alignEl = document.getElementById('editPdfTextAlign');
    if (alignEl) alignEl.value = node.style.textAlign || 'left';

    const boldBtn = document.getElementById('editPdfTextBoldBtn');
    if (boldBtn) boldBtn.classList.toggle('active', node.style.fontWeight === 'bold');

    const italicBtn = document.getElementById('editPdfTextItalicBtn');
    if (italicBtn) italicBtn.classList.toggle('active', node.style.fontStyle === 'italic');

    // Save state on blur / finalize
    node.addEventListener('blur', () => {
        saveNodeState(node);
    }, { once: true });
}

function deselectActiveNode() {
    if (editActiveNode) {
        saveNodeState(editActiveNode);
        editActiveNode.classList.remove('focused');
        editActiveNode.removeAttribute('contenteditable');
        editActiveNode = null;
    }
}

function saveNodeState(node) {
    const text = node.innerText.trim();
    const type = node.classList.contains('added-node') ? 'add' : 'edit';
    const original = node.dataset.original || '';

    // If unchanged and original type, don't store an edit record
    if (type === 'edit' && text === original) {
        // revert back to transparent color
        node.style.color = 'transparent';
        node.style.background = 'transparent';

        // Remove from list if existed
        const idx = editList.findIndex(e => e.id === node.id);
        if (idx > -1) {
            saveHistoryState();
            editList.splice(idx, 1);
        }
        return;
    }

    saveHistoryState();

    const boldState = node.style.fontWeight === 'bold';
    const italicState = node.style.fontStyle === 'italic';
    const color = rgbToHex(node.style.color) || '#000000';
    const fontFamily = node.style.fontFamily.split(',')[0].replace(/['"]/g, '') || 'Helvetica';
    const fontSizePts = parseFloat(node.dataset.fontSizePts) || 12;
    const alignState = node.style.textAlign || 'left';

    const editObj = {
        id: node.id,
        page_index: editCurrentPage - 1,
        type: type,
        x: parseFloat(node.dataset.leftPct),
        y: parseFloat(node.dataset.topPct),
        width: parseFloat(node.dataset.widthPct),
        height: parseFloat(node.dataset.heightPct),
        text: text,
        font_family: fontFamily,
        font_size: fontSizePts,
        color: color,
        bold: boldState,
        italic: italicState,
        align: alignState
    };

    const idx = editList.findIndex(e => e.id === node.id);
    if (idx > -1) {
        editList[idx] = editObj;
    } else {
        editList.push(editObj);
    }
}

// Draggable Added Text Blocks
function setupDragAndDrop(node, canvasWidth, canvasHeight) {
    let isDragging = false;
    let dragStart = { x: 0, y: 0 };
    let elemStart = { x: 0, y: 0 };

    node.addEventListener('mousedown', (e) => {
        if (e.target !== node && !e.target.classList.contains('drag-handle')) return;
        if (node.getAttribute('contenteditable') === 'true') return; // let edit click happen

        isDragging = true;
        dragStart.x = e.clientX;
        dragStart.y = e.clientY;
        elemStart.x = parseFloat(node.style.left) || 0;
        elemStart.y = parseFloat(node.style.top) || 0;
        e.preventDefault();
        e.stopPropagation();
    });

    document.addEventListener('mousemove', (e) => {
        if (!isDragging) return;
        const dx = e.clientX - dragStart.x;
        const dy = e.clientY - dragStart.y;

        const newX = Math.max(0, Math.min(canvasWidth - node.offsetWidth, elemStart.x + dx));
        const newY = Math.max(0, Math.min(canvasHeight - node.offsetHeight, elemStart.y + dy));

        node.style.left = `${newX}px`;
        node.style.top = `${newY}px`;

        node.dataset.leftPct = (newX / canvasWidth).toString();
        node.dataset.topPct = (newY / canvasHeight).toString();
    });

    document.addEventListener('mouseup', () => {
        if (isDragging) {
            isDragging = false;
            // Save state immediately
            saveNodeState(node);
        }
    });
}

// Formatting application
function toggleStyle(style) {
    if (!editActiveNode) return;
    if (style === 'bold') {
        const isBold = editActiveNode.style.fontWeight === 'bold';
        editActiveNode.style.fontWeight = isBold ? 'normal' : 'bold';
        const boldBtn = document.getElementById('editPdfTextBoldBtn');
        if (boldBtn) boldBtn.classList.toggle('active', !isBold);
    } else if (style === 'italic') {
        const isItalic = editActiveNode.style.fontStyle === 'italic';
        editActiveNode.style.fontStyle = isItalic ? 'normal' : 'italic';
        const italicBtn = document.getElementById('editPdfTextItalicBtn');
        if (italicBtn) italicBtn.classList.toggle('active', !isItalic);
    }
}

// Navigation
function prevEditPage() {
    if (editCurrentPage > 1) {
        deselectActiveNode();
        renderEditPage(editCurrentPage - 1);
    }
}

function nextEditPage() {
    if (editPdfDoc && editCurrentPage < editPdfDoc.numPages) {
        deselectActiveNode();
        renderEditPage(editCurrentPage + 1);
    }
}

// History & Undo State
function saveHistoryState() {
    // Save deep copy of editList
    editHistory.push(JSON.parse(JSON.stringify(editList)));
    if (editHistory.length > 20) {
        editHistory.shift(); // limit history depth
    }
}

function undoLastEdit() {
    if (editHistory.length > 0) {
        deselectActiveNode();
        editList = editHistory.pop();
        renderEditPage(editCurrentPage);
    } else {
        alert('Nothing to undo.');
    }
}

function resetAllEdits() {
    if (confirm('Are you sure you want to reset all changes?')) {
        deselectActiveNode();
        editList = [];
        editHistory = [];
        renderEditPage(editCurrentPage);
    }
}

// Backend Save Submission
function applyPdfTextEdits() {
    if (!editCurrentFile) {
        alert('No PDF file loaded. Please upload a PDF first.');
        return;
    }

    deselectActiveNode();

    // Check if any edits made
    if (editList.length === 0) {
        alert('No edits made to apply. Please click on text to edit it or add new text boxes first.');
        return;
    }

    const resultDiv = document.getElementById('editPdfTextResult');
    resultDiv.style.display = 'block';
    resultDiv.innerHTML = `
        <div class="processing-card" style="padding:1.5rem; background:#F3F4F6; border-radius:8px; border:1px solid #E5E7EB; text-align:center;">
            <p>🔄 Processing edits and flattening PDF text layer...</p>
            <div class="progress-bar-container" style="background:#E5E7EB; border-radius:4px; height:8px; margin-top:0.75rem; overflow:hidden;">
                <div class="progress-bar-fill" style="background:#3B82F6; width:50%; height:100%; transition:width 0.4s;"></div>
            </div>
        </div>
    `;

    const fd = new FormData();
    fd.append('file', editCurrentFile);
    fd.append('edits', JSON.stringify(editList));

    const token = localStorage.getItem('token');

    window.safeFetch(`${API_BASE_URL}/edit/edit-pdf-text`, {
        method: 'POST',
        headers: {
            'Authorization': `Bearer ${token}`
        },
        body: fd
    })
    .then(res => {
        if (!res.ok) {
            return res.json().then(e => { throw new Error(e.error || `Server error (${res.status})`); });
        }
        return res.json();
    })
    .then(data => {
        // Build a proper download URL using the backend API base
        const downloadUrl = data.download_url.startsWith('http')
            ? data.download_url
            : `${API_BASE_URL}${data.download_url}`;

        resultDiv.innerHTML = `
            <div class="success-card" style="padding:1.5rem; background:#ECFDF5; border-radius:8px; border:1px solid #A7F3D0; text-align:center;">
                <h4 style="color:#065F46; margin-bottom:0.5rem;">🎉 PDF Text Edited Successfully!</h4>
                <p style="color:#047857; font-size:14px; margin-bottom:1rem;">Your changes have been flattened into the PDF content stream.</p>
                <a href="${downloadUrl}" class="btn btn-success" download style="display:inline-flex; align-items:center; gap:0.5rem;">
                    📥 Download Edited PDF (${(data.size / 1024).toFixed(1)} KB)
                </a>
            </div>
        `;
    })
    .catch(err => {
        resultDiv.innerHTML = `
            <div class="error-card" style="padding:1.5rem; background:#FEF2F2; border-radius:8px; border:1px solid #FCA5A5; text-align:center; color:#991B1B;">
                <p>❌ Error processing edits: ${err.message}</p>
                <button class="btn btn-sm btn-outline-danger" style="margin-top:0.5rem;" onclick="applyPdfTextEdits()">Try Again</button>
            </div>
        `;
    });
}

// Helpers
function rgbToHex(rgbStr) {
    if (!rgbStr) return '#000000';
    if (rgbStr.startsWith('#')) return rgbStr;
    const match = rgbStr.match(/^rgb\((\d+),\s*(\d+),\s*(\d+)\)$/);
    if (!match) return '#000000';
    function hex(x) {
        return ("0" + parseInt(x).toString(16)).slice(-2);
    }
    return "#" + hex(match[1]) + hex(match[2]) + hex(match[3]);
}
