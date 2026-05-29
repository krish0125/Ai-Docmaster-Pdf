/* ============================================
   AI DocMaster — AI Interactive Flashcard Maker
   ============================================ */

let flashcardFile = null;
let currentFlashcards = [];
let currentCardIndex = 0;

function initFlashcardsTool() {
    const dropzone = document.getElementById('flashcardsDropzone');
    const fileInput = document.getElementById('flashcardsFileInput');

    if (!dropzone) return;

    dropzone.addEventListener('click', () => fileInput.click());
    fileInput.addEventListener('click', (e) => e.stopPropagation());
    dropzone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropzone.classList.add('drag-over');
    });
    dropzone.addEventListener('dragleave', () => dropzone.classList.remove('drag-over'));
    dropzone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropzone.classList.remove('drag-over');
        setFlashcardFile(e.dataTransfer.files[0]);
    });
    fileInput.addEventListener('change', () => {
        setFlashcardFile(fileInput.files[0]);
        fileInput.value = '';
    });
}

function setFlashcardFile(file) {
    if (!file || !file.name.toLowerCase().endsWith('.pdf')) {
        showToast('Please select a PDF file', 'error');
        return;
    }
    flashcardFile = file;
    const info = document.getElementById('flashcardsFileInfo');
    if (info) {
        info.innerHTML = `
            <div class="file-item">
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
    document.getElementById('flashcardsOptions').style.display = 'block';
}

async function handleGenerateFlashcards(e) {
    if (e) {
        e.preventDefault();
    }
    if (!flashcardFile) {
        showToast('Please select a PDF first', 'warning');
        return;
    }

    const btn = document.getElementById('flashcardsBtn');
    const resultDiv = document.getElementById('flashcardsResult');
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner-sm"></span> Generating Flashcards...';

    const formData = new FormData();
    formData.append('file', flashcardFile);

    try {
        const data = await uploadFileWithProgress('/ai/flashcards', formData, () => {});
        if (data && data.cards && data.cards.length > 0) {
            currentFlashcards = data.cards;
            currentCardIndex = 0;
            renderFlashcard();
            resultDiv.style.display = 'block';
            showToast('Flashcards generated successfully!', 'success');
        } else {
            showToast('No flashcards could be generated from this document.', 'error');
        }
    } catch (err) {
        showToast('Flashcard generation failed: ' + err.message, 'error');
    } finally {
        btn.disabled = false;
        btn.innerHTML = `
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <rect x="3" y="3" width="18" height="18" rx="2"/>
                <path d="M7 7h10M7 12h10M7 17h10"/>
            </svg> Generate Flashcards`;
    }
}

function renderFlashcard() {
    const displayArea = document.getElementById('flashcardDisplayArea');
    if (!displayArea || currentFlashcards.length === 0) return;

    const card = currentFlashcards[currentCardIndex];
    displayArea.innerHTML = `
        <div class="flashcard-wrapper">
            <div class="flashcard-inner" id="flashcardInner" onclick="flipFlashcard()">
                <!-- Front Side -->
                <div class="flashcard-front">
                    <div class="flashcard-badge font-secondary">QUESTION</div>
                    <div class="flashcard-content">${renderMarkdown(card.question)}</div>
                    <div class="flashcard-hint">Click card to reveal answer</div>
                </div>
                <!-- Back Side -->
                <div class="flashcard-back">
                    <div class="flashcard-badge font-secondary">ANSWER</div>
                    <div class="flashcard-content">${renderMarkdown(card.answer)}</div>
                    <div class="flashcard-hint">Click card to see question</div>
                </div>
            </div>
        </div>
        
        <div class="flashcard-controls">
            <button class="btn btn-outline btn-sm" onclick="prevCard()" ${currentCardIndex === 0 ? 'disabled' : ''}>
                ← Previous
            </button>
            <span class="flashcard-progress">Card ${currentCardIndex + 1} of ${currentFlashcards.length}</span>
            <button class="btn btn-outline btn-sm" onclick="nextCard()" ${currentCardIndex === currentFlashcards.length - 1 ? 'disabled' : ''}>
                Next →
            </button>
        </div>
        
        <div class="result-actions" style="margin-top: 1.5rem; justify-content: center;">
            <button class="btn btn-primary btn-sm" onclick="downloadFlashcardsJson()">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                    <polyline points="7 10 12 15 17 10"/>
                    <line x1="12" y1="15" x2="12" y2="3"/>
                </svg> Download JSON List
            </button>
        </div>
    `;
}

function flipFlashcard() {
    const inner = document.getElementById('flashcardInner');
    if (inner) {
        inner.classList.toggle('flipped');
    }
}

function nextCard() {
    if (currentCardIndex < currentFlashcards.length - 1) {
        currentCardIndex++;
        renderFlashcard();
    }
}

function prevCard() {
    if (currentCardIndex > 0) {
        currentCardIndex--;
        renderFlashcard();
    }
}

function downloadFlashcardsJson() {
    if (currentFlashcards.length === 0) return;
    const blob = new Blob([JSON.stringify(currentFlashcards, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = (flashcardFile?.name?.replace(/\.[^.]+$/, '') || 'flashcards') + '_cards.json';
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
}

// Initialize on DOM load
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initFlashcardsTool);
} else {
    initFlashcardsTool();
}
