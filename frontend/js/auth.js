/* ============================================
   AI DocMaster — Authentication Logic
   ============================================ */

const API_BASE = 'http://127.0.0.1:5001';

// ── Check if already logged in ──
document.addEventListener('DOMContentLoaded', () => {
    const token = localStorage.getItem('token');
    if (token) {
        window.location.href = 'dashboard.html';
        return;
    }
    initAuthPage();
});

function initAuthPage() {
    // Tab switching (support both .auth-tab and .auth-tab-btn)
    const tabBtns = document.querySelectorAll('.auth-tab, .auth-tab-btn');
    const loginForm = document.getElementById('loginForm');
    const signupForm = document.getElementById('signupForm');
    const tabIndicator = document.querySelector('.tab-indicator, .auth-tab-indicator');

    tabBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const tab = btn.dataset.tab;
            tabBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');

            if (tab === 'login') {
                loginForm.classList.add('active');
                signupForm.classList.remove('active');
                if (tabIndicator) tabIndicator.style.transform = 'translateX(0)';
            } else {
                signupForm.classList.add('active');
                loginForm.classList.remove('active');
                if (tabIndicator) tabIndicator.style.transform = 'translateX(100%)';
            }
        });
    });

    // Password visibility toggles
    document.querySelectorAll('.toggle-password').forEach(toggle => {
        toggle.addEventListener('click', () => {
            const wrapper = toggle.closest('.input-wrapper') || toggle.closest('.auth-input-wrapper');
            const input = wrapper.querySelector('input');
            if (input.type === 'password') {
                input.type = 'text';
                toggle.innerHTML = `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"/><line x1="1" y1="1" x2="23" y2="23"/></svg>`;
            } else {
                input.type = 'password';
                toggle.innerHTML = `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>`;
            }
        });
    });

    // Password strength indicator
    const signupPassword = document.getElementById('signupPassword');
    if (signupPassword) {
        signupPassword.addEventListener('input', (e) => {
            updatePasswordStrength(e.target.value);
        });
    }

    // Form submissions
    if (loginForm) {
        loginForm.addEventListener('submit', handleLogin);
    }
    if (signupForm) {
        signupForm.addEventListener('submit', handleSignup);
    }

    // Auto-switch tab if #signup is in the URL hash
    if (window.location.hash === '#signup') {
        const signupTab = document.getElementById('signupTab');
        if (signupTab) signupTab.click();
    }
}

// ── Password Strength ──
function updatePasswordStrength(password) {
    const strengthBar = document.querySelector('.strength-bar-fill');
    const strengthText = document.querySelector('.strength-text');
    
    // Fallback for segment-based strength indicators if any
    const seg1 = document.getElementById('seg1');
    const seg2 = document.getElementById('seg2');
    const seg3 = document.getElementById('seg3');
    const seg4 = document.getElementById('seg4');
    const strengthArea = document.getElementById('passwordStrength');

    if (strengthArea) strengthArea.style.display = password ? 'block' : 'none';

    let score = 0;
    if (password.length >= 6) score++;
    if (password.length >= 10) score++;
    if (/[A-Z]/.test(password)) score++;
    if (/[0-9]/.test(password)) score++;
    if (/[^A-Za-z0-9]/.test(password)) score++;

    const levels = [
        { label: '', color: 'transparent', width: '0%' },
        { label: 'Very Weak', color: '#FF5252', width: '20%' },
        { label: 'Weak', color: '#FF9800', width: '40%' },
        { label: 'Fair', color: '#FFD600', width: '60%' },
        { label: 'Strong', color: '#00E676', width: '80%' },
        { label: 'Very Strong', color: '#00D4FF', width: '100%' }
    ];

    const level = levels[score] || levels[0];

    if (strengthBar) {
        strengthBar.style.width = level.width;
        strengthBar.style.background = level.color;
    }
    if (strengthText) {
        strengthText.textContent = level.label;
        strengthText.style.color = level.color;
    }

    // Update segment-based styles if present
    if (seg1 && seg2 && seg3 && seg4) {
        [seg1, seg2, seg3, seg4].forEach(s => s.style.background = 'rgba(255,255,255,0.1)');
        if (score >= 1) seg1.style.background = level.color;
        if (score >= 2) seg2.style.background = level.color;
        if (score >= 3) seg3.style.background = level.color;
        if (score >= 4) seg4.style.background = level.color;
        
        const labelText = document.getElementById('strengthText');
        if (labelText) {
            labelText.textContent = level.label;
            labelText.style.color = level.color;
        }
    }
}

// ── Validation ──
function validateEmail(email) {
    return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
}

function showFieldError(fieldId, message) {
    const field = document.getElementById(fieldId);
    if (!field) return;
    field.classList.add('error');
    
    const group = field.closest('.form-group') || field.closest('.auth-input-group');
    if (group) {
        group.classList.add('error');
    }
    
    // Check for explicit error label like "loginEmailError"
    const customError = document.getElementById(fieldId + 'Error');
    if (customError) {
        customError.textContent = message;
        customError.style.display = 'block';
        return;
    }

    if (!group) return;
    let errorEl = group.querySelector('.field-error, .auth-input-error');
    if (!errorEl) {
        errorEl = document.createElement('span');
        errorEl.className = 'field-error';
        group.appendChild(errorEl);
    }
    errorEl.textContent = message;
    errorEl.style.display = 'block';
}

function clearFieldErrors() {
    document.querySelectorAll('.field-error, .auth-input-error').forEach(el => el.style.display = 'none');
    document.querySelectorAll('.error').forEach(el => el.classList.remove('error'));
    document.querySelectorAll('.auth-input-group').forEach(el => el.classList.remove('error'));
}

// ── Show/Hide auth error banner ──
function showAuthError(message) {
    const authError = document.getElementById('authError');
    const authErrorText = document.getElementById('authErrorText');
    if (authError && authErrorText) {
        authErrorText.textContent = message;
        authError.classList.add('show');
        // Auto-hide after 5s
        setTimeout(() => authError.classList.remove('show'), 5000);
    }
}

function hideAuthError() {
    const authError = document.getElementById('authError');
    if (authError) authError.classList.remove('show');
}

// ── Login Handler ──
async function handleLogin(e) {
    e.preventDefault();
    clearFieldErrors();
    hideAuthError();

    const email = document.getElementById('loginEmail').value.trim();
    const password = document.getElementById('loginPassword').value;
    const btn = e.target.querySelector('button[type="submit"]');

    // Client-side validation
    if (!email) { showFieldError('loginEmail', 'Email is required'); return; }
    if (!validateEmail(email)) { showFieldError('loginEmail', 'Please enter a valid email'); return; }
    if (!password) { showFieldError('loginPassword', 'Password is required'); return; }
    if (password.length < 6) { showFieldError('loginPassword', 'Password must be at least 6 characters'); return; }

    // Set loading state
    btn.classList.add('loading');
    btn.disabled = true;

    try {
        const res = await fetch(`${API_BASE}/auth/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password })
        });

        const data = await res.json();

        const tokenVal = data.access_token || data.token;
        if (res.ok && tokenVal) {
            localStorage.setItem('token', tokenVal);
            if (data.user) {
                localStorage.setItem('user', JSON.stringify(data.user));
            }
            showToast('Login successful! Redirecting...', 'success');
            setTimeout(() => { window.location.href = 'dashboard.html'; }, 800);
        } else {
            const errorMsg = data.error || data.message || 'Login failed. Please check your credentials.';
            showAuthError(errorMsg);
            showToast(errorMsg, 'error');
        }
    } catch (err) {
        console.error('Login error:', err);
        const errorMsg = 'Cannot connect to server. Make sure the backend is running on port 5001.';
        showAuthError(errorMsg);
        showToast(errorMsg, 'error');
    } finally {
        btn.classList.remove('loading');
        btn.disabled = false;
    }
}

// ── Signup Handler ──
async function handleSignup(e) {
    e.preventDefault();
    clearFieldErrors();
    hideAuthError();

    const name = document.getElementById('signupName').value.trim();
    const email = document.getElementById('signupEmail').value.trim();
    const password = document.getElementById('signupPassword').value;
    const confirmPassword = document.getElementById('signupConfirm').value;
    const btn = e.target.querySelector('button[type="submit"]');

    // Client-side validation
    if (!name) { showFieldError('signupName', 'Full name is required'); return; }
    if (!email) { showFieldError('signupEmail', 'Email is required'); return; }
    if (!validateEmail(email)) { showFieldError('signupEmail', 'Please enter a valid email'); return; }
    if (!password) { showFieldError('signupPassword', 'Password is required'); return; }
    if (password.length < 6) { showFieldError('signupPassword', 'Password must be at least 6 characters'); return; }
    if (password !== confirmPassword) { showFieldError('signupConfirm', 'Passwords do not match'); return; }

    // Set loading state
    btn.classList.add('loading');
    btn.disabled = true;

    try {
        const res = await fetch(`${API_BASE}/auth/signup`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, email, password })
        });

        const data = await res.json();

        if (res.ok) {
            showToast('Account created successfully! Please login.', 'success');
            // Switch to login tab
            const loginTab = document.getElementById('loginTab');
            if (loginTab) loginTab.click();
            // Pre-fill the email
            const loginEmailField = document.getElementById('loginEmail');
            if (loginEmailField) loginEmailField.value = email;
        } else {
            const errorMsg = data.error || data.message || 'Signup failed. Please try again.';
            showAuthError(errorMsg);
            showToast(errorMsg, 'error');
        }
    } catch (err) {
        console.error('Signup error:', err);
        const errorMsg = 'Cannot connect to server. Make sure the backend is running on port 5001.';
        showAuthError(errorMsg);
        showToast(errorMsg, 'error');
    } finally {
        btn.classList.remove('loading');
        btn.disabled = false;
    }
}

// ── Toast Notification ──
function showToast(message, type = 'info') {
    // Remove any existing toast
    const existing = document.querySelector('.auth-toast');
    if (existing) existing.remove();

    const toast = document.createElement('div');
    toast.className = `auth-toast auth-toast-${type}`;

    const icons = {
        success: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>',
        error: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>',
        info: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>'
    };

    toast.innerHTML = `
        <div class="auth-toast-content">
            <span class="auth-toast-icon">${icons[type] || icons.info}</span>
            <span class="auth-toast-message">${message}</span>
        </div>
        <button class="auth-toast-close" onclick="this.parentElement.remove()">×</button>
    `;

    document.body.appendChild(toast);

    // Trigger animation
    requestAnimationFrame(() => {
        toast.classList.add('auth-toast-show');
    });

    // Auto-remove after 4 seconds
    setTimeout(() => {
        toast.classList.remove('auth-toast-show');
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}
