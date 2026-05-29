/* ============================================
   AI DocMaster — Chat with PDF Logic
   ============================================ */

const API_BASE_CHAT = 'http://127.0.0.1:5001';
let chatFileId = null;
let chatFileName = '';
let chatMessages = [];

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        if (!localStorage.getItem('token')) {
            window.location.href = 'login.html';
            return;
        }
        initChat();
    });
} else {
    if (!localStorage.getItem('token')) {
        window.location.href = 'login.html';
    } else {
        initChat();
    }
}

function initChat() {
    const chatForm = document.getElementById('chatForm');
    const chatInput = document.getElementById('chatInput');
    const pdfUploadZone = document.getElementById('chatPdfDropzone');
    const pdfFileInput = document.getElementById('chatPdfInput');
    const clearBtn = document.getElementById('clearChatBtn');

    // Prevent programmatic click events from bubbling up to dropzone and creating recursive loops!
    if (pdfFileInput) {
        pdfFileInput.addEventListener('click', (e) => {
            e.stopPropagation();
        });
    }

    // PDF upload for chat
    if (pdfUploadZone) {
        pdfUploadZone.addEventListener('click', () => pdfFileInput.click());
        pdfUploadZone.addEventListener('dragover', (e) => { e.preventDefault(); pdfUploadZone.classList.add('drag-over'); });
        pdfUploadZone.addEventListener('dragleave', () => pdfUploadZone.classList.remove('drag-over'));
        pdfUploadZone.addEventListener('drop', (e) => {
            e.preventDefault();
            pdfUploadZone.classList.remove('drag-over');
            uploadChatPdf(e.dataTransfer.files[0]);
        });
        pdfFileInput.addEventListener('change', () => { uploadChatPdf(pdfFileInput.files[0]); pdfFileInput.value = ''; });
    }

    // Send message
    if (chatForm) {
        chatForm.addEventListener('submit', (e) => {
            e.preventDefault();
            const msg = chatInput.value.trim();
            if (msg) sendMessage(msg);
        });
    }

    // Enter key (without shift)
    if (chatInput) {
        chatInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                const msg = chatInput.value.trim();
                if (msg) sendMessage(msg);
            }
        });
    }

    // Clear chat
    if (clearBtn) {
        clearBtn.addEventListener('click', () => {
            chatMessages = [];
            renderMessages();
            showToast('Chat cleared', 'info');
        });
    }

    // Check URL params for pre-loaded file
    const params = new URLSearchParams(window.location.search);
    const fileId = params.get('file_id');
    if (fileId) {
        chatFileId = fileId;
        loadChatHistory(fileId);
    }
}

async function uploadChatPdf(file) {
    if (!file || !file.name.toLowerCase().endsWith('.pdf')) {
        showToast('Please select a PDF file', 'error');
        return;
    }

    const uploadStatus = document.getElementById('chatUploadStatus');
    if (uploadStatus) {
        uploadStatus.innerHTML = '<span class="spinner-sm"></span> Uploading PDF...';
        uploadStatus.style.display = 'flex';
    }

    const formData = new FormData();
    formData.append('file', file);

    try {
        const token = localStorage.getItem('token');
        const headers = { 'Authorization': `Bearer ${token}` };
        const customKey = localStorage.getItem('user_gemini_key');
        if (customKey) {
            headers['X-Gemini-Key'] = customKey;
        }

        const res = await fetch(`${API_BASE_CHAT}/pdf/upload`, {
            method: 'POST',
            headers: headers,
            body: formData
        });

        const data = await res.json();
        if (res.ok && data.file_id) {
            chatFileId = data.file_id;
            chatFileName = file.name;
            chatMessages = [];

            // Update sidebar info
            const pdfInfo = document.getElementById('pdfInfoPanel');
            const pageCount = data.file_info && data.file_info.page_count ? data.file_info.page_count : (data.page_count || 0);
            if (pdfInfo) {
                pdfInfo.innerHTML = `
                    <div class="pdf-info-card">
                        <div class="pdf-icon">
                            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#FF5252" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
                        </div>
                        <div class="pdf-name" style="color: var(--text-primary); text-align: center; margin-bottom: var(--space-3); font-weight: 600; font-size: var(--fs-sm);">${file.name}</div>
                        <div class="pdf-info-details" style="display: flex; flex-direction: column; gap: var(--space-2);">
                            <div class="pdf-info-row" style="display: flex; justify-content: space-between; font-size: var(--fs-xs);">
                                <span class="label" style="color: var(--text-muted);">Size</span>
                                <span class="value" style="color: var(--text-secondary); font-weight: 500;">${formatFileSize(file.size)}</span>
                            </div>
                            ${pageCount ? `
                            <div class="pdf-info-row" style="display: flex; justify-content: space-between; font-size: var(--fs-xs);">
                                <span class="label" style="color: var(--text-muted);">Pages</span>
                                <span class="value" style="color: var(--text-secondary); font-weight: 500;">${pageCount} pages</span>
                            </div>` : ''}
                            <div class="pdf-info-row" style="display: flex; justify-content: space-between; font-size: var(--fs-xs);">
                                <span class="label" style="color: var(--text-muted);">Status</span>
                                <span class="value" style="color: var(--success,#00E676); font-weight: 500;">✓ Ready</span>
                            </div>
                        </div>
                        <button class="btn btn-outline btn-sm w-full" onclick="resetChatUpload()" style="margin-top: 15px; width: 100%; display: flex; align-items: center; justify-content: center; gap: 8px; font-size: var(--fs-xs);">
                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21.5 2v6h-6M21.34 15.57a10 10 0 1 1-.57-8.38l5.67-5.67"/></svg>
                            Upload Different PDF
                        </button>
                    </div>
                `;
            }

            // Update topbar doc name
            const headerDocName = document.getElementById('chatHeaderDocName');
            if (headerDocName) {
                headerDocName.textContent = file.name;
            }

            // Hide upload dropzone, keep sidebar visible
            const uploadArea = document.getElementById('chatUploadArea');
            if (uploadArea) uploadArea.style.display = 'none';

            // Reset and initialize chat messages
            chatMessages = [];
            renderMessages();

            // Add welcome message
            addBotMessage(`I've loaded **${file.name}**. Ask me anything about this document!`);
            showToast('PDF uploaded! Start chatting.', 'success');
        } else {
            showToast(data.error || 'Upload failed', 'error');
        }
    } catch (err) {
        showToast('Upload failed: ' + err.message, 'error');
    } finally {
        if (uploadStatus) uploadStatus.style.display = 'none';
    }
}

async function sendMessage(text) {
    if (!chatFileId) {
        showToast('Please upload a PDF first', 'warning');
        return;
    }

    const chatInput = document.getElementById('chatInput');
    const sendBtn = document.getElementById('sendBtn');

    // Add user message
    addUserMessage(text);
    chatInput.value = '';
    chatInput.style.height = 'auto';

    // Show typing indicator
    showTypingIndicator();
    if (sendBtn) sendBtn.disabled = true;

    try {
        const token = localStorage.getItem('token');
        const headers = {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
        };
        const customKey = localStorage.getItem('user_gemini_key');
        if (customKey) {
            headers['X-Gemini-Key'] = customKey;
        }

        const res = await fetch(`${API_BASE_CHAT}/ai/chat`, {
            method: 'POST',
            headers: headers,
            body: JSON.stringify({ file_id: chatFileId, question: text })
        });

        const data = await res.json();
        hideTypingIndicator();

        if (res.ok) {
            addBotMessage(data.response || data.answer || 'No response received');
        } else {
            addBotMessage('Sorry, I encountered an error: ' + (data.error || 'Unknown error'));
        }
    } catch (err) {
        hideTypingIndicator();
        addBotMessage('Connection error. Please make sure the server is running.');
    } finally {
        if (sendBtn) sendBtn.disabled = false;
        chatInput.focus();
    }
}

function addUserMessage(text) {
    chatMessages.push({ role: 'user', content: text, time: new Date() });
    renderMessages();
}

function addBotMessage(text) {
    chatMessages.push({ role: 'assistant', content: text, time: new Date() });
    renderMessages();
}

function renderMessages() {
    const container = document.getElementById('chatMessages');
    if (!container) return;

    if (chatMessages.length === 0) {
        container.innerHTML = `
            <div class="chat-empty">
                <div class="chat-empty-icon">
                    <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
                </div>
                <h3>Chat with Your PDF</h3>
                <p class="text-muted">Upload a PDF document in the sidebar to start an intelligent conversation about its content.</p>
                
                <div class="example-questions" style="margin-top: 30px; display: flex; flex-direction: column; align-items: center; gap: 10px;">
                    <p class="text-sm text-muted">Try asking:</p>
                    <button class="btn btn-secondary btn-sm" onclick="document.getElementById('chatInput').value='What is this document about?'; document.getElementById('chatInput').dispatchEvent(new Event('input'))" style="max-width: 320px; width: 100%;">What is this document about?</button>
                    <button class="btn btn-secondary btn-sm" onclick="document.getElementById('chatInput').value='Summarize the key points'; document.getElementById('chatInput').dispatchEvent(new Event('input'))" style="max-width: 320px; width: 100%;">Summarize the key points</button>
                    <button class="btn btn-secondary btn-sm" onclick="document.getElementById('chatInput').value='List the main conclusions'; document.getElementById('chatInput').dispatchEvent(new Event('input'))" style="max-width: 320px; width: 100%;">List the main conclusions</button>
                </div>
            </div>
        `;
        return;
    }

    container.innerHTML = chatMessages.map(msg => {
        const isUser = msg.role === 'user';
        const time = msg.time ? new Date(msg.time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '';
        const content = formatMessageContent(msg.content);

        return `
            <div class="message ${isUser ? 'message-user' : 'message-ai'}">
                <div class="message-avatar">
                    ${isUser
                        ? '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>'
                        : '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2a4 4 0 0 1 4 4v2a4 4 0 0 1-8 0V6a4 4 0 0 1 4-4z"/><path d="M6 12h12v4a6 6 0 0 1-12 0v-4z"/></svg>'
                    }
                </div>
                <div class="message-content">
                    <div class="message-bubble">${content}</div>
                    <span class="message-time">${time}</span>
                </div>
            </div>
        `;
    }).join('');

    scrollToBottom();
}

function formatMessageContent(text) {
    // Basic markdown-like formatting
    return text
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/\*(.*?)\*/g, '<em>$1</em>')
        .replace(/`(.*?)`/g, '<code>$1</code>')
        .replace(/\n/g, '<br>');
}

function showTypingIndicator() {
    const container = document.getElementById('chatMessages');
    if (!container) return;
    const indicator = document.createElement('div');
    indicator.id = 'typingIndicator';
    indicator.className = 'message message-ai';
    indicator.innerHTML = `
        <div class="message-avatar">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2a4 4 0 0 1 4 4v2a4 4 0 0 1-8 0V6a4 4 0 0 1 4-4z"/><path d="M6 12h12v4a6 6 0 0 1-12 0v-4z"/></svg>
        </div>
        <div class="message-content">
            <div class="message-bubble typing-indicator show">
                <span class="typing-dot"></span>
                <span class="typing-dot"></span>
                <span class="typing-dot"></span>
            </div>
        </div>
    `;
    container.appendChild(indicator);
    scrollToBottom();
}

function hideTypingIndicator() {
    const indicator = document.getElementById('typingIndicator');
    if (indicator) indicator.remove();
}

function scrollToBottom() {
    const container = document.getElementById('chatMessages');
    if (container) {
        container.scrollTop = container.scrollHeight;
    }
}

async function loadChatHistory(fileId) {
    try {
        const token = localStorage.getItem('token');
        const headers = { 'Authorization': `Bearer ${token}` };

        // 1. Fetch chat history messages
        const res = await fetch(`${API_BASE_CHAT}/ai/chat-history/${fileId}`, {
            headers: headers
        });
        const data = await res.json();
        if (data && data.messages) {
            chatMessages = data.messages;
            renderMessages();
        }

        // 2. Fetch user's file list to match and load file details
        const filesRes = await fetch(`${API_BASE_CHAT}/files/list`, {
            headers: headers
        });
        const filesData = await filesRes.json();
        if (filesData && filesData.files) {
            const activeFile = filesData.files.find(f => f.id === fileId);
            if (activeFile) {
                chatFileName = activeFile.original_name || activeFile.filename;
                
                // Hide upload dropzone, keep sidebar visible
                const uploadArea = document.getElementById('chatUploadArea');
                if (uploadArea) uploadArea.style.display = 'none';

                // Update sidebar info
                const pdfInfo = document.getElementById('pdfInfoPanel');
                if (pdfInfo) {
                    pdfInfo.innerHTML = `
                        <div class="pdf-info-card">
                            <div class="pdf-icon">
                                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#FF5252" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
                            </div>
                            <div class="pdf-name" style="color: var(--text-primary); text-align: center; margin-bottom: var(--space-3); font-weight: 600; font-size: var(--fs-sm);">${chatFileName}</div>
                            <div class="pdf-info-details" style="display: flex; flex-direction: column; gap: var(--space-2);">
                                <div class="pdf-info-row" style="display: flex; justify-content: space-between; font-size: var(--fs-xs);">
                                    <span class="label" style="color: var(--text-muted);">Size</span>
                                    <span class="value" style="color: var(--text-secondary); font-weight: 500;">${activeFile.size_formatted || formatFileSize(activeFile.size)}</span>
                                </div>
                                <div class="pdf-info-row" style="display: flex; justify-content: space-between; font-size: var(--fs-xs);">
                                    <span class="label" style="color: var(--text-muted);">Status</span>
                                    <span class="value" style="color: var(--success,#00E676); font-weight: 500;">✓ Ready</span>
                                </div>
                            </div>
                            <button class="btn btn-outline btn-sm w-full" onclick="resetChatUpload()" style="margin-top: 15px; width: 100%; display: flex; align-items: center; justify-content: center; gap: 8px; font-size: var(--fs-xs);">
                                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21.5 2v6h-6M21.34 15.57a10 10 0 1 1-.57-8.38l5.67-5.67"/></svg>
                                Upload Different PDF
                            </button>
                        </div>
                    `;
                }

                // Update topbar doc name
                const headerDocName = document.getElementById('chatHeaderDocName');
                if (headerDocName) {
                    headerDocName.textContent = chatFileName;
                }

                // If chat history has no messages, welcome the user
                if (chatMessages.length === 0) {
                    addBotMessage(`I've loaded **${chatFileName}**. Ask me anything about this document!`);
                }
            }
        }
    } catch (e) {
        console.error('Failed to load chat history details:', e);
    }
}

function resetChatUpload() {
    chatFileId = null;
    chatFileName = '';
    chatMessages = [];
    renderMessages();
    
    // Clear sidebar info
    const pdfInfo = document.getElementById('pdfInfoPanel');
    if (pdfInfo) {
        pdfInfo.innerHTML = `
            <div class="pdf-info-card" id="pdfInfoPlaceholder">
                <div class="pdf-icon">
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
                </div>
                <div class="pdf-name" style="color:var(--text-muted);">No PDF loaded yet</div>
            </div>
        `;
    }

    // Reset topbar doc name
    const headerDocName = document.getElementById('chatHeaderDocName');
    if (headerDocName) {
        headerDocName.textContent = 'No active document';
    }

    // Show upload area
    const uploadArea = document.getElementById('chatUploadArea');
    if (uploadArea) uploadArea.style.display = 'block';
    
    // Remove query params from URL so reloading doesn't bring back the old file
    const url = new URL(window.location);
    url.searchParams.delete('file_id');
    window.history.pushState({}, '', url);
}

function formatFileSize(bytes) {
    if (!bytes) return '0 B';
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(1024));
    return (bytes / Math.pow(1024, i)).toFixed(i > 0 ? 1 : 0) + ' ' + sizes[i];
}

function showToast(message, type = 'info') {
    const existing = document.querySelector('.toast');
    if (existing) existing.remove();

    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.innerHTML = `<div class="toast-content"><span class="toast-message">${message}</span></div><button class="toast-close" onclick="this.parentElement.remove()">×</button>`;
    document.body.appendChild(toast);
    requestAnimationFrame(() => toast.classList.add('show'));
    setTimeout(() => { toast.classList.remove('show'); setTimeout(() => toast.remove(), 300); }, 4000);
}
