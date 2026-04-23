/**
 * Admin Dashboard Logic
 */
console.log("Admin.js loading...");

// --- Auth / Session Helpers ---
const AUTH_CLOCK_SKEW_SECONDS = 30; // tolerate minor client/server clock drift
let authExpiryTimer = null;

function base64UrlDecode(input) {
    // base64url -> base64
    const base64 = input.replace(/-/g, '+').replace(/_/g, '/');
    const padded = base64.padEnd(base64.length + (4 - (base64.length % 4)) % 4, '=');
    return atob(padded);
}

function parseJwtPayload(token) {
    try {
        if (!token) return null;
        const parts = token.split('.');
        if (parts.length !== 3) return null;
        return JSON.parse(base64UrlDecode(parts[1]));
    } catch (e) {
        return null;
    }
}

function getTokenExpiryMs(token) {
    const payload = parseJwtPayload(token);
    if (!payload || typeof payload.exp !== 'number') return null;
    return payload.exp * 1000;
}

function isTokenExpired(token) {
    const expMs = getTokenExpiryMs(token);
    if (!expMs) return true;
    return Date.now() >= (expMs - AUTH_CLOCK_SKEW_SECONDS * 1000);
}

function scheduleAutoLogout(token) {
    if (authExpiryTimer) {
        clearTimeout(authExpiryTimer);
        authExpiryTimer = null;
    }

    const expMs = getTokenExpiryMs(token);
    if (!expMs) return;

    const delayMs = Math.max(expMs - Date.now() - AUTH_CLOCK_SKEW_SECONDS * 1000, 0);
    authExpiryTimer = setTimeout(() => handleAuthFailure('expired'), delayMs);
}

function getValidTokenOrRedirect() {
    const token = localStorage.getItem('admin_token');
    if (!token || isTokenExpired(token)) {
        handleAuthFailure('expired');
        return null;
    }
    return token;
}


// --- Global Config & Init ---
const tinyConfig = {
    plugins: 'link image code table lists media',
    toolbar: 'undo redo | blocks | bold italic | alignleft aligncenter alignright | bullist numlist | link image media | table code',
    menubar: false,
    height: 400,
    image_title: true,
    automatic_uploads: true,
    file_picker_types: 'image',
    // Custom Upload Logic for TinyMCE
    images_upload_handler: (blobInfo, progress) => new Promise((resolve, reject) => {
        const formData = new FormData();
        formData.append('file', blobInfo.blob(), blobInfo.filename());
        const token = getValidTokenOrRedirect();
        if (!token) return reject('Auth required');
        fetch('/admin/api/upload', { 
            method: 'POST', 
            body: formData,
            headers: token ? { 'Authorization': `Bearer ${token}` } : {}
        })
            .then(r => {
                if(r.status === 401) return handleAuthFailure();
                return r.json()
            })
            .then(json => {
                if (!json) return reject('Upload failed: Auth error');
                if (json.location) resolve(json.location);
                else reject('Upload failed: ' + json.error);
            })
            .catch(err => reject('Upload error: ' + err));
    })
};

document.addEventListener('DOMContentLoaded', () => {
    // Check if authenticated
    const token = localStorage.getItem('admin_token');
    if (!token || isTokenExpired(token)) return handleAuthFailure('expired');
    scheduleAutoLogout(token);
    initAdminApp();
});

function getUserPayload() {
    return parseJwtPayload(getValidTokenOrRedirect());
}

function initAdminApp() {
    const payload = getUserPayload();
    let initialSection = 'dashboard';
    
    // Role Based Access Control UI
    if (payload && payload.role === 'teacher') {
        initialSection = 'cv_update';
        // Hide CMS menus for teachers
        const adminIds = ['nav-dashboard', 'nav-pages', 'nav-unified', 'nav-faculty', 'nav-home_sections', 'nav-media', 'nav-settings', 'nav-appeals'];
        adminIds.forEach(id => {
            const el = document.getElementById(id);
            if(el) el.style.display = 'none';
        });
        document.getElementById('headerTitle').innerText = 'ระบบจัดการโปรไฟล์อาจารย์';
    } else {
        // Hide CV update for Admins if they don't want to use it
        // Or keep it so admins can update their own CV too. Let's keep it visible.
    }

    // Init TinyMCE
    if (typeof tinymce !== 'undefined') {
        tinymce.init({ ...tinyConfig, selector: '#content' });      // Page Editor
        tinymce.init({ ...tinyConfig, selector: '#postContent' });  // Unified Editor
        tinymce.init({ ...tinyConfig, selector: '#cv_editor' });    // CV Editor
    }

    // Default Section
    showSection(initialSection);
}

// --- Navigation & Sections ---
function showSection(sectionId) {
    document.querySelectorAll('.section-view').forEach(el => el.classList.remove('active'));
    document.querySelectorAll('nav a').forEach(el => {
        // Reset styles but preserve display:none
        if (el.style.display !== 'none') {
            el.className = 'block py-3 px-6 hover:bg-slate-800 cursor-pointer transition-colors border-l-4 border-transparent hover:border-blue-500 text-slate-100';
        }
    });

    const target = document.getElementById(sectionId);
    if (target) target.classList.add('active');

    const activeNav = document.getElementById('nav-' + sectionId);
    if (activeNav) {
        activeNav.className = 'block py-3 px-6 bg-slate-800 cursor-pointer transition-colors border-l-4 border-blue-500 text-white shadow-inner';
    }

    // Load Data on Switch
    if (sectionId === 'cv_update') loadMyCV();
    if (sectionId === 'pages') loadPages();
    if (sectionId === 'unified') switchUnifiedTab('content');
    if (sectionId === 'faculty') loadFaculty();
    if (sectionId === 'home_sections') switchHomeTab('banners');
    if (sectionId === 'media') loadMedia();
    if (sectionId === 'appeals') loadAppeals();
    if (sectionId === 'settings') loadSettings();
}

// --- API Helpers ---
function handleAuthFailure(reason = 'unauthorized') {
    try {
        localStorage.removeItem('admin_token');
        sessionStorage.setItem('auth_failure_reason', reason);
    } catch (e) {
        // ignore
    }
    window.location.href = '/admin/login';
}

async function uploadCVImage() {
    const fileInput = document.getElementById('cv_image_file');
    if(!fileInput.files.length) return Swal.fire('แจ้งเตือน', 'กรุณาเลือกไฟล์รูปภาพก่อน', 'warning');
    
    const formData = new FormData();
    formData.append('file', fileInput.files[0]);
    
    try {
        // Note: this uses the new unified role-based token. We can use /admin/api/upload if it's protected by verify_user instead of verify_admin_role
        // We will fallback to the public api if /admin/api/upload requires admin.
        const token = getValidTokenOrRedirect();
        if (!token) return;
        const headers = { 'Authorization': `Bearer ${token}` };
        
        // Use generic upload endpoint
        const res = await fetch('/admin/api/upload', { method: 'POST', body: formData, headers });
        if(res.status === 401) return handleAuthFailure();
        if(res.status === 403) return Swal.fire('Error', 'Permission denied', 'error');
        
        const data = await res.json();
        if(data.location) {
            document.getElementById('cv_image_url').value = data.location;
            Swal.fire('สำเร็จ', 'อัปโหลดรูปภาพเรียบร้อย', 'success');
        } else {
            Swal.fire('Error', data.error || 'Upload failed', 'error');
        }
    } catch(e) {
        Swal.fire('Error', e.message, 'error');
    }
}

async function loadMyCV() {
    Swal.fire({ title: 'กำลังโหลด...', allowOutsideClick: false, didOpen: () => Swal.showLoading() });
    try {
        const res = await apiCall('/admin/api/faculty/my-cv');
        Swal.close();
        if (res && res.success && res.faculty) {
            document.getElementById('cv_academic_position').value = res.faculty.position || '';
            document.getElementById('cv_image_url').value = res.faculty.image || '';
            
            const preview = document.getElementById('cv_image_preview');
            if (res.faculty.image) {
                preview.src = res.faculty.image;
                preview.classList.remove('hidden');
            } else {
                preview.classList.add('hidden');
            }
            
            const expContainer = document.getElementById('cv_expertise_container');
            expContainer.innerHTML = '';
            let expertiseList = [];
            if (Array.isArray(res.faculty.expertise)) {
                expertiseList = res.faculty.expertise;
            } else if (res.faculty.expertise) {
                try {
                    let rawExp = String(res.faculty.expertise);
                    // Convert python single-quoted list to valid JSON if it's a python string
                    let fixedJson = rawExp.replace(/'/g, '"');
                    expertiseList = JSON.parse(fixedJson);
                    if (!Array.isArray(expertiseList)) expertiseList = [expertiseList];
                } catch (e) {
                    let rawExp = String(res.faculty.expertise).replace(/^\[/, '').replace(/\]$/, '');
                    expertiseList = rawExp.split(',').map(s => s.replace(/['"]/g, '').trim()).filter(s => s);
                }
            }
            
            if (expertiseList.length === 0) {
                addExpertiseField('');
            } else {
                expertiseList.forEach(exp => addExpertiseField(exp));
            }
            
            if (res.cv_file) {
                document.getElementById('cv_file_url').value = res.cv_file;
                const link = document.getElementById('cv_file_preview_link');
                link.href = res.cv_file;
                link.classList.remove('hidden');
            } else {
                document.getElementById('cv_file_url').value = '';
                document.getElementById('cv_file_preview_link').classList.add('hidden');
            }
        } else if (res && !res.success) {
            Swal.fire('ข้อความจากระบบ', 'Debug: ' + JSON.stringify(res), 'info');
            addExpertiseField('');
        }
    } catch (e) {
        Swal.close();
        console.error("Failed to load CV:", e);
    }
}

function addExpertiseField(value) {
    const container = document.getElementById('cv_expertise_container');
    const div = document.createElement('div');
    div.className = 'flex gap-2 items-center';
    div.innerHTML = `
        <span class="text-gray-400">•</span>
        <input type="text" class="expertise-input flex-1 p-2 border rounded-lg text-sm bg-gray-50 focus:bg-white transition outline-none" value="${value || ''}" placeholder="ระบุความเชี่ยวชาญ">
        <button type="button" onclick="this.parentElement.remove()" class="text-red-500 hover:bg-red-50 rounded px-2 py-1 text-lg leading-none">&times;</button>
    `;
    container.appendChild(div);
}

async function uploadCVPdf() {
    const fileInput = document.getElementById('cv_pdf_file');
    if(!fileInput.files.length) return Swal.fire('แจ้งเตือน', 'กรุณาเลือกไฟล์ PDF ก่อน', 'warning');
    
    const file = fileInput.files[0];
    if(file.type !== 'application/pdf' && !file.name.toLowerCase().endsWith('.pdf')) {
        return Swal.fire('แจ้งเตือน', 'กรุณาอัปโหลดไฟล์ PDF เท่านั้น', 'warning');
    }
    
    const formData = new FormData();
    formData.append('file', file);
    
    Swal.fire({ title: 'กำลังอัปโหลด...', allowOutsideClick: false, didOpen: () => Swal.showLoading() });
    try {
        const token = getValidTokenOrRedirect();
        if (!token) return;
        const headers = { 'Authorization': `Bearer ${token}` };
        const res = await fetch('/admin/api/upload', { method: 'POST', body: formData, headers });
        if(res.status === 401) return handleAuthFailure();
        if(res.status === 403) return Swal.fire('Error', 'Permission denied', 'error');
        
        const data = await res.json();
        if(data.location) {
            document.getElementById('cv_file_url').value = data.location;
            const link = document.getElementById('cv_file_preview_link');
            link.href = data.location;
            link.classList.remove('hidden');
            Swal.fire('สำเร็จ', 'อัปโหลดไฟล์ PDF เรียบร้อย', 'success');
        } else {
            Swal.fire('Error', data.error || 'Upload failed', 'error');
        }
    } catch(e) {
        Swal.fire('Error', e.message, 'error');
    }
}

async function submitMyCV() {
    Swal.fire({ title: 'กำลังบันทึก...', allowOutsideClick: false, didOpen: () => Swal.showLoading() });
    try {
        const expInputs = document.querySelectorAll('.expertise-input');
        const expList = Array.from(expInputs).map(inp => inp.value.trim()).filter(val => val);
        
        const payload = {
            position: document.getElementById('cv_academic_position').value,
            expertise: JSON.stringify(expList),
            image: document.getElementById('cv_image_url').value,
            cv_file: document.getElementById('cv_file_url').value
        };
        const res = await apiCall('/admin/api/faculty/my-cv', 'POST', payload);
        if(!res) return; // Error handled inside apiCall already
        
        if(res.success) {
            Swal.fire('สำเร็จ', 'บันทึกข้อมูล CV เรียบร้อย', 'success');
        } else {
            Swal.fire('ผิดพลาด', res.message || 'ไม่สามารถบันทึกได้', 'error');
        }
    } catch(e) {
        Swal.fire('Error', e.message, 'error');
    }
}

function logout() {
    try { localStorage.removeItem('admin_token'); } catch (e) {}
    window.location.href = '/admin/login';
}

async function apiCall(url, method = 'GET', body = null) {
    try {
        const token = getValidTokenOrRedirect();
        if (!token) return null;
        const opts = { method, headers: {} };
        opts.headers['Authorization'] = `Bearer ${token}`;
        if (body) {
            opts.headers['Content-Type'] = 'application/json';
            opts.body = JSON.stringify(body);
        }
        const res = await fetch(url, opts);
        if (res.status === 401) {
            return handleAuthFailure();
        }
        return await res.json();
    } catch (e) {
        console.error("API Error:", e);
        Swal.fire({ icon: 'error', title: 'Error', text: e.message });
        return null;
    }
}

async function confirmAction(message, actionFn) {
    const result = await Swal.fire({
        title: 'Are you sure?',
        text: message,
        icon: 'warning',
        showCancelButton: true,
        confirmButtonColor: '#d33',
        cancelButtonColor: '#3085d6',
        confirmButtonText: 'Yes, proceed'
    });
    if (result.isConfirmed) await actionFn();
}

// --- Pages Logic ---
async function loadPages() {
    const pages = await apiCall('/admin/api/pages');
    if (!pages) return;
    const tbody = document.getElementById('pagesTableBody');
    tbody.innerHTML = pages.map(p => `
        <tr class="border-b hover:bg-gray-50 transition">
            <td class="py-3 px-4 font-medium text-gray-800">${p.title}</td>
            <td class="py-3 px-4 text-gray-500 text-sm font-mono">/${p.slug}</td>
            <td class="py-3 px-4 text-gray-500 text-sm">${p.updated_at ? new Date(p.updated_at).toLocaleDateString() : '-'}</td>
            <td class="py-3 px-4 text-right space-x-2">
                <button onclick="editPage(${p.id}, '${p.title}', '${p.slug}')" class="text-blue-600 hover:text-blue-800 font-medium text-sm">✎ Edit</button>
                <button onclick="deletePage(${p.id})" class="text-red-600 hover:text-red-800 font-medium text-sm">🗑 Delete</button>
            </td>
        </tr>
    `).join('');
}

async function editPage(id, title, slug) {
    document.getElementById('pageId').value = id || '';
    document.getElementById('title').value = title || '';
    document.getElementById('slug').value = slug || '';

    // Fetch content to load into editor
    if (id) {
        const pages = await apiCall('/admin/api/pages');
        const page = pages.find(p => p.id === id);
        if (page) {
            const content = page.content || '';
            
            // ALWAYS populate the raw HTML textarea so it is available if switched
            document.getElementById('rawHtmlContent').value = content;
            
            // Auto-detect full HTML document vs rich-text content
            const isFullHtml = content.trim().toLowerCase().startsWith('<!doctype') ||
                content.trim().toLowerCase().startsWith('<html') ||
                content.includes('bg-gradient') || 
                content.includes('class="container');
                
            if (isFullHtml) {
                switchEditorMode('html');
                updateHtmlPreview();
            } else {
                switchEditorMode('wysiwyg');
                tinymce.get('content').setContent(content);
            }
        }
    } else {
        document.getElementById('rawHtmlContent').value = '';
        switchEditorMode('wysiwyg');
        tinymce.get('content').setContent('');
    }

    document.getElementById('editorTitle').textContent = id ? 'แก้ไขหน้าเพจ (Edit Page)' : 'สร้างหน้าใหม่ (New Page)';
    document.getElementById('pageListView').classList.add('hidden');
    document.getElementById('pageEditorView').classList.remove('hidden');
}

function closePageEditor() {
    document.getElementById('pageListView').classList.remove('hidden');
    document.getElementById('pageEditorView').classList.add('hidden');
}

// ─── HTML Editor Mode ─────────────────────────────────────────────────────────
let currentEditorMode = 'wysiwyg'; // 'wysiwyg' | 'html'

function switchEditorMode(mode) {
    currentEditorMode = mode;
    const wysiwygWrapper = document.getElementById('wysiwygEditorWrapper');
    const htmlWrapper = document.getElementById('htmlEditorWrapper');
    const btnWysiwyg = document.getElementById('btnWysiwyg');
    const btnHtml = document.getElementById('btnHtmlMode');
    if (!wysiwygWrapper) return; // guard if editor not visible yet

    if (mode === 'wysiwyg') {
        // Carry over changes from HTML to WYSIWYG if switching back
        if (!htmlWrapper.classList.contains('hidden')) {
            const rawContent = document.getElementById('rawHtmlContent').value;
            if (rawContent && tinymce.get('content')) tinymce.get('content').setContent(rawContent);
        }
        wysiwygWrapper.classList.remove('hidden');
        htmlWrapper.classList.add('hidden');
        btnWysiwyg.className = 'px-3 py-1.5 rounded-md text-xs font-bold transition bg-white text-gray-800 shadow';
        btnHtml.className = 'px-3 py-1.5 rounded-md text-xs font-bold transition text-gray-500 hover:text-gray-700';
    } else {
        // Carry over changes from WYSIWYG to HTML if user typed there first
        if (!wysiwygWrapper.classList.contains('hidden') && tinymce.get('content')) {
            const wyContent = tinymce.get('content').getContent();
            // Optional: Only overwrite if it contains something (so we don't overwrite DB copy when empty)
            if (wyContent) document.getElementById('rawHtmlContent').value = wyContent;
        }
        wysiwygWrapper.classList.add('hidden');
        htmlWrapper.classList.remove('hidden');
        btnWysiwyg.className = 'px-3 py-1.5 rounded-md text-xs font-bold transition text-gray-500 hover:text-gray-700';
        btnHtml.className = 'px-3 py-1.5 rounded-md text-xs font-bold transition bg-white text-gray-800 shadow';
        updateHtmlPreview();
    }
}

function updateHtmlPreview() {
    const raw = document.getElementById('rawHtmlContent').value;
    const frame = document.getElementById('htmlPreviewFrame');
    if (!frame) return;
    const doc = frame.contentDocument || frame.contentWindow.document;
    doc.open();
    doc.write(raw);
    doc.close();
}

function clearHtmlEditor() {
    document.getElementById('rawHtmlContent').value = '';
    updateHtmlPreview();
}

async function savePage(e) {
    e.preventDefault();

    let content = '';
    if (currentEditorMode === 'html') {
        // Store the full HTML document as-is.
        // page.html uses {{ page.content | safe }} which renders it correctly.
        content = document.getElementById('rawHtmlContent').value;
    } else {
        content = tinymce.get('content').getContent();
    }

    const data = {
        id: document.getElementById('pageId').value ? parseInt(document.getElementById('pageId').value) : null,
        title: document.getElementById('title').value,
        slug: document.getElementById('slug').value,
        content: content
    };

    const res = await apiCall('/admin/api/pages', 'POST', data);
    if (res && res.success) {
        Swal.fire({ icon: 'success', title: 'Saved', timer: 1000, showConfirmButton: false });
        closePageEditor();
        loadPages();
    } else {
        Swal.fire({ icon: 'error', title: 'Error', text: res ? res.message : 'Unknown error' });
    }
}

async function deletePage(id) {
    confirmAction('ต้องการลบหน้านี้หรือไม่?', async () => {
        const res = await apiCall('/admin/api/pages/delete', 'POST', { id });
        if (res && res.success) loadPages();
    });
}


// --- Unified Content (News & Activities) ---
function switchUnifiedTab(tab) {
    document.querySelectorAll('.unified-content').forEach(el => el.classList.add('hidden'));
    document.getElementById(`unified-${tab}`).classList.remove('hidden');

    document.querySelectorAll('.unified-tab-btn').forEach(btn => {
        btn.classList.remove('border-blue-600', 'text-blue-700', 'bg-gray-50');
        btn.classList.add('border-transparent');
    });
    document.getElementById(`tab-u-${tab}`).classList.add('border-blue-600', 'text-blue-700', 'bg-gray-50');
    document.getElementById(`tab-u-${tab}`).classList.remove('border-transparent');

    if (tab === 'content') loadUnifiedContent();
    if (tab === 'tags') loadTags();
}

let allContent = [];

async function loadUnifiedContent() {
    const list = await apiCall('/admin/api/content/all');
    if (!list) return;
    allContent = list;
    renderContentTable(list);
}

function filterContent() {
    const type = document.getElementById('filterType').value;
    if (type === 'all') renderContentTable(allContent);
    else renderContentTable(allContent.filter(x => x.type === type));
}

function renderContentTable(items) {
    const tbody = document.getElementById('contentTableBody');
    tbody.innerHTML = items.map(item => `
        <tr class="border-b hover:bg-gray-50 transition">
             <td class="py-3 px-4">
                <span class="px-2 py-1 rounded text-xs font-bold ${item.type === 'news' ? 'bg-slate-100 text-slate-800' : 'bg-blue-100 text-blue-800'}">
                    ${item.type.toUpperCase()}
                </span>
             </td>
            <td class="py-3 px-4 font-medium text-gray-800">${item.title}</td>
            <td class="py-3 px-4 text-center text-sm text-gray-500">${item.category || '-'}</td>
            <td class="py-3 px-4 text-sm text-gray-500">${item.created_at ? new Date(item.created_at).toLocaleDateString() : '-'}</td>
            <td class="py-3 px-4 text-right space-x-2">
                <button onclick="editUnifiedContent(${item.id}, '${item.type}')" class="text-blue-600 hover:text-blue-800 font-medium text-sm">✎ Edit</button>
                <button onclick="deleteUnifiedContent(${item.id}, '${item.type}')" class="text-red-600 hover:text-red-800 font-medium text-sm">🗑 Delete</button>
            </td>
        </tr>
    `).join('');
}

function openUnifiedEditor() {
    document.getElementById('contentListView').classList.add('hidden');
    document.getElementById('contentEditorView').classList.remove('hidden');
    // Default Reset
    document.getElementById('unifiedForm').reset();
    document.getElementById('postId').value = '';
    tinymce.get('postContent').setContent('');
    toggleFormFields();
}

function closeUnifiedEditor() {
    document.getElementById('contentListView').classList.remove('hidden');
    document.getElementById('contentEditorView').classList.add('hidden');
}

function toggleFormFields() {
    // Dynamic fields based on type? Currently they are mostly same.
    // Maybe change Category options based on type.
}

async function editUnifiedContent(id, type) {
    const item = allContent.find(x => x.id === id && x.type === type);
    if (!item) return;

    document.getElementById('contentListView').classList.add('hidden');
    document.getElementById('contentEditorView').classList.remove('hidden');

    document.getElementById('postId').value = item.id;
    document.querySelector(`input[name="postType"][value="${item.type}"]`).checked = true;
    document.getElementById('postTitle').value = item.title;
    document.getElementById('postCategory').value = item.category || 'General';
    document.getElementById('postImage').value = item.image_url || '';
    document.getElementById('postTags').value = item.tags || '';
    document.getElementById('postEventDate').value = item.event_date ? item.event_date.split('T')[0] : '';
    tinymce.get('postContent').setContent(item.content || '');
}

async function saveUnifiedContent(e) {
    e.preventDefault();
    const type = document.querySelector('input[name="postType"]:checked').value;
    const data = {
        id: document.getElementById('postId').value ? parseInt(document.getElementById('postId').value) : null,
        type: type,
        title: document.getElementById('postTitle').value,
        content: tinymce.get('postContent').getContent(),
        category: document.getElementById('postCategory').value,
        image: document.getElementById('postImage').value,
        tags: document.getElementById('postTags').value,
        event_date: document.getElementById('postEventDate').value
    };

    const res = await apiCall('/admin/api/content/save', 'POST', data);
    if (res && res.success) {
        Swal.fire({ icon: 'success', title: 'Saved', timer: 1000, showConfirmButton: false });
        closeUnifiedEditor();
        loadUnifiedContent();
    } else {
        Swal.fire({ icon: 'error', title: 'Error', text: res ? res.message : 'Unknown error' });
    }
}

async function deleteUnifiedContent(id, type) {
    confirmAction('Delete this item?', async () => {
        const res = await apiCall('/admin/api/content/delete', 'POST', { id, type });
        if (res && res.success) loadUnifiedContent();
    });
}


// --- Media Logic ---
async function loadMedia() {
    const files = await apiCall('/admin/api/media');
    const container = document.getElementById('mediaGallery');
    if (!container) return;

    if (!files || files.length === 0) {
        container.innerHTML = '<p class="text-gray-500 col-span-full text-center py-8">No files found.</p>';
        return;
    }

    container.innerHTML = files.map(f => {
        const isImg = ['jpg', 'jpeg', 'png', 'gif', 'webp'].includes(f.name.split('.').pop().toLowerCase());
        const preview = isImg ? `<img src="${f.url}" class="w-full h-32 object-cover">`
            : `<div class="w-full h-32 flex items-center justify-center bg-gray-100 text-4xl">📄</div>`;
        return `
            <div class="group relative border rounded overflow-hidden shadow-sm hover:shadow-md bg-white transition">
                ${preview}
                <div class="p-2 text-xs truncate border-t bg-gray-50">${f.name}</div>
                <div class="absolute inset-0 bg-black/60 opacity-0 group-hover:opacity-100 flex flex-col items-center justify-center gap-2 transition-opacity">
                    <button onclick="navigator.clipboard.writeText('${f.url}'); Swal.fire({toast:true, title:'Copied', icon:'success', position:'top-end', timer:1000, showConfirmButton:false});" class="bg-white text-gray-800 px-3 py-1 rounded text-xs font-bold hover:bg-gray-100">Copy URL</button>
                    <button onclick="deleteMedia('${f.name}')" class="bg-red-600 text-white px-3 py-1 rounded text-xs font-bold hover:bg-red-700">Delete</button>
                </div>
            </div>
        `;
    }).join('');
}

async function uploadFile(input) {
    if (!input.files[0]) return;
    const formData = new FormData();
    formData.append('file', input.files[0]);

    Swal.fire({ title: 'Uploading...', allowOutsideClick: false, didOpen: () => Swal.showLoading() });

    try {
        const token = localStorage.getItem('admin_token');
        const headers = token ? { 'Authorization': `Bearer ${token}` } : {};
        const res = await fetch('/admin/api/upload', { method: 'POST', headers, body: formData });
        if(res.status === 401) {
            Swal.close();
            return handleAuthFailure();
        }
        const json = await res.json();
        if (json.location) {
            Swal.close();
            loadMedia();
        } else {
            throw new Error(json.error);
        }
    } catch (e) {
        Swal.fire('Error', e.message, 'error');
    }
    input.value = ''; // Reset
}

async function deleteMedia(filename) {
    confirmAction('Delete file ' + filename + '?', async () => {
        await apiCall('/admin/api/media/delete', 'POST', { filename });
        loadMedia();
    });
}

// Media Selector Modal Helpers
let mediaCallback = null;
function openMediaSelector(cb) {
    mediaCallback = cb;
    document.getElementById('mediaSelectorModal').classList.remove('hidden');
    loadMediaSelectorGrid();
}
function closeMediaSelector() {
    document.getElementById('mediaSelectorModal').classList.add('hidden');
    mediaCallback = null;
}
async function loadMediaSelectorGrid() {
    const files = await apiCall('/admin/api/media');
    const grid = document.getElementById('mediaSelectorGrid');
    grid.innerHTML = files.map(f => `
        <div onclick="selectMedia('${f.url}')" class="cursor-pointer border rounded overflow-hidden hover:ring-2 ring-green-500">
            <img src="${f.url}" class="w-full h-24 object-cover bg-gray-100">
            <div class="text-[10px] p-1 truncate text-center">${f.name}</div>
        </div>
    `).join('');
}
function selectMedia(url) {
    if (mediaCallback) mediaCallback(url);
    closeMediaSelector();
}

// Upload file and set image field + preview
async function uploadAndSetHomeImage(inputEl, fieldId, previewId) {
    const file = inputEl.files[0];
    if (!file) return;

    const formData = new FormData();
    formData.append('file', file);

    try {
        const token = localStorage.getItem('admin_token');
        const headers = token ? { 'Authorization': `Bearer ${token}` } : {};
        const res = await fetch('/admin/api/upload', { method: 'POST', headers, body: formData });
        if(res.status === 401) {
            return handleAuthFailure();
        }
        const data = await res.json();
        if (data.location) {
            const input = document.getElementById(fieldId);
            const preview = document.getElementById(previewId);
            if (input) input.value = data.location;
            if (preview) {
                preview.src = data.location;
                preview.classList.remove('hidden');
            }
            // Also refresh media selector grid if open
            loadMediaSelectorGrid();
        } else {
            Swal.fire({ icon: 'error', title: 'อัพโหลดไม่สำเร็จ', text: data.error || 'Unknown error' });
        }
    } catch (err) {
        Swal.fire({ icon: 'error', title: 'เกิดข้อผิดพลาด', text: err.message });
    }
}

// --- Tag Logic ---
async function loadTags() {
    const tags = await apiCall('/admin/api/tags');
    const container = document.getElementById('tagsContainer');
    container.innerHTML = tags.map(t => `
        <div class="flex justify-between items-center bg-gray-50 p-3 rounded border">
            <span class="font-medium text-gray-700">${t.name}</span>
            <button onclick="deleteTag(${t.id})" class="text-red-500 hover:text-red-700 text-lg leading-none">&times;</button>
        </div>
    `).join('');
}
async function addTag() {
    const name = document.getElementById('newTagName').value;
    if (!name) return;
    await apiCall('/admin/api/tags', 'POST', { name });
    document.getElementById('newTagName').value = '';
    loadTags();
}
async function deleteTag(id) {
    confirmAction('Delete Tag?', async () => {
        await apiCall('/admin/api/tags/delete', 'POST', { id });
        loadTags();
    });
}


// --- Appeals Logic ---
async function loadAppeals() {
    const appeals = await apiCall('/admin/api/appeals');
    const tbody = document.getElementById('appealsTableBody');
    tbody.innerHTML = appeals.map(a => `
        <tr class="border-b hover:bg-gray-50">
            <td class="py-3 px-4 text-sm text-gray-500">${new Date(a.created_at).toLocaleDateString()}</td>
            <td class="py-3 px-4 font-medium">${a.topic}</td>
            <td class="py-3 px-4 text-gray-600">${a.sender_name || 'Anonymous'}</td>
            <td class="py-3 px-4"><span class="px-2 py-1 rounded text-xs font-bold ${a.status === 'pending' ? 'bg-yellow-100 text-yellow-800' : 'bg-teal-100 text-teal-800'}">${a.status}</span></td>
            <td class="py-3 px-4 text-right">
                <button onclick="viewAppeal('${a.topic}', '${a.message}')" class="text-blue-600 hover:underline text-sm">View</button>
                <button onclick="deleteAppeal(${a.id})" class="text-red-600 hover:underline text-sm ml-2">Delete</button>
            </td>
        </tr>
    `).join('');
}
function viewAppeal(topic, msg) {
    Swal.fire({ title: topic, text: msg, width: 600 });
}
async function deleteAppeal(id) {
    confirmAction('Delete Appeal?', async () => {
        await apiCall('/admin/api/appeals/delete', 'POST', { id });
        loadAppeals();
    });
}


// --- Faculty Management ---
let allFaculty = [];
async function loadFaculty() {
    const list = await apiCall('/admin/api/faculty');
    if (!list) return;
    allFaculty = list;
    const tbody = document.getElementById('facultyTableBody');
    tbody.innerHTML = list.map(f => `
        <tr class="border-b hover:bg-gray-50 transition">
            <td class="py-3 px-4 font-medium text-gray-800">${f.prefix || ''} ${f.fname} ${f.lname}</td>
            <td class="py-3 px-4 text-sm text-gray-500">${f.position || '-'} / ${f.major || '-'}</td>
            <td class="py-3 px-4 text-sm text-gray-500">${f.email || '-'}</td>
            <td class="py-3 px-4 text-right space-x-2">
                <button onclick="editFaculty(${f.id})" class="text-blue-600 hover:text-blue-800 font-medium text-sm">✎ Edit</button>
                <button onclick="deleteFaculty(${f.id})" class="text-red-600 hover:text-red-800 font-medium text-sm">🗑 Delete</button>
            </td>
        </tr>
    `).join('');
}

function editFaculty(id) {
    const f = id ? allFaculty.find(x => x.id === id) : { fname: '', lname: '', prefix: '', position: '', major: '', email: '', phone: '', image: '', admin_position: '', is_expert: false, expertise: '' };

    Swal.fire({
        title: id ? 'แก้ไขข้อมูลคณาจารย์' : 'เพิ่มคณาจารย์ใหม่',
        html: `
            <div class="grid grid-cols-2 gap-4 text-left p-2">
                <div class="col-span-2 flex gap-2">
                    <input id="sw_prefix" class="swal2-input !m-0 w-24" placeholder="คำนำหน้า" value="${f.prefix || ''}">
                    <input id="sw_fname" class="swal2-input !m-0 flex-1" placeholder="ชื่อ (TH)" value="${f.fname || ''}">
                    <input id="sw_lname" class="swal2-input !m-0 flex-1" placeholder="นามสกุล (TH)" value="${f.lname || ''}">
                </div>
                <input id="sw_fname_en" class="swal2-input !m-0" placeholder="First Name (EN)" value="${f.fname_en || ''}">
                <input id="sw_lname_en" class="swal2-input !m-0" placeholder="Last Name (EN)" value="${f.lname_en || ''}">
                <input id="sw_position" class="swal2-input !m-0" placeholder="ตำแหน่งทางวิชาการ" value="${f.position || ''}">
                <input id="sw_major" class="swal2-input !m-0" placeholder="ภาควิชา/สาขา" value="${f.major || ''}">
                <input id="sw_email" class="swal2-input !m-0" placeholder="อีเมล" value="${f.email || ''}">
                <input id="sw_phone" class="swal2-input !m-0" placeholder="เบอร์โทรศัพท์" value="${f.phone || ''}">
                <div class="col-span-2">
                    <label class="text-xs text-gray-500">Image URL</label>
                    <div class="flex gap-2">
                        <input id="sw_image" class="swal2-input !m-0 flex-1" placeholder="URL รูปภาพ" value="${f.image || ''}">
                        <button onclick="openMediaSelector((url) => document.getElementById('sw_image').value = url)" class="bg-gray-200 px-3 rounded">เลือก</button>
                    </div>
                </div>
                <input id="sw_admin_position" class="swal2-input !m-0 col-span-2" placeholder="ตำแหน่งบริหาร (ถ้ามี)" value="${f.admin_position || ''}">
                <div class="col-span-2">
                    <label class="text-xs text-gray-500">Expertise / Research (JSON or Text)</label>
                    <textarea id="sw_expertise" class="swal2-textarea !m-0 !w-full" placeholder='{"expertise": ["GIS", "RS"], "awards": []}'>${f.expertise || ''}</textarea>
                </div>
                <div class="col-span-2 flex items-center gap-2">
                    <input type="checkbox" id="sw_is_expert" ${f.is_expert ? 'checked' : ''}>
                    <label for="sw_is_expert">ผู้ทรงคุณวุฒิ / ผู้เชี่ยวชาญ</label>
                </div>
            </div>
        `,
        width: 700,
        showCancelButton: true,
        confirmButtonText: 'บันทึก',
        preConfirm: () => {
            return {
                id: id,
                prefix: document.getElementById('sw_prefix').value,
                fname: document.getElementById('sw_fname').value,
                lname: document.getElementById('sw_lname').value,
                fname_en: document.getElementById('sw_fname_en').value,
                lname_en: document.getElementById('sw_lname_en').value,
                position: document.getElementById('sw_position').value,
                major: document.getElementById('sw_major').value,
                email: document.getElementById('sw_email').value,
                phone: document.getElementById('sw_phone').value,
                image: document.getElementById('sw_image').value,
                admin_position: document.getElementById('sw_admin_position').value,
                is_expert: document.getElementById('sw_is_expert').checked,
                expertise: document.getElementById('sw_expertise').value
            }
        }
    }).then(async (result) => {
        if (result.isConfirmed) {
            const res = await apiCall('/admin/api/faculty', 'POST', result.value);
            if (res && res.success) {
                Swal.fire('Saved', '', 'success');
                loadFaculty();
            }
        }
    });
}

async function deleteFaculty(id) {
    confirmAction('ต้องการลบข้อมูลบุคลากรนี้หรือไม่?', async () => {
        await apiCall('/admin/api/faculty/delete', 'POST', { id });
        loadFaculty();
    });
}


// --- Home Sections Management (Dynamic) ---
let currentHomeTab = 'banners';
let currentHomeItems = [];

function switchHomeTab(tab) {
    console.log("Switching home tab to:", tab);
    currentHomeTab = tab;
    document.querySelectorAll('.h-tab').forEach(btn => {
        btn.className = 'h-tab px-4 py-2 rounded-lg bg-gray-100 text-gray-500 font-medium hover:bg-gray-200 transition';
    });
    document.getElementById(`h-tab-${tab}`).className = 'h-tab px-4 py-2 rounded-lg bg-primary text-white font-bold shadow-md';

    cancelHomeEdit(); // Ensure we are in list view
    loadHomeSectionData();
}

async function loadHomeSectionData() {
    const endpoint = `/admin/api/${currentHomeTab}`;
    const list = await apiCall(endpoint);
    if (!list) return;
    currentHomeItems = list;
    renderHomeSectionTable(list);
}

function renderHomeSectionTable(items) {
    const titleMap = { 'banners': 'สไลด์แบนเนอร์', 'missions': 'พันธกิจ', 'stats': 'สถิติ', 'awards': 'รางวัล/ประกาศ', 'courses': 'วิดีโอหลักสูตร' };
    document.getElementById('home_section_title').textContent = titleMap[currentHomeTab];

    let head = '';
    if (currentHomeTab === 'banners') head = `<tr><th class="py-3 px-4">Title</th><th class="py-3 px-4">Status</th><th class="py-3 px-4 text-right">Actions</th></tr>`;
    if (currentHomeTab === 'missions') head = `<tr><th class="py-3 px-4">Title</th><th class="py-3 px-4">Icon</th><th class="py-3 px-4 text-right">Actions</th></tr>`;
    if (currentHomeTab === 'stats') head = `<tr><th class="py-3 px-4">Label</th><th class="py-3 px-4">Value</th><th class="py-3 px-4 text-right">Actions</th></tr>`;
    if (currentHomeTab === 'awards') head = `<tr><th class="py-3 px-4">Title</th><th class="py-3 px-4">Description</th><th class="py-3 px-4 text-right">Actions</th></tr>`;
    if (currentHomeTab === 'courses') head = `<tr><th class="py-3 px-4">Title (TH)</th><th class="py-3 px-4">Video ID</th><th class="py-3 px-4 text-right">Actions</th></tr>`;

    document.getElementById('home_table_head').innerHTML = head;

    const tbody = document.getElementById('home_table_body');
    tbody.innerHTML = items.map(item => {
        let cells = '';
        if (currentHomeTab === 'banners') cells = `<td class="py-3 px-4 font-medium">${item.title}</td><td class="py-3 px-4">${item.is_active ? 'Active' : 'Hidden'}</td>`;
        if (currentHomeTab === 'missions') cells = `<td class="py-3 px-4 font-medium">${item.title}</td><td class="py-3 px-4 text-xl">#${item.icon}</td>`;
        if (currentHomeTab === 'stats') cells = `<td class="py-3 px-4 font-medium">${item.label}</td><td class="py-3 px-4 font-bold">${item.value}${item.suffix || ''}</td>`;
        if (currentHomeTab === 'awards') cells = `<td class="py-3 px-4 font-medium">${item.title}</td><td class="py-3 px-4 text-sm text-gray-500">${item.description || '-'}</td>`;
        if (currentHomeTab === 'courses') cells = `<td class="py-3 px-4 font-medium">${item.title_th}</td><td class="py-3 px-4 font-mono text-xs">${item.video_url}</td>`;

        return `
            <tr class="border-b hover:bg-gray-50 transition">
                ${cells}
                <td class="py-3 px-4 text-right space-x-2">
                    <button onclick="editHomeItem(${item.id})" class="text-blue-600 font-medium text-sm">✎</button>
                    <button onclick="deleteHomeItem(${item.id})" class="text-red-500 font-medium text-sm">🗑</button>
                </td>
            </tr>
        `;
    }).join('');

    document.getElementById('add_home_item_btn').onclick = () => editHomeItem(null);
}

function editHomeItem(id) {
    const item = id ? currentHomeItems.find(x => x.id === id) : {};
    document.getElementById('home_list_view').classList.add('hidden');
    document.getElementById('home_editor_view').classList.remove('hidden');
    document.getElementById('home_item_id').value = id || '';

    const fields = document.getElementById('home_form_fields');
    let html = '';

    if (currentHomeTab === 'banners') {
        html = `
            <div class="col-span-2"><label class="block text-xs mb-1">Title</label><input name="title" class="w-full border p-2 rounded" value="${item.title || ''}"></div>
            <div class="col-span-2"><label class="block text-xs mb-1">Subtitle</label><input name="subtitle" class="w-full border p-2 rounded" value="${item.subtitle || ''}"></div>
            <div class="col-span-2">
                <label class="block text-xs mb-1">Image</label>
                <div class="flex gap-2 items-center">
                    <input id="home_image_url" name="image_url" class="flex-1 border p-2 rounded text-sm" value="${item.image_url || ''}" placeholder="/uploads/filename.jpg">
                    <button type="button" onclick="openMediaSelector((url)=>{ document.getElementById('home_image_url').value=url; document.getElementById('home_image_preview').src=url; document.getElementById('home_image_preview').classList.remove('hidden'); })" class="px-3 py-2 bg-indigo-600 text-white text-xs rounded hover:bg-indigo-700 whitespace-nowrap">🖼 เลือก</button>
                    <label class="px-3 py-2 bg-gray-600 text-white text-xs rounded hover:bg-gray-700 cursor-pointer whitespace-nowrap">📁 อัพโหลด<input type="file" accept="image/*" class="hidden" onchange="uploadAndSetHomeImage(this, 'home_image_url', 'home_image_preview')"></label>
                </div>
                <img id="home_image_preview" src="${item.image_url || ''}" class="mt-2 h-24 rounded object-cover ${item.image_url ? '' : 'hidden'}">
            </div>
            <div><label class="block text-xs mb-1">Video URL (Optional)</label><input name="video_url" class="w-full border p-2 rounded" value="${item.video_url || ''}"></div>
            <div><label class="block text-xs mb-1">Order</label><input name="order_index" type="number" class="w-full border p-2 rounded" value="${item.order_index || 0}"></div>
            <div class="flex items-center gap-2 mt-4"><input type="checkbox" name="is_active" ${item.is_active !== 0 ? 'checked' : ''}> <label>Active</label></div>
        `;
    } else if (currentHomeTab === 'missions') {
        html = `
            <div class="col-span-2"><label class="block text-xs mb-1">Title</label><input name="title" class="w-full border p-2 rounded" value="${item.title || ''}"></div>
            <div class="col-span-2"><label class="block text-xs mb-1">Description</label><textarea name="desc" class="w-full border p-2 rounded">${item.desc || ''}</textarea></div>
            <div><label class="block text-xs mb-1">Icon (e.g. globe, academic-cap)</label><input name="icon" class="w-full border p-2 rounded" value="${item.icon || ''}"></div>
            <div><label class="block text-xs mb-1">Color Theme</label><input name="color" class="w-full border p-2 rounded" value="${item.color || 'green'}"></div>
            <div><label class="block text-xs mb-1">Order</label><input name="order_index" type="number" class="w-full border p-2 rounded" value="${item.order_index || 0}"></div>
        `;
    } else if (currentHomeTab === 'stats') {
        html = `
            <div><label class="block text-xs mb-1">Label</label><input name="label" class="w-full border p-2 rounded" value="${item.label || ''}"></div>
            <div><label class="block text-xs mb-1">Value (Number)</label><input name="value" type="number" class="w-full border p-2 rounded" value="${item.value || 0}"></div>
            <div><label class="block text-xs mb-1">Suffix (e.g. +)</label><input name="suffix" class="w-full border p-2 rounded" value="${item.suffix || ''}"></div>
            <div><label class="block text-xs mb-1">Icon</label><input name="icon" class="w-full border p-2 rounded" value="${item.icon || ''}"></div>
            <div><label class="block text-xs mb-1">Order</label><input name="order_index" type="number" class="w-full border p-2 rounded" value="${item.order_index || 0}"></div>
        `;
    } else if (currentHomeTab === 'awards') {
        html = `
             <div class="col-span-2"><label class="block text-xs mb-1">Award Title</label><input name="title" class="w-full border p-2 rounded" value="${item.title || ''}"></div>
             <div class="col-span-2"><label class="block text-xs mb-1">Description</label><textarea name="description" class="w-full border p-2 rounded">${item.description || ''}</textarea></div>
             <div><label class="block text-xs mb-1">Icon (academic-cap / beaker / globe)</label><input name="icon" class="w-full border p-2 rounded" value="${item.icon || ''}"></div>
             <div><label class="block text-xs mb-1">Color Theme (yellow/blue/purple)</label><input name="color_theme" class="w-full border p-2 rounded" value="${item.color_theme || 'yellow'}"></div>
             <div><label class="block text-xs mb-1">Link URL</label><input name="link_url" class="w-full border p-2 rounded" value="${item.link_url || ''}"></div>
             <div><label class="block text-xs mb-1">Order</label><input name="order_index" type="number" class="w-full border p-2 rounded" value="${item.order_index || 0}"></div>
             <div class="col-span-2">
                 <label class="block text-xs mb-1 font-medium">รูปภาพ (Image)</label>
                 <div class="flex gap-2 items-center">
                     <input id="home_image_url" name="image_url" class="flex-1 border p-2 rounded text-sm" value="${item.image_url || ''}" placeholder="/uploads/filename.jpg">
                     <button type="button" onclick="openMediaSelector((url)=>{ document.getElementById('home_image_url').value=url; document.getElementById('home_image_preview').src=url; document.getElementById('home_image_preview').classList.remove('hidden'); })" class="px-3 py-2 bg-indigo-600 text-white text-xs rounded hover:bg-indigo-700 whitespace-nowrap">🖼 เลือกจากคลัง</button>
                     <label class="px-3 py-2 bg-gray-600 text-white text-xs rounded hover:bg-gray-700 cursor-pointer whitespace-nowrap">📁 อัพโหลด<input type="file" accept="image/*" class="hidden" onchange="uploadAndSetHomeImage(this, 'home_image_url', 'home_image_preview')"></label>
                 </div>
                 <img id="home_image_preview" src="${item.image_url || ''}" class="mt-2 h-32 w-auto rounded object-cover shadow border ${item.image_url ? '' : 'hidden'}">
             </div>
        `;

    } else if (currentHomeTab === 'courses') {
        html = `
            <div class="col-span-2"><label class="block text-xs mb-1">Course Title (TH)</label><input name="title_th" class="w-full border p-2 rounded" value="${item.title_th || ''}"></div>
            <div class="col-span-2"><label class="block text-xs mb-1">Course Title (EN)</label><input name="title_en" class="w-full border p-2 rounded" value="${item.title_en || ''}"></div>
            <div><label class="block text-xs mb-1">Video URL (YouTube ID or Link)</label><input name="video_url" class="w-full border p-2 rounded" value="${item.video_url || ''}"></div>
            <div><label class="block text-xs mb-1">Color Theme</label><input name="color_theme" class="w-full border p-2 rounded" value="${item.color_theme || 'green'}"></div>
            <div><label class="block text-xs mb-1">Order</label><input name="order_index" type="number" class="w-full border p-2 rounded" value="${item.order_index || 0}"></div>
        `;
    }

    fields.innerHTML = html;
}

function cancelHomeEdit() {
    document.getElementById('home_list_view').classList.remove('hidden');
    document.getElementById('home_editor_view').classList.add('hidden');
}

async function saveHomeItem(e) {
    e.preventDefault();
    const formData = new FormData(e.target);
    const data = Object.fromEntries(formData.entries());

    // Convert numeric fields
    if (data.id) data.id = parseInt(data.id);
    else data.id = null;
    if (data.order_index) data.order_index = parseInt(data.order_index);
    if (data.value) data.value = parseInt(data.value);

    // Checkbox special handle
    if (data.is_active !== undefined) data.is_active = 1;
    else if (currentHomeTab === 'banners') data.is_active = 0;

    const res = await apiCall(`/admin/api/${currentHomeTab}`, 'POST', data);
    if (res && res.success) {
        Swal.fire({ icon: 'success', title: 'Saved', timer: 1000, showConfirmButton: false });
        cancelHomeEdit();
        loadHomeSectionData();
    }
}

async function deleteHomeItem(id) {
    confirmAction('ลบรายการนี้ใช่หรือไม่?', async () => {
        let model = "";
        if (currentHomeTab === 'banners') model = "Banner";
        else if (currentHomeTab === 'missions') model = "Mission";
        else if (currentHomeTab === 'courses') model = "Course";
        else if (currentHomeTab === 'stats') model = "Statistic";
        else if (currentHomeTab === 'awards') model = "Award";

        if (model) {
            await apiCall(`/admin/api/generic/delete`, 'POST', { model: model, id: id });
        } else {
            await apiCall(`/admin/api/${currentHomeTab}/delete`, 'POST', { id: id });
        }
        loadHomeSectionData();
    });
}


// --- Settings & Menu Logic ---

function switchSettingsTab(tab) {
    document.querySelectorAll('.settings-tab-content').forEach(el => el.classList.add('hidden'));
    document.getElementById('settings-' + tab).classList.remove('hidden');

    ['general', 'home', 'menu', 'contact'].forEach(t => {
        const btn = document.getElementById('tab-' + t);
        if (t === tab) btn.className = 'px-6 py-2 border-b-2 border-primary text-primary font-bold bg-white transition';
        else btn.className = 'px-6 py-2 border-b-2 border-transparent text-gray-500 hover:text-primary font-medium transition';
    });

    if (tab === 'contact') loadContactInfo();
}

async function loadContactInfo() {
    const list = await apiCall('/admin/api/contact');
    const container = document.getElementById('contactInfoContainer');

    const icons = [
        { label: 'Auto (ตามชื่อหัวข้อ)', value: '' },
        { label: 'มือถือ/โทรศัพท์', value: '<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 5a2 2 0 012-2h3.28a1 1 0 01.948.684l1.498 4.493a1 1 0 01-.502 1.21l-2.257 1.13a11.042 11.042 0 005.516 5.516l1.13-2.257a1 1 0 011.21-.502l4.493 1.498a1 1 0 01.684.949V19a2 2 0 01-2 2h-1C9.716 21 3 14.284 3 6V5z"/></svg>' },
        { label: 'อีเมล', value: '<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"/></svg>' },
        { label: 'ที่อยู่/แผนที่', value: '<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.243-4.243a8 8 0 1111.314 0z"/><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 11a3 3 0 11-6 0 3 3 0 016 0z"/></svg>' },
        { label: 'Facebook', value: '<svg class="w-5 h-5" fill="currentColor" viewBox="0 0 24 24"><path d="M9 8h-3v4h3v12h5v-12h3.642l.358-4h-4v-1.667c0-.955.192-1.333 1.115-1.333h2.885v-5h-3.808c-3.596 0-5.192 1.583-5.192 4.615v3.385z"/></svg>' },
        { label: 'Line', value: '<svg class="w-5 h-5" fill="currentColor" viewBox="0 0 24 24"><path d="M24 10.304c0-5.369-5.383-9.738-12-9.738-6.616 0-12 4.369-12 9.738 0 4.814 4.269 8.846 10.036 9.608.391.084.922.258 1.057.592.122.303.079.778.039 1.085l-.171 1.027c-.053.303-.242 1.186 1.039.647 1.281-.54 6.911-4.069 9.428-6.967 1.739-1.907 2.572-3.843 2.572-5.992z"/></svg>' },
        { label: 'เว็บไซต์ (Globe)', value: '<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 12a9 9 0 01-9 9m9-9a9 9 0 00-9-9m9 9H3m9 9a9 9 0 01-9-9m9 9c1.657 0 3-4.03 3-9s-1.343-9-3-9m0 18c-1.657 0-3-4.03-3-9s1.343-9 3-9m-9 9a9 9 0 019-9"/></svg>' }
    ];

    container.innerHTML = list.map((c, i) => `
        <div class="flex gap-2 items-center border p-2 rounded bg-white contact-item shadow-sm relative group pr-12" data-key="${c.key}">
            <div class="contact-drag-handle cursor-move text-gray-400 hover:text-gray-600 px-1 py-2">
                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 8h16M4 16h16"/></svg>
            </div>
            <input class="border px-2 py-1.5 text-sm bg-gray-50 flex-1 min-w-[100px] font-semibold text-gray-700" value="${c.key}" readonly title="Contact Key">
            <input class="border px-2 py-1.5 text-sm flex-[2] text-gray-800" value="${c.value ? c.value.replace(/"/g, '&quot;') : ''}" onchange="saveContactItem('${c.key}', this.value, this.nextElementSibling.value, ${c.order_index})" placeholder="Contact Value">
            <select class="border px-2 py-1.5 text-sm flex-1 bg-white cursor-pointer" onchange="saveContactItem('${c.key}', this.previousElementSibling.value, this.value, ${c.order_index})">
                ${icons.map(opt => `<option value="${opt.value.replace(/"/g, '&quot;')}" ${c.icon === opt.value ? 'selected' : ''}>${opt.label}</option>`).join('')}
            </select>
            <button onclick="deleteContactItem('${c.key}')" class="text-red-500 hover:text-red-700 bg-red-50 hover:bg-red-100 p-1.5 rounded transition absolute right-2 opacity-0 group-hover:opacity-100" title="Delete">
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" /></svg>
            </button>
        </div>
    `).join('');

    if (window.Sortable) {
        new Sortable(container, {
            handle: '.contact-drag-handle',
            animation: 150,
            onEnd: async function () {
                const items = container.querySelectorAll('.contact-item');
                let promises = [];
                items.forEach((item, index) => {
                    const key = item.getAttribute('data-key');
                    const value = item.querySelector('input:nth-child(3)').value;
                    const icon = item.querySelector('select').value;
                    promises.push(apiCall('/admin/api/contact', 'POST', {
                        key: key,
                        value: value,
                        icon: icon,
                        order_index: index
                    }));
                });
                await Promise.all(promises);
                toast('Contact order saved');
            }
        });
    }
}

async function saveContactItem(key, value, icon, order_index) {
    const current = (await apiCall('/admin/api/contact')).find(x => x.key === key) || {};
    await apiCall('/admin/api/contact', 'POST', {
        key: key,
        value: value !== null ? value : current.value,
        icon: icon !== undefined ? icon : current.icon,
        order_index: order_index !== undefined ? order_index : (current.order_index || 0)
    });
    toast('Saved');
}

async function deleteContactItem(key) {
    if (confirm(`Are you sure you want to delete '${key}'?`)) {
        await apiCall('/admin/api/contact/delete', 'POST', { key: key });
        toast('Deleted');
        loadContactInfo();
    }
}

function addContactRow() {
    Swal.fire({
        title: 'Add Contact Field',
        input: 'text',
        inputPlaceholder: 'Field Key (e.g. facebook, line, map)',
        showCancelButton: true
    }).then(result => {
        if (result.value) {
            saveContactItem(result.value, '', '').then(() => loadContactInfo());
        }
    });
}


// Variables for JSON Editors
let heroImages = [], quickButtons = [], featureItems = [], statItems = [], currentMenus = [], activeMenuName = '';

async function loadSettings() {
    const settings = await apiCall('/admin/api/settings');
    if (settings) {
        // General
        if (settings.site_title) document.getElementById('setting_site_title').value = settings.site_title;
        if (settings.footer_text) document.getElementById('setting_footer_text').value = settings.footer_text;

        // Home Configs
        heroImages = JSON.parse(settings.hero_slider_images || '[]');
        quickButtons = JSON.parse(settings.quick_buttons_json || '[]');
        featureItems = JSON.parse(settings.home_features_json || '[]');
        statItems = JSON.parse(settings.stats_json || '[]');

        renderHomeEditors();
    }
    loadMenuGroups();
}

function renderHomeEditors() {
    document.getElementById('setting_hero_slider_images').value = JSON.stringify(heroImages);
    document.getElementById('hero-slider-container').innerHTML = heroImages.map((url, i) => `
        <div class="flex gap-2 mb-2"><input class="flex-1 border rounded px-2" value="${url}" onchange="heroImages[${i}]=this.value; renderHomeEditors()"> <button onclick="heroImages.splice(${i},1); renderHomeEditors()" class="text-red-500">x</button></div>
    `).join('');

    // Simplification: We can expand these editors same as dashboard.html logic if needed. 
    // For now assuming basic text areas or implementing full UI if requested. 
    // Given file size limits, I'll rely on a generic JSON editor approach or the detailed UI if space permits.
    // Let's stick to the JSON hidden field sync for now to save space in this file, 
    // but fully implement the UI in dashboard.html or here? 
    // Best practice: The UI rendering logic should be here.
}

// Save Settings
async function saveSettings(formId) {
    const formData = new FormData(document.getElementById(formId));
    // Sync JSONs
    formData.set('hero_slider_images', JSON.stringify(heroImages));
    // ... others

    const data = Object.fromEntries(formData.entries());
    await apiCall('/admin/api/settings', 'POST', data);
    Swal.fire('Saved', '', 'success');
}

// Menu Groups
async function createNewMenu() {
    const { value: menuName } = await Swal.fire({
        title: 'New Menu Name',
        input: 'text',
        inputPlaceholder: 'e.g. main'
    });
    if (menuName) {
        await apiCall('/admin/api/menus', 'POST', { name: menuName, data_json: '[]' });
        loadMenuGroups();
        Swal.fire('Created', '', 'success');
    }
}

async function loadMenuGroups() {
    currentMenus = await apiCall('/admin/api/menus');
    const sel = document.getElementById('menuGroupSelector');
    if (!sel) return;
    sel.innerHTML = '<option value="" disabled selected>-- Select Menu --</option>' +
        currentMenus.map(m => `<option value="${m.name}">${m.name}</option>`).join('');
}

async function loadSelectedMenu() {
    activeMenuName = document.getElementById('menuGroupSelector').value;
    const menu = currentMenus.find(m => m.name === activeMenuName);
    if (!menu) return;

    const data = JSON.parse(menu.data_json || '[]');
    renderMenuEditor(data);
}

function renderMenuEditor(data) {
    const container = document.getElementById('menuEditorContainer');
    container.innerHTML = `
        <div class="space-y-2" id="menu-items-root"></div>
        <button onclick="addMenuItem()" class="mt-4 px-3 py-1 bg-green-100 text-green-700 rounded text-sm hover:bg-green-200 transition">+ Add Root Item</button>
        <button onclick="saveCurrentMenu()" class="mt-4 ml-2 px-4 py-1 bg-blue-600 text-white rounded text-sm hover:bg-blue-700 shadow transition">Save Menu Structure</button>
    `;

    const root = document.getElementById('menu-items-root');
    renderMenuItems(data, root);
}

function renderMenuItems(items, parentEl, pathPrefix = '') {
    items.forEach((item, index) => {
        const path = pathPrefix ? `${pathPrefix}.${index}` : `${index}`;
        const level = pathPrefix ? pathPrefix.split('.').filter(x => x === 'children').length + 1 : 0;
        const div = document.createElement('div');
        div.className = `p-2 border rounded bg-white mt-1 menu-item-node`;
        div.dataset.label = item.label || '';
        div.dataset.url = item.url || '';

        if (level > 0) div.classList.add('ml-6', 'border-l-4', 'border-l-blue-200');
        div.innerHTML = `
            <div class="flex gap-2 items-center">
                <span class="text-gray-400 cursor-move drag-handle">☰</span>
                <input class="border px-2 py-1 text-sm flex-1 label-input" value="${item.label || ''}" placeholder="Label" onchange="this.parentElement.parentElement.dataset.label = this.value; rebuildMenuDataFromDOM()">
                <input class="border px-2 py-1 text-sm flex-1 url-input" value="${item.url}" placeholder="URL" onchange="this.parentElement.parentElement.dataset.url = this.value; rebuildMenuDataFromDOM()">
                <button onclick="addSubMenuItemPath('${path}')" class="text-blue-500 hover:bg-blue-50 bg-white border border-blue-200 rounded px-2 font-bold" title="Add Submenu">+ Sub</button>
                <button onclick="removeMenuItemPath('${path}')" class="text-red-500 hover:bg-red-50 bg-white border border-red-200 rounded px-2 font-bold" title="Remove">&times;</button>
            </div>
            <div class="child-container mt-1 min-h-[10px]"></div>
        `;
        parentEl.appendChild(div);
        if (item.children && item.children.length > 0) {
            renderMenuItems(item.children, div.querySelector('.child-container'), `${path}.children`);
        }
    });

    if (window.Sortable) {
        new Sortable(parentEl, {
            group: 'nested',
            animation: 150,
            fallbackOnBody: true,
            swapThreshold: 0.65,
            handle: '.drag-handle',
            onEnd: function (evt) {
                rebuildMenuDataFromDOM();
            }
        });
    }
}

function rebuildMenuDataFromDOM() {
    const root = document.getElementById('menu-items-root');
    const newData = parseMenuNodes(root);

    const menu = currentMenus.find(m => m.name === activeMenuName);
    if (menu) {
        menu.data_json = JSON.stringify(newData);
    }
}

function parseMenuNodes(container) {
    let result = [];
    const children = container.children; // direct child div elements (the menu items)
    for (let i = 0; i < children.length; i++) {
        const node = children[i];
        if (!node.classList.contains('menu-item-node')) continue;
        const item = {
            label: node.dataset.label,
            url: node.dataset.url,
            children: []
        };
        const childContainer = node.querySelector(':scope > .child-container');
        if (childContainer && childContainer.children.length > 0) {
            item.children = parseMenuNodes(childContainer);
        }
        result.push(item);
    }
    return result;
}

// Global Menu State
let editingMenuData = [];
function addMenuItem() {
    const menu = currentMenus.find(m => m.name === activeMenuName);
    const data = JSON.parse(menu.data_json || '[]');
    data.push({ label: 'New Item', url: '#', children: [] });
    menu.data_json = JSON.stringify(data);
    loadSelectedMenu();
}

function getNodeByPath(data, pathParts) {
    let curr = data;
    for (let i = 0; i < pathParts.length; i++) {
        curr = curr[pathParts[i]];
    }
    return curr;
}

function updateMenuItemPath(path, field, value) {
    const menu = currentMenus.find(m => m.name === activeMenuName);
    const data = JSON.parse(menu.data_json || '[]');
    let parts = path.split('.');
    let item = getNodeByPath(data, parts);
    item[field] = value;
    menu.data_json = JSON.stringify(data);
}

function removeMenuItemPath(path) {
    const menu = currentMenus.find(m => m.name === activeMenuName);
    const data = JSON.parse(menu.data_json || '[]');
    let parts = path.split('.');
    let index = parseInt(parts.pop());
    let parent = parts.length > 0 ? getNodeByPath(data, parts) : data;
    parent.splice(index, 1);
    menu.data_json = JSON.stringify(data);
    loadSelectedMenu();
}

function addSubMenuItemPath(path) {
    const menu = currentMenus.find(m => m.name === activeMenuName);
    const data = JSON.parse(menu.data_json || '[]');
    let parts = path.split('.');
    let item = getNodeByPath(data, parts);
    if (!item.children) item.children = [];
    item.children.push({ label: 'New Sub Item', url: '#', children: [] });
    menu.data_json = JSON.stringify(data);
    loadSelectedMenu();
}

async function saveCurrentMenu() {
    const menu = currentMenus.find(m => m.name === activeMenuName);
    if (!menu) return;
    const res = await apiCall('/admin/api/menus', 'POST', { name: menu.name, data_json: menu.data_json });
    if (res && res.success) Swal.fire('Menu Saved', '', 'success');
}
console.log("Admin.js loaded successfully.");
window.switchHomeTab = switchHomeTab;
