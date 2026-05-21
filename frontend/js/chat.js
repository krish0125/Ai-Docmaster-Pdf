/* ============================================
   AI DocMaster — Chat with PDF Logic
   ============================================ */

const API_BASE_CHAT = 'http://127.0.0.1:5000';
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
        const res = await fetch(`${API_BASE_CHAT}/pdf/upload`, {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${token}` },
            body: formData
        });

        const data = await res.json();
        if (res.ok && data.file_id) {
            chatFileId = data.file_id;
            chatFileName = file.name;
            chatMessages = [];

            // Update sidebar info
            const pdfInfo = document.getElementById('pdfInfoPanel');
            if (pdfInfo) {
                pdfInfo.innerHTML = `
                    <div class="pdf-info-card">
                        <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="#FF5252" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
                        <h4>${file.name}</h4>
                        <p class="text-muted">${formatFileSize(file.size)}</p>
                        ${data.page_count ? `<p class="text-muted">${data.page_count} pages</p>` : ''}
                    </div>
                `;
            }

            // Show chat interface, hide upload
            const uploadArea = document.getElementById('chatUploadArea');
            const chatArea = document.getElementById('chatArea');
            if (uploadArea) uploadArea.style.display = 'none';
            if (chatArea) chatArea.style.display = 'flex';

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
        const res = await fetch(`${API_BASE_CHAT}/ai/chat`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
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
            <div class="chat-empty-state">
                <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="var(--text-muted)" stroke-width="1"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
                <h3>Start a Conversation</h3>
                <p>Upload a PDF and ask questions about its content</p>
            </div>
        `;
        return;
    }

    container.innerHTML = chatMessages.map(msg => {
        const isUser = msg.role === 'user';
        const time = msg.time ? new Date(msg.time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '';
        const content = formatMessageContent(msg.content);

        return `
            <div class="chat-message ${isUser ? 'user' : 'bot'}">
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
    indicator.className = 'chat-message bot';
    indicator.innerHTML = `
        <div class="message-avatar">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2a4 4 0 0 1 4 4v2a4 4 0 0 1-8 0V6a4 4 0 0 1 4-4z"/><path d="M6 12h12v4a6 6 0 0 1-12 0v-4z"/></svg>
        </div>
        <div class="message-content">
            <div class="message-bubble typing">
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
        const res = await fetch(`${API_BASE_CHAT}/ai/chat-history/${fileId}`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        const data = await res.json();
        if (data && data.messages) {
            chatMessages = data.messages;
            renderMessages();
        }
    } catch (e) { /* ignore */ }
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
