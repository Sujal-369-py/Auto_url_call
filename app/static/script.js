let token = localStorage.getItem('autocall_token');

// DOM Elements
const authOverlay = document.getElementById('authOverlay');
const appShell = document.getElementById('appShell');
const loginPanel = document.getElementById('loginPanel');
const signupPanel = document.getElementById('signupPanel');
const displayUsername = document.getElementById('displayUsername');
const urlListEl = document.getElementById('urlList');
const urlInputEl = document.getElementById('urlInput');
const toastStack = document.getElementById('toastStack');

// --- Notification System ---
function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = 'toast';
    
    let icon = 'fa-info-circle';
    if (type === 'success') icon = 'fa-check-circle';
    if (type === 'error') icon = 'fa-exclamation-circle';
    
    toast.innerHTML = `<i class="fas ${icon}"></i> <span>${message}</span>`;
    toastStack.appendChild(toast);
    
    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateY(-20px)';
        setTimeout(() => toast.remove(), 400);
    }, 4000);
}

// --- Auth Toggle & Feedback ---
function toggleAuth(type) {
    if (type === 'signup') {
        loginPanel.classList.add('hidden');
        signupPanel.classList.remove('hidden');
    } else {
        signupPanel.classList.add('hidden');
        loginPanel.classList.remove('hidden');
    }
}

async function handleSignup() {
    const username = document.getElementById('signupUsername').value.trim();
    const password = document.getElementById('signupPassword').value.trim();
    if (!username || !password) return showToast("Please fill all fields", "error");

    try {
        const res = await fetch('/api/signup', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password })
        });
        const data = await res.json();
        if (res.ok) {
            showToast("Account created successfully!", "success");
            toggleAuth('login');
        } else {
            showToast(data.detail || "Signup failed", "error");
        }
    } catch (err) {
        showToast("Network failure", "error");
    }
}

async function handleLogin() {
    const username = document.getElementById('loginUsername').value.trim();
    const password = document.getElementById('loginPassword').value.trim();
    if (!username || !password) return showToast("Credentials required", "error");

    try {
        const res = await fetch('/api/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password })
        });
        const data = await res.json();
        if (res.ok) {
            token = data.access_token;
            localStorage.setItem('autocall_token', token);
            localStorage.setItem('autocall_user', username);
            showToast("Welcome back!", "success");
            initApp();
        } else {
            showToast("Invalid credentials", "error");
        }
    } catch (err) {
        showToast("Server unreachable", "error");
    }
}

function logout() {
    localStorage.removeItem('autocall_token');
    localStorage.removeItem('autocall_user');
    token = null;
    appShell.classList.add('hidden');
    authOverlay.classList.remove('hidden');
}

// --- Core App Logic ---
function initApp() {
    if (!token) {
        authOverlay.classList.remove('hidden');
        appShell.classList.add('hidden');
        return;
    }
    
    authOverlay.classList.add('hidden');
    appShell.classList.remove('hidden');
    displayUsername.textContent = localStorage.getItem('autocall_user');
    fetchUrls();
}

async function fetchUrls() {
    try {
        const res = await fetch('/api/urls', {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        if (res.status === 401) return logout();
        const data = await res.json();
        renderUrls(data);
    } catch (err) {
        showToast("Failed to sync data", "error");
    }
}

function renderUrls(urls) {
    if (urls.length === 0) {
        urlListEl.innerHTML = `
            <div style="text-align: center; padding: 4rem 2rem; border: 1px dashed var(--glass-border); border-radius: 24px;">
                <i class="fas fa-cloud-upload-alt" style="font-size: 2rem; color: var(--text-dim); margin-bottom: 1rem;"></i>
                <p style="color: var(--text-secondary)">No active pings. Connect your first URL above.</p>
            </div>`;
        return;
    }

    urlListEl.innerHTML = '';
    urls.forEach(u => {
        const div = document.createElement('div');
        div.className = 'url-card';

        const status = (u.status || 'Pending').toUpperCase();
        let statusClass = 'pending';
        let statusIcon = 'fa-clock';

        if (status === '200' || status === 'OK') {
            statusClass = 'ok';
            statusIcon = 'fa-check-double';
        } else if (status !== 'PENDING') {
            statusClass = 'err';
            statusIcon = 'fa-exclamation-triangle';
        }

        div.innerHTML = `
            <div class="url-content">
                <a href="${u.url}" target="_blank" class="url-title">
                    <i class="fas fa-link" style="font-size: 0.9rem; opacity: 0.5; margin-right: 0.5rem;"></i>
                    ${u.url}
                </a>
                <div style="display: flex; align-items: center; gap: 1rem; margin-top: 0.25rem;">
                    <div class="status-tag ${statusClass}">
                        <i class="fas ${statusIcon}"></i>
                        ${status}
                    </div>
                    <span style="font-size: 0.75rem; color: var(--text-dim); font-weight: 600;">
                        <i class="far fa-clock" style="margin-right: 0.25rem;"></i>
                        ${u.last_ping || 'NEVER'}
                    </span>
                </div>
            </div>
            <div class="url-actions">
                <button class="btn btn-ghost" onclick="deleteUrl('${u.id}')" style="background: rgba(255,0,0,0.05); color: #ff3e3e; border: 1px solid rgba(255,0,0,0.1); padding: 0.6rem 1rem;">
                    <i class="fas fa-trash-alt"></i>
                </button>
            </div>
        `;
        urlListEl.appendChild(div);
    });
}

async function addUrl() {
    const url = urlInputEl.value.trim();
    if (!url) return showToast("URL cannot be empty", "error");

    try {
        const res = await fetch('/api/urls', {
            method: 'POST',
            headers: { 
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({ url })
        });

        if (res.ok) {
            urlInputEl.value = '';
            showToast("Tracking initialized", "success");
            fetchUrls();
        } else {
            const data = await res.json();
            showToast(data.detail || "Setup incomplete", "error");
            if (res.status === 401) logout();
        }
    } catch (err) {
        showToast("Request failed", "error");
    }
}

async function deleteUrl(id) {
    try {
        const res = await fetch(`/api/urls/${id}`, {
            method: 'DELETE',
            headers: { 'Authorization': `Bearer ${token}` }
        });
        if (res.ok) {
            showToast("Connection severed", "success");
            fetchUrls();
        } else if (res.status === 401) {
            logout();
        }
    } catch (err) {
        showToast("Operation failed", "error");
    }
}

// Initialize
initApp();

// Background Sync
setInterval(() => {
    if (token && document.visibilityState === 'visible') fetchUrls();
}, 30000);
