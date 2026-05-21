/* ============================================
   AI DocMaster — Main Application Logic
   ============================================ */

const API_BASE = 'http://127.0.0.1:5000';

// ── Auth Helpers ──
function getToken() {
    return localStorage.getItem('token');
}

function isLoggedIn() {
    return !!getToken();
}

function getUser() {
    try {
        return JSON.parse(localStorage.getItem('user') || '{}');
    } catch { return {}; }
}

function logout() {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    window.location.href = 'login.html';
}

function requireAuth() {
    if (!isLoggedIn()) {
        window.location.href = 'login.html';
        return false;
    }
    return true;
}

// ── API Fetch Wrapper ──
async function apiFetch(endpoint, options = {}) {
    const token = getToken();
    const headers = { ...options.headers };

    if (token) {
        headers['Authorization'] = `Bearer ${token}`;
    }

    if (!(options.body instanceof FormData)) {
        headers['Content-Type'] = 'application/json';
    }

    try {
        const res = await fetch(`${API_BASE}${endpoint}`, { ...options, headers });

        if (res.status === 401) {
            showToast('Session expired. Please login again.', 'error');
            logout();
            return null;
        }

        const data = await res.json();
        if (!res.ok) {
            throw new Error(data.error || data.message || `HTTP ${res.status}`);
        }
        return data;
    } catch (err) {
        if (err.message.includes('Failed to fetch') || err.message.includes('NetworkError')) {
            showToast('Cannot connect to server. Is the backend running?', 'error');
        }
        throw err;
    }
}

// ── Toast Notification System ──
function showToast(message, type = 'info') {
    const existing = document.querySelector('.toast');
    if (existing) existing.remove();

    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;

    const icons = {
        success: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>',
        error: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>',
        warning: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>',
        info: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>'
    };

    toast.innerHTML = `
        <div class="toast-content">
            <span class="toast-icon">${icons[type] || icons.info}</span>
            <span class="toast-message">${message}</span>
        </div>
        <button class="toast-close" onclick="this.parentElement.remove()">×</button>
    `;

    document.body.appendChild(toast);
    requestAnimationFrame(() => toast.classList.add('show'));
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}

// ── Format Helpers ──
function formatFileSize(bytes) {
    if (!bytes || bytes === 0) return '0 B';
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(1024));
    return (bytes / Math.pow(1024, i)).toFixed(i > 0 ? 1 : 0) + ' ' + sizes[i];
}

function formatDate(dateStr) {
    if (!dateStr) return 'N/A';
    const d = new Date(dateStr);
    const now = new Date();
    const diffMs = now - d;
    const diffMins = Math.floor(diffMs / 60000);
    const diffHrs = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHrs < 24) return `${diffHrs}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;
    return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

function getFileIcon(type) {
    if (type === 'pdf' || type === 'application/pdf') {
        return '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#FF5252" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/><polyline points="10 9 9 9 8 9"/></svg>';
    }
    return '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#00D4FF" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"/><circle cx="8.5" cy="8.5" r="1.5"/><polyline points="21 15 16 10 5 21"/></svg>';
}

// ── Dashboard Initialization ──
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        if (!requireAuth()) return;
        initDashboard();
    });
} else {
    if (requireAuth()) {
        initDashboard();
    }
}

function initDashboard() {
    loadUserProfile();
    initSidebar();
    initToolPanels();
    loadStats();
    loadRecentFiles();
    showSection('dashboard-home');
}

// ── User Profile ──
async function loadUserProfile() {
    const user = getUser();
    const nameEl = document.getElementById('userName');
    const avatarEl = document.getElementById('userAvatar');
    const welcomeEl = document.getElementById('welcomeName');

    if (user.name) {
        if (nameEl) nameEl.textContent = user.name;
        if (welcomeEl) welcomeEl.textContent = user.name;
        if (avatarEl) avatarEl.textContent = user.name.charAt(0).toUpperCase();
    }

    // Fetch fresh profile from API
    try {
        const data = await apiFetch('/auth/profile');
        if (data && data.user) {
            localStorage.setItem('user', JSON.stringify(data.user));
            if (nameEl) nameEl.textContent = data.user.name;
            if (welcomeEl) welcomeEl.textContent = data.user.name;
            if (avatarEl) avatarEl.textContent = data.user.name.charAt(0).toUpperCase();
        }
    } catch (e) { /* silently fail, use cached data */ }
}

// ── Stats ──
async function loadStats() {
    try {
        const data = await apiFetch('/files/stats');
        if (data) {
            animateCounter('statFiles', data.total_files || 0);
            animateCounter('statPdfs', data.pdf_count || 0);
            animateCounter('statOcr', data.ocr_count || 0);
            animateCounter('statChats', data.chat_count || 0);
        }
    } catch (e) {
        // Set defaults
        ['statFiles', 'statPdfs', 'statOcr', 'statChats'].forEach(id => {
            const el = document.getElementById(id);
            if (el) el.textContent = '0';
        });
    }
}

function animateCounter(elementId, target) {
    const el = document.getElementById(elementId);
    if (!el) return;
    let current = 0;
    const step = Math.max(1, Math.floor(target / 30));
    const timer = setInterval(() => {
        current += step;
        if (current >= target) { current = target; clearInterval(timer); }
        el.textContent = current;
    }, 30);
}

// ── Recent Files ──
async function loadRecentFiles() {
    const container = document.getElementById('recentFilesList');
    if (!container) return;

    try {
        const data = await apiFetch('/files/list');
        if (data && data.files && data.files.length > 0) {
            const recent = data.files.slice(0, 5);
            container.innerHTML = recent.map(f => `
                <div class="file-item">
                    <div class="file-icon">${getFileIcon(f.file_type)}</div>
                    <div class="file-info">
                        <span class="file-name">${f.original_name || f.filename}</span>
                        <span class="file-meta">${formatFileSize(f.size)} • ${formatDate(f.created_at)}</span>
                    </div>
                    <button class="btn-icon" onclick="downloadFile('${f._id}')" title="Download">
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
                    </button>
                </div>
            `).join('');
        } else {
            container.innerHTML = '<div class="empty-state"><p>No files uploaded yet</p></div>';
        }
    } catch (e) {
        container.innerHTML = '<div class="empty-state"><p>Connect to server to see files</p></div>';
    }
}

async function downloadFile(fileId) {
    try {
        const token = getToken();
        const res = await fetch(`${API_BASE}/files/download/${fileId}`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        if (res.ok) {
            const blob = await res.blob();
            const cd = res.headers.get('Content-Disposition');
            let filename = 'download';
            if (cd) {
                const match = cd.match(/filename="?(.+?)"?$/);
                if (match) filename = match[1];
            }
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url; a.download = filename;
            document.body.appendChild(a); a.click(); a.remove();
            URL.revokeObjectURL(url);
            showToast('File downloaded!', 'success');
        }
    } catch (e) {
        showToast('Download failed', 'error');
    }
}

// ── Sidebar Navigation ──
function initSidebar() {
    const toggle = document.getElementById('sidebarToggle');
    const sidebar = document.getElementById('sidebar');
    const overlay = document.getElementById('sidebarOverlay');

    if (toggle && sidebar) {
        toggle.addEventListener('click', () => {
            sidebar.classList.toggle('open');
            if (overlay) overlay.classList.toggle('show');
        });
    }

    if (overlay) {
        overlay.addEventListener('click', () => {
            sidebar.classList.remove('open');
            overlay.classList.remove('show');
        });
    }

    // Nav item clicks
    document.querySelectorAll('.nav-item[data-section]').forEach(item => {
        item.addEventListener('click', (e) => {
            e.preventDefault();
            const section = item.dataset.section;

            document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
            item.classList.add('active');

            if (section === 'chat') {
                window.location.href = 'chat.html';
                return;
            }

            showSection(section);

            // Close sidebar on mobile
            if (window.innerWidth <= 768) {
                sidebar.classList.remove('open');
                if (overlay) overlay.classList.remove('show');
            }
        });
    });

    // Logout
    const logoutBtn = document.getElementById('logoutBtn');
    if (logoutBtn) {
        logoutBtn.addEventListener('click', (e) => {
            e.preventDefault();
            logout();
        });
    }

    // PDF Tools submenu toggle
    const pdfToolsToggle = document.getElementById('pdfToolsToggle');
    if (pdfToolsToggle) {
        pdfToolsToggle.addEventListener('click', (e) => {
            e.preventDefault();
            pdfToolsToggle.closest('.nav-group').classList.toggle('expanded');
        });
    }
}

// ── Section Switching ──
function showSection(sectionId) {
    document.querySelectorAll('.tool-section').forEach(sec => {
        sec.classList.remove('active');
        sec.style.display = 'none';
    });

    const target = document.getElementById(sectionId);
    if (target) {
        target.style.display = 'block';
        requestAnimationFrame(() => target.classList.add('active'));
    }
}

// ── Tool Panel Initialization ──
function initToolPanels() {
    // Tool cards on dashboard home
    document.querySelectorAll('.tool-card[data-tool]').forEach(card => {
        card.addEventListener('click', () => {
            const tool = card.dataset.tool;
            const section = document.getElementById(tool);
            if (section) {
                showSection(tool);
                // Update sidebar active state
                document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
                const navItem = document.querySelector(`.nav-item[data-section="${tool}"]`);
                if (navItem) navItem.classList.add('active');
            }
        });
    });
}

// ── Upload Helper (used by multiple tools) ──
function createDropZone(containerId, options = {}) {
    const container = document.getElementById(containerId);
    if (!container) return null;

    const accept = options.accept || '.pdf,.png,.jpg,.jpeg';
    const multiple = options.multiple || false;
    const maxSize = options.maxSize || 50 * 1024 * 1024; // 50MB

    const input = container.querySelector('input[type="file"]') || (() => {
        const inp = document.createElement('input');
        inp.type = 'file';
        inp.accept = accept;
        inp.multiple = multiple;
        inp.style.display = 'none';
        container.appendChild(inp);
        return inp;
    })();

    container.addEventListener('click', () => input.click());

    container.addEventListener('dragover', (e) => {
        e.preventDefault();
        container.classList.add('drag-over');
    });

    container.addEventListener('dragleave', () => {
        container.classList.remove('drag-over');
    });

    container.addEventListener('drop', (e) => {
        e.preventDefault();
        container.classList.remove('drag-over');
        const files = Array.from(e.dataTransfer.files);
        if (options.onFiles) options.onFiles(files);
    });

    input.addEventListener('change', () => {
        const files = Array.from(input.files);
        if (options.onFiles) options.onFiles(files);
        input.value = '';
    });

    return { input, container };
}

// ── File Upload with Progress ──
function uploadFileWithProgress(url, formData, onProgress) {
    return new Promise((resolve, reject) => {
        const xhr = new XMLHttpRequest();
        xhr.open('POST', `${API_BASE}${url}`);

        const token = getToken();
        if (token) xhr.setRequestHeader('Authorization', `Bearer ${token}`);

        xhr.upload.addEventListener('progress', (e) => {
            if (e.lengthComputable && onProgress) {
                onProgress(Math.round((e.loaded / e.total) * 100));
            }
        });

        xhr.onload = () => {
            try {
                const data = JSON.parse(xhr.responseText);
                if (xhr.status >= 200 && xhr.status < 300) {
                    resolve(data);
                } else {
                    reject(new Error(data.error || `HTTP ${xhr.status}`));
                }
            } catch (e) {
                reject(new Error('Invalid response'));
            }
        };

        xhr.onerror = () => reject(new Error('Network error'));
        xhr.send(formData);
    });
}
