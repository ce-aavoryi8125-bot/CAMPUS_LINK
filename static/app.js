// CampusLink Web Application Engine

let currentUser = null;
let currentReportId = 1;
let categoriesList = [];
let uploadedListingImageUrl = 'assets/logo.jpg';

document.addEventListener('DOMContentLoaded', () => {
    initApp();
});

async function initApp() {
    applyStoredTheme();
    await fetchDbStatus();
    await loadDemoAccounts();
    await loadCategories();
    
    // Check if user session exists in localStorage
    const savedUser = localStorage.getItem('campuslink_user');
    if (savedUser) {
        try {
            currentUser = JSON.parse(savedUser);
            showMainAppScreen();
        } catch (e) {
            showAuthScreen();
        }
    } else {
        showAuthScreen();
    }
}

// --- THEME ENGINE (LIGHT & AMBIENT DARK MODES) ---

function applyStoredTheme() {
    const theme = localStorage.getItem('campuslink_theme') || 'dark';
    const body = document.body;
    
    if (theme === 'light') {
        body.classList.remove('dark-theme');
        body.classList.add('light-theme');
        updateThemeIconUI(true);
    } else {
        body.classList.remove('light-theme');
        body.classList.add('dark-theme');
        updateThemeIconUI(false);
    }
}

function toggleTheme() {
    const body = document.body;
    const isLight = body.classList.contains('light-theme');
    
    if (isLight) {
        body.classList.remove('light-theme');
        body.classList.add('dark-theme');
        localStorage.setItem('campuslink_theme', 'dark');
        updateThemeIconUI(false);
        showToast('Switched to Ambient Dark Mode', 'info');
    } else {
        body.classList.remove('dark-theme');
        body.classList.add('light-theme');
        localStorage.setItem('campuslink_theme', 'light');
        updateThemeIconUI(true);
        showToast('Switched to Light Mode', 'info');
    }
}

function updateThemeIconUI(isLight) {
    const iconHeader = document.getElementById('headerThemeIcon');
    const iconBtn = document.getElementById('themeToggleIconBtn');
    const textBtn = document.getElementById('themeToggleText');
    
    if (isLight) {
        if (iconHeader) iconHeader.className = 'fa-solid fa-sun';
        if (iconBtn) iconBtn.className = 'fa-solid fa-moon';
        if (textBtn) textBtn.innerText = 'Dark Mode';
    } else {
        if (iconHeader) iconHeader.className = 'fa-solid fa-moon';
        if (iconBtn) iconBtn.className = 'fa-solid fa-sun';
        if (textBtn) textBtn.innerText = 'Light Mode';
    }
}

// --- SCREEN TOGGLING & AUTH ---

function showAuthScreen() {
    document.getElementById('authScreen').classList.remove('hidden');
    document.getElementById('mainAppScreen').classList.add('hidden');
}

function showMainAppScreen() {
    if (!currentUser) return;
    document.getElementById('authScreen').classList.add('hidden');
    document.getElementById('mainAppScreen').classList.remove('hidden');
    
    updateUserProfileDisplay();
    switchTab('marketplace');
    loadListings();
    loadSavedAndWishlist();
}

function switchAuthTab(tab) {
    const loginForm = document.getElementById('loginForm');
    const regForm = document.getElementById('registerForm');
    const tabBtnLogin = document.getElementById('tabBtnLogin');
    const tabBtnRegister = document.getElementById('tabBtnRegister');
    
    if (tab === 'login') {
        loginForm.classList.remove('hidden');
        regForm.classList.add('hidden');
        tabBtnLogin.classList.add('active');
        tabBtnRegister.classList.remove('active');
    } else {
        loginForm.classList.add('hidden');
        regForm.classList.remove('hidden');
        tabBtnLogin.classList.remove('active');
        tabBtnRegister.classList.add('active');
    }
}

function togglePasswordVisibility(inputId, iconId) {
    const input = document.getElementById(inputId);
    const icon = document.getElementById(iconId);
    if (input.type === 'password') {
        input.type = 'text';
        icon.className = 'fa-solid fa-eye-slash';
    } else {
        input.type = 'password';
        icon.className = 'fa-solid fa-eye';
    }
}

async function handleLoginSubmit(e) {
    e.preventDefault();
    const email = document.getElementById('loginEmail').value;
    const password = document.getElementById('loginPassword').value;
    
    try {
        const res = await fetch('/api/auth/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password })
        });
        const data = await res.json();
        
        if (data.success) {
            currentUser = data.user;
            localStorage.setItem('campuslink_user', JSON.stringify(currentUser));
            showToast(`Welcome back, ${currentUser.name}!`, 'success');
            showMainAppScreen();
        } else {
            showToast(data.message || 'Login failed', 'error');
        }
    } catch (err) {
        showToast('Server connection error', 'error');
    }
}

async function handleRegisterSubmit(e) {
    e.preventDefault();
    const payload = {
        name: document.getElementById('regName').value,
        email: document.getElementById('regEmail').value,
        student_id: document.getElementById('regStudentId').value,
        phone: document.getElementById('regPhone').value,
        department: document.getElementById('regDepartment').value,
        password: document.getElementById('regPassword').value,
        hostel: 'Chamber of Mines Hostel'
    };
    
    try {
        const res = await fetch('/api/auth/register', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const data = await res.json();
        
        if (data.success) {
            currentUser = data.user;
            localStorage.setItem('campuslink_user', JSON.stringify(currentUser));
            showToast('Account registered successfully! Welcome to CampusLink.', 'success');
            showMainAppScreen();
        } else {
            showToast(data.message || 'Registration failed', 'error');
        }
    } catch (err) {
        showToast('Registration error', 'error');
    }
}

function handleLogout() {
    currentUser = null;
    localStorage.removeItem('campuslink_user');
    showToast('Logged out of CampusLink session', 'info');
    showAuthScreen();
}

function updateUserProfileDisplay() {
    if (!currentUser) return;
    document.getElementById('userNameMeta').innerText = currentUser.name;
    document.getElementById('userRoleMeta').innerText = `${currentUser.verification_level} • ${currentUser.department}`;
    
    const initials = currentUser.name.split(' ').map(n => n[0]).join('').substring(0, 2).toUpperCase();
    document.getElementById('userAvatarCircle').innerText = initials;
    if (document.getElementById('profileAvatarLarge')) {
        document.getElementById('profileAvatarLarge').innerText = initials;
    }
    
    // ROLE-BASED ACCESS CONTROL (RBAC)
    const isAdmin = currentUser.user_id === 6 || currentUser.verification_level === 'Admin' || (currentUser.email && currentUser.email.includes('admin'));
    const adminElements = document.querySelectorAll('.admin-only-feature');
    
    adminElements.forEach(el => {
        if (isAdmin) {
            el.classList.remove('hidden');
        } else {
            el.classList.add('hidden');
        }
    });
    
    if (isAdmin) {
        loadReportMenu();
        fetchReport(1);
    }
}

// --- DEMO ACCOUNTS QUICK CARDS ---

async function loadDemoAccounts() {
    try {
        const res = await fetch('/api/demo-accounts');
        const accounts = await res.json();
        
        const container = document.getElementById('demoAccountsContainer');
        container.innerHTML = '';
        
        accounts.forEach(acc => {
            const card = document.createElement('div');
            card.className = 'demo-card';
            card.onclick = () => quickDemoLogin(acc);
            card.innerHTML = `
                <span class="demo-name">${acc.name}</span>
                <span class="demo-role">${acc.role}</span>
            `;
            container.appendChild(card);
        });
    } catch (e) {
        console.error('Failed to load demo accounts', e);
    }
}

async function quickDemoLogin(account) {
    document.getElementById('loginEmail').value = account.email;
    document.getElementById('loginPassword').value = account.password;
    
    showToast(`Authenticating ${account.name}...`, 'info');
    
    try {
        const res = await fetch('/api/auth/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email: account.email, password: account.password })
        });
        const data = await res.json();
        
        if (data.success) {
            currentUser = data.user;
            localStorage.setItem('campuslink_user', JSON.stringify(currentUser));
            showToast(`Instant Demo Access: Logged in as ${currentUser.name}`, 'success');
            showMainAppScreen();
        } else {
            showToast('Demo login error', 'error');
        }
    } catch (err) {
        showToast('Login connection failed', 'error');
    }
}

// --- DATABASE STATUS & CONFIG ---

async function fetchDbStatus() {
    try {
        const res = await fetch('/api/status');
        const data = await res.json();
        
        const pillLabel = document.getElementById('dbEngineLabel');
        if (pillLabel) {
            pillLabel.innerText = `ENGINE: ${data.engine}`;
        }
        
        document.getElementById('infoEngine').innerText = data.engine;
        document.getElementById('infoHost').innerText = data.host;
        document.getElementById('infoDb').innerText = data.database;
    } catch (e) {
        console.error('Failed to fetch DB status', e);
    }
}

async function saveDbConfig(e) {
    e.preventDefault();
    const config = {
        host: document.getElementById('cfgHost').value,
        port: document.getElementById('cfgPort').value,
        user: document.getElementById('cfgUser').value,
        password: document.getElementById('cfgPassword').value,
        database: document.getElementById('cfgDatabase').value
    };
    
    showToast('Connecting & Migrating to MySQL...', 'info');
    try {
        const res = await fetch('/api/db/config', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(config)
        });
        const status = await res.json();
        
        if (status.engine === 'MYSQL') {
            showToast('Successfully connected and migrated to MySQL!', 'success');
        } else {
            showToast('Could not connect to MySQL. SQLite remains active.', 'warning');
        }
        fetchDbStatus();
    } catch (err) {
        showToast('Database configuration error', 'error');
    }
}

// --- TAB SWITCHING ---

function switchTab(tabId) {
    document.querySelectorAll('.nav-tab').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
    
    const targetTab = document.getElementById(`tab-${tabId}`);
    if (targetTab) targetTab.classList.add('active');
    
    const activeBtn = Array.from(document.querySelectorAll('.nav-tab')).find(b => b.getAttribute('onclick') && b.getAttribute('onclick').includes(tabId));
    if (activeBtn) activeBtn.classList.add('active');
    
    if (tabId === 'my-rentals') loadUserRentals();
    if (tabId === 'trust') loadTrustScore();
    if (tabId === 'saved-wishlist') loadSavedAndWishlist();
    if (tabId === 'profile') loadProfileData();
}

// --- USER PROFILE & PASSWORD SETTINGS ---

function loadProfileData() {
    if (!currentUser) return;
    document.getElementById('profName').value = currentUser.name || '';
    document.getElementById('profEmail').value = currentUser.email || '';
    document.getElementById('profPhone').value = currentUser.phone || '+233241234567';
    document.getElementById('profHostel').value = currentUser.hostel || 'Chamber of Mines Hostel';
    document.getElementById('profDepartment').value = currentUser.department || 'Geomatic Engineering';
}

async function handleProfileUpdate(e) {
    e.preventDefault();
    if (!currentUser) return;
    
    const payload = {
        user_id: currentUser.user_id,
        phone: document.getElementById('profPhone').value,
        hostel: document.getElementById('profHostel').value,
        department: document.getElementById('profDepartment').value
    };
    
    try {
        const res = await fetch('/api/user/profile', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const data = await res.json();
        
        if (data.success) {
            currentUser.phone = payload.phone;
            currentUser.hostel = payload.hostel;
            currentUser.department = payload.department;
            localStorage.setItem('campuslink_user', JSON.stringify(currentUser));
            
            updateUserProfileDisplay();
            showToast('Account profile updated successfully!', 'success');
        } else {
            showToast(data.message || 'Profile update failed', 'error');
        }
    } catch (err) {
        showToast('Error saving profile changes', 'error');
    }
}

async function handleAvatarFileSelect(e) {
    const file = e.target.files[0];
    if (!file) return;
    
    const reader = new FileReader();
    reader.onload = async function(evt) {
        const base64Data = evt.target.result;
        try {
            const res = await fetch('/api/upload-image', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ image_data: base64Data })
            });
            const data = await res.json();
            if (data.success) {
                showToast('Profile picture uploaded!', 'success');
            }
        } catch (err) {
            showToast('Error uploading picture', 'error');
        }
    };
    reader.readAsDataURL(file);
}

async function handlePasswordChange(e) {
    e.preventDefault();
    if (!currentUser) return;
    
    const oldPw = document.getElementById('pwOld').value;
    const newPw = document.getElementById('pwNew').value;
    const confirmPw = document.getElementById('pwConfirm').value;
    
    if (newPw !== confirmPw) {
        showToast('New passwords do not match', 'error');
        return;
    }
    
    try {
        const res = await fetch('/api/user/change-password', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                user_id: currentUser.user_id,
                old_password: oldPw,
                new_password: newPw
            })
        });
        const data = await res.json();
        
        if (data.success) {
            showToast('Password changed successfully!', 'success');
            document.getElementById('pwOld').value = '';
            document.getElementById('pwNew').value = '';
            document.getElementById('pwConfirm').value = '';
        } else {
            showToast(data.message || 'Current password incorrect', 'error');
        }
    } catch (err) {
        showToast('Password update error', 'error');
    }
}

// --- MARKETPLACE & LISTINGS ---

async function loadCategories() {
    try {
        const res = await fetch('/api/categories');
        categoriesList = await res.json();
        
        const filter = document.getElementById('categoryFilter');
        const modalSelect = document.getElementById('newCategory');
        
        filter.innerHTML = '<option value="all">All 13 Categories</option>';
        if (modalSelect) modalSelect.innerHTML = '';
        
        categoriesList.forEach(c => {
            const opt1 = document.createElement('option');
            opt1.value = c.category_id;
            opt1.innerText = c.name;
            filter.appendChild(opt1);
            
            if (modalSelect) {
                const opt2 = document.createElement('option');
                opt2.value = c.category_id;
                opt2.innerText = c.name;
                modalSelect.appendChild(opt2);
            }
        });
    } catch (e) {
        console.error('Failed to load categories', e);
    }
}

async function loadListings() {
    const cat = document.getElementById('categoryFilter').value;
    const search = document.getElementById('searchInput').value;
    
    let url = `/api/listings?category_id=${cat}&search=${encodeURIComponent(search)}`;
    try {
        const res = await fetch(url);
        const listings = await res.json();
        
        document.getElementById('resultsCount').innerText = `${listings.length} Items Found`;
        renderListingsGrid(listings);
    } catch (e) {
        console.error('Failed to load listings', e);
    }
}

function handleSearch() {
    loadListings();
}

function renderListingsGrid(listings) {
    const grid = document.getElementById('listingsGrid');
    grid.innerHTML = '';
    
    if (listings.length === 0) {
        grid.innerHTML = `<div class="no-results card" style="grid-column: 1/-1; text-align: center; padding: 3rem;">
            <i class="fa-solid fa-box-open" style="font-size: 3rem; color: var(--text-subtle); margin-bottom: 1rem;"></i>
            <h3>No Equipment Found</h3>
            <p class="text-subtle">Try broadening your search term or selecting another category.</p>
        </div>`;
        return;
    }
    
    listings.forEach(item => {
        const card = document.createElement('div');
        card.className = 'listing-card';
        
        const imgSrc = item.thumbnail_path && item.thumbnail_path.length > 5 ? `/${item.thumbnail_path}` : '/assets/logo.jpg';
        
        card.innerHTML = `
            <div class="card-img-wrapper">
                <img src="${imgSrc}" alt="${item.title}" onerror="this.src='/assets/logo.jpg'">
                <span class="condition-badge">${item.condition}</span>
            </div>
            <div class="card-body-content">
                <span class="item-category">${item.category_name}</span>
                <h4 class="item-title">${item.title}</h4>
                <div class="item-meta">
                    <span><i class="fa-solid fa-user"></i> ${item.owner_name}</span>
                    <span><i class="fa-solid fa-location-dot"></i> ${item.pickup_location}</span>
                </div>
                <div class="pricing-row">
                    <div>
                        <div class="daily-rate">GH₵ ${item.rental_rate_per_day.toFixed(2)} <span>/ day</span></div>
                        <div class="deposit-text">Deposit: GH₵ ${item.deposit_amount.toFixed(2)}</div>
                    </div>
                    <div style="display:flex; gap:6px;">
                        <button class="btn btn-secondary btn-sm" onclick="saveListingBookmark(${item.listing_id})" title="Save Listing">
                            <i class="fa-solid fa-bookmark"></i>
                        </button>
                        <button class="btn btn-primary btn-sm" onclick="openBookingModal(${item.listing_id}, '${escapeHtml(item.title)}', ${item.rental_rate_per_day}, ${item.deposit_amount})">
                            <i class="fa-solid fa-calendar-check"></i> Request
                        </button>
                    </div>
                </div>
            </div>
        `;
        grid.appendChild(card);
    });
}

function escapeHtml(text) {
    return text.replace(/'/g, "\\'").replace(/"/g, "&quot;");
}

// --- NEW LISTING PRODUCT IMAGE UPLOADER & PREVIEW ---

function previewListingImage(e) {
    const file = e.target.files[0];
    if (!file) return;
    
    const reader = new FileReader();
    reader.onload = async function(evt) {
        const base64Data = evt.target.result;
        document.getElementById('newItemImgPreview').src = base64Data;
        
        showToast('Uploading product image...', 'info');
        try {
            const res = await fetch('/api/upload-image', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ image_data: base64Data })
            });
            const data = await res.json();
            if (data.success) {
                uploadedListingImageUrl = data.image_url;
                document.getElementById('newItemImageUrl').value = data.image_url;
                showToast('Product image uploaded!', 'success');
            }
        } catch (err) {
            showToast('Error uploading image', 'error');
        }
    };
    reader.readAsDataURL(file);
}

function updateListingImageUrl(url) {
    if (url) {
        uploadedListingImageUrl = url;
        document.getElementById('newItemImgPreview').src = url.startsWith('/') || url.startsWith('http') || url.startsWith('assets') ? url : `/${url}`;
    }
}

// --- BOOKING MODAL & WORKFLOW ---

let currentModalDailyRate = 0.0;
let currentModalDeposit = 0.0;

function openBookingModal(listingId, title, rate, deposit = 0.0) {
    document.getElementById('modalListingId').value = listingId;
    document.getElementById('modalListingTitle').innerText = `Request Rental: ${title}`;
    
    currentModalDailyRate = parseFloat(rate) || 0.0;
    currentModalDeposit = parseFloat(deposit) || 0.0;
    
    document.getElementById('modalRateMeta').innerText = `Daily Rate: GH₵ ${currentModalDailyRate.toFixed(2)} / day | Deposit: GH₵ ${currentModalDeposit.toFixed(2)}`;
    
    const today = new Date();
    const future = new Date();
    future.setDate(today.getDate() + 2); // Default 3 days rental
    
    document.getElementById('bookStartDate').value = today.toISOString().split('T')[0];
    document.getElementById('bookEndDate').value = future.toISOString().split('T')[0];
    
    calculateBookingTotal();
    document.getElementById('bookingModal').classList.add('active');
}

function calculateBookingTotal() {
    const startVal = document.getElementById('bookStartDate').value;
    const endVal = document.getElementById('bookEndDate').value;
    
    if (!startVal || !endVal) return;
    
    const d1 = new Date(startVal);
    const d2 = new Date(endVal);
    
    const diffTime = d2.getTime() - d1.getTime();
    let numDays = Math.ceil(diffTime / (1000 * 3600 * 24)) + 1;
    
    if (isNaN(numDays) || numDays < 1) {
        numDays = 1;
    }
    
    const subtotal = numDays * currentModalDailyRate;
    const grandTotal = subtotal + currentModalDeposit;
    
    const durationElem = document.getElementById('calcDurationText');
    const rateElem = document.getElementById('calcDailyRateText');
    const subtotalElem = document.getElementById('calcSubtotalText');
    const depositElem = document.getElementById('calcDepositText');
    const grandElem = document.getElementById('calcGrandTotalText');
    
    if (durationElem) durationElem.innerText = `${numDays} Day${numDays > 1 ? 's' : ''}`;
    if (rateElem) rateElem.innerText = `GH₵ ${currentModalDailyRate.toFixed(2)} / day`;
    if (subtotalElem) subtotalElem.innerText = `GH₵ ${subtotal.toFixed(2)} (${numDays} days × GH₵ ${currentModalDailyRate.toFixed(2)})`;
    if (depositElem) depositElem.innerText = `GH₵ ${currentModalDeposit.toFixed(2)}`;
    if (grandElem) grandElem.innerText = `GH₵ ${grandTotal.toFixed(2)}`;
}

function closeBookingModal() {
    document.getElementById('bookingModal').classList.remove('active');
}

async function submitBooking(e) {
    e.preventDefault();
    if (!currentUser) {
        showToast('Please sign in to request rentals', 'error');
        return;
    }
    
    const payload = {
        listing_id: document.getElementById('modalListingId').value,
        borrower_id: currentUser.user_id,
        rent_start_date: document.getElementById('bookStartDate').value,
        rent_end_date: document.getElementById('bookEndDate').value,
        rental_purpose: document.getElementById('bookPurpose').value,
        notes: document.getElementById('bookNotes').value
    };
    
    try {
        const res = await fetch('/api/rentals/request', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const data = await res.json();
        
        if (data.success) {
            showToast('Rental request submitted successfully!', 'success');
            closeBookingModal();
            switchTab('my-rentals');
        } else {
            showToast(data.message || 'Failed to submit request', 'error');
        }
    } catch (err) {
        showToast('Error submitting booking request', 'error');
    }
}

// --- USER RENTALS, APPROVAL, AND RETURNS ---

async function loadUserRentals() {
    if (!currentUser) return;
    
    try {
        const res = await fetch(`/api/rentals/my-requests/${currentUser.user_id}`);
        const data = await res.json();
        
        const incomingBox = document.getElementById('incomingRequestsList');
        const outgoingBox = document.getElementById('outgoingRequestsList');
        const activeLentBox = document.getElementById('activeLentList');
        
        incomingBox.innerHTML = '';
        outgoingBox.innerHTML = '';
        activeLentBox.innerHTML = '';
        
        // Render Incoming Requests
        if (!data.incoming || data.incoming.length === 0) {
            incomingBox.innerHTML = '<p class="text-subtle">No incoming rental requests for your listings.</p>';
        } else {
            data.incoming.forEach(req => {
                const item = document.createElement('div');
                item.className = 'card mb-2';
                item.style.padding = '10px 14px';
                item.style.marginBottom = '10px';
                item.style.background = 'rgba(255,255,255,0.02)';
                item.innerHTML = `
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <div>
                            <strong>${req.listing_title}</strong>
                            <div style="font-size:0.8rem; color:var(--text-muted);">
                                Borrower: ${req.borrower_name} | Purpose: ${req.rental_purpose} (${req.rent_start_date} to ${req.rent_end_date})
                            </div>
                        </div>
                        <button class="btn btn-primary btn-sm" onclick="approveRequest(${req.request_id})">
                            <i class="fa-solid fa-check"></i> Approve & Lock
                        </button>
                    </div>
                `;
                incomingBox.appendChild(item);
            });
        }
        
        // Render Outgoing Requests
        if (!data.outgoing || data.outgoing.length === 0) {
            outgoingBox.innerHTML = '<p class="text-subtle">No booking requests submitted yet.</p>';
        } else {
            data.outgoing.forEach(req => {
                const item = document.createElement('div');
                item.className = 'card mb-2';
                item.style.padding = '10px 14px';
                item.style.marginBottom = '10px';
                item.style.background = 'rgba(255,255,255,0.02)';
                
                const badge = req.status === 'Approved' ? '<span class="badge badge-emerald">Approved</span>' : '<span class="badge badge-amber">Pending</span>';
                
                item.innerHTML = `
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <div>
                            <strong>${req.listing_title}</strong>
                            <div style="font-size:0.8rem; color:var(--text-muted);">
                                Owner: ${req.owner_name} | Dates: ${req.rent_start_date} to ${req.rent_end_date}
                            </div>
                        </div>
                        ${badge}
                    </div>
                `;
                outgoingBox.appendChild(item);
            });
        }
        
        // Render Active Rented Out Items
        if (!data.active_lent || data.active_lent.length === 0) {
            activeLentBox.innerHTML = '<p class="text-subtle">No items currently rented out.</p>';
        } else {
            data.active_lent.forEach(t => {
                const item = document.createElement('div');
                item.className = 'card mb-2';
                item.style.padding = '10px 14px';
                item.style.marginBottom = '10px';
                item.style.background = 'rgba(255,255,255,0.02)';
                
                item.innerHTML = `
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <div>
                            <strong>${t.listing_title}</strong>
                            <div style="font-size:0.8rem; color:var(--text-muted);">
                                Borrower: ${t.borrower_name} | Rental Status: ${t.rental_status} (Gross: GH₵ ${t.gross_amount.toFixed(2)})
                            </div>
                        </div>
                        <button class="btn btn-secondary btn-sm" onclick="openReturnModal(${t.transaction_id})">
                            <i class="fa-solid fa-rotate-left"></i> Process Return
                        </button>
                    </div>
                `;
                activeLentBox.appendChild(item);
            });
        }
    } catch (e) {
        console.error('Failed to load user rentals', e);
    }
}

async function approveRequest(requestId) {
    try {
        const res = await fetch('/api/rentals/approve', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ request_id: requestId })
        });
        const data = await res.json();
        if (data.success) {
            showToast('Request Approved! 10% platform commission locked.', 'success');
            loadUserRentals();
        } else {
            showToast(data.message || 'Failed to approve request', 'error');
        }
    } catch (err) {
        showToast('Error approving request', 'error');
    }
}

function openReturnModal(txId) {
    document.getElementById('returnTxId').value = txId;
    document.getElementById('returnModal').classList.add('active');
}

function closeReturnModal() {
    document.getElementById('returnModal').classList.remove('active');
}

function toggleDamageFields(val) {
    const fields = document.getElementById('damageFields');
    if (val === 'Damage') {
        fields.classList.remove('hidden');
    } else {
        fields.classList.add('hidden');
    }
}

async function submitReturnProcess(e) {
    e.preventDefault();
    const txId = document.getElementById('returnTxId').value;
    const isDamage = document.getElementById('returnCondition').value === 'Damage';
    
    const payload = {
        transaction_id: txId,
        has_damage: isDamage,
        issue_description: document.getElementById('returnIssue').value,
        repair_cost: document.getElementById('returnCost').value || 0.0,
        return_notes: document.getElementById('returnNotes').value
    };
    
    try {
        const res = await fetch('/api/rentals/return', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const data = await res.json();
        if (data.success) {
            showToast('Item return processed cleanly!', 'success');
            closeReturnModal();
            loadUserRentals();
        } else {
            showToast('Error processing return', 'error');
        }
    } catch (err) {
        showToast('Return server error', 'error');
    }
}

// --- SAVED LISTINGS & WISHLIST ALERTS ---

async function loadSavedAndWishlist() {
    if (!currentUser) return;
    
    try {
        // Saved listings
        const res1 = await fetch(`/api/saved-listings?user_id=${currentUser.user_id}`);
        const saved = await res1.json();
        const savedBox = document.getElementById('savedListingsContainer');
        savedBox.innerHTML = '';
        
        if (!saved || saved.length === 0) {
            savedBox.innerHTML = '<p class="text-subtle">No bookmarked items saved.</p>';
        } else {
            saved.forEach(s => {
                const d = document.createElement('div');
                d.style.padding = '8px 12px';
                d.style.borderBottom = '1px solid var(--border-color)';
                d.innerHTML = `<strong>${s.title}</strong> — GH₵ ${s.rental_rate_per_day.toFixed(2)}/day (${s.owner_name})`;
                savedBox.appendChild(d);
            });
        }
        
        // Wishlist
        const res2 = await fetch(`/api/wishlist?user_id=${currentUser.user_id}`);
        const wishlist = await res2.json();
        const wishBox = document.getElementById('wishlistContainer');
        wishBox.innerHTML = '';
        
        if (!wishlist || wishlist.length === 0) {
            wishBox.innerHTML = '<p class="text-subtle">No active keyword wishlist alerts.</p>';
        } else {
            wishlist.forEach(w => {
                const d = document.createElement('div');
                d.style.padding = '6px 10px';
                d.innerHTML = `<span class="badge badge-emerald"><i class="fa-solid fa-bell"></i> Alert: ${w.keyword || w.category_name}</span>`;
                wishBox.appendChild(d);
            });
        }
    } catch (e) {
        console.error('Failed to load saved/wishlist', e);
    }
}

async function saveListingBookmark(listingId) {
    if (!currentUser) return;
    try {
        await fetch('/api/saved-listings', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id: currentUser.user_id, listing_id: listingId })
        });
        showToast('Item saved to your bookmarks!', 'success');
    } catch (e) {
        showToast('Could not save listing', 'error');
    }
}

async function handleAddWishlist(e) {
    e.preventDefault();
    if (!currentUser) return;
    const kw = document.getElementById('wishlistKeyword').value;
    if (!kw) return;
    
    try {
        await fetch('/api/wishlist', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id: currentUser.user_id, keyword: kw })
        });
        showToast(`Wishlist alert added for '${kw}'`, 'success');
        document.getElementById('wishlistKeyword').value = '';
        loadSavedAndWishlist();
    } catch (e) {
        showToast('Could not add wishlist alert', 'error');
    }
}

// --- NEW LISTING MODAL ---

function openNewListingModal() {
    uploadedListingImageUrl = 'assets/logo.jpg';
    if (document.getElementById('newItemImgPreview')) {
        document.getElementById('newItemImgPreview').src = '/assets/logo.jpg';
    }
    if (document.getElementById('newItemImageUrl')) {
        document.getElementById('newItemImageUrl').value = '';
    }
    document.getElementById('newListingModal').classList.add('active');
}

function closeNewListingModal() {
    document.getElementById('newListingModal').classList.remove('active');
}

async function submitNewListing(e) {
    e.preventDefault();
    if (!currentUser) {
        showToast('Please sign in first', 'error');
        return;
    }
    
    const today = new Date().toISOString().split('T')[0];
    const future = new Date(Date.now() + 90*24*60*60*1000).toISOString().split('T')[0];
    
    const payload = {
        owner_id: currentUser.user_id,
        category_id: document.getElementById('newCategory').value,
        title: document.getElementById('newTitle').value,
        subcategory: document.getElementById('newSubcategory').value,
        brand: document.getElementById('newBrand').value,
        model: document.getElementById('newModel').value,
        rental_rate_per_day: document.getElementById('newRate').value,
        deposit_amount: document.getElementById('newDeposit').value,
        condition: document.getElementById('newCondition').value,
        pickup_location: document.getElementById('newLocation').value,
        description: document.getElementById('newDescription').value,
        available_from: today,
        available_until: future,
        thumbnail_path: uploadedListingImageUrl || 'assets/logo.jpg'
    };
    
    try {
        const res = await fetch('/api/listings', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const data = await res.json();
        
        if (data.success) {
            showToast('Equipment published for rent with image!', 'success');
            closeNewListingModal();
            loadListings();
        } else {
            showToast(data.message || 'Failed to publish listing', 'error');
        }
    } catch (err) {
        showToast('Error publishing listing', 'error');
    }
}

// --- 15 CAMPUS INTELLIGENCE REPORTS ---

const REPORT_TITLES = [
    "01. Platform Revenue & Commission Summary",
    "02. Top 10 Lenders by Total Earnings",
    "03. Most Active Borrowers",
    "04. Category Revenue Performance",
    "05. Currently Active Rentals Overview",
    "06. Maintenance & Repair Expenses",
    "07. High Risk Overdue Rentals",
    "08. Unborrowed Idle Listings",
    "09. Rental Purpose Distribution",
    "10. Average Rental Rates by Category",
    "11. User Trust Score Rankings",
    "12. Hostel Equipment Density Report",
    "13. Monthly Rental Trends",
    "14. Lender vs Borrower Ratings Comparison",
    "15. Delisted Equipment Audit Log"
];

function loadReportMenu() {
    const menu = document.getElementById('reportMenu');
    if (!menu) return;
    menu.innerHTML = '';
    
    REPORT_TITLES.forEach((title, idx) => {
        const id = idx + 1;
        const btn = document.createElement('button');
        btn.className = `report-item-btn ${id === 1 ? 'active' : ''}`;
        btn.innerText = title;
        btn.onclick = () => {
            document.querySelectorAll('.report-item-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            fetchReport(id);
        };
        menu.appendChild(btn);
    });
}

async function fetchReport(reportId) {
    currentReportId = reportId;
    try {
        const res = await fetch(`/api/reports/${reportId}`);
        const data = await res.json();
        
        document.getElementById('currentReportTitle').innerText = `Report ${reportId < 10 ? '0'+reportId : reportId}: ${data.title}`;
        
        const thead = document.getElementById('reportTableHead');
        const tbody = document.getElementById('reportTableBody');
        
        thead.innerHTML = '';
        tbody.innerHTML = '';
        
        // Render Headers
        const headerRow = document.createElement('tr');
        data.headers.forEach(h => {
            const th = document.createElement('th');
            th.innerText = h;
            headerRow.appendChild(th);
        });
        thead.appendChild(headerRow);
        
        // Render Rows
        if (!data.data || data.data.length === 0) {
            tbody.innerHTML = `<tr><td colspan="${data.headers.length}" style="text-align:center; color:var(--text-subtle); padding:2rem;">No data returned for this report query.</td></tr>`;
            return;
        }
        
        data.data.forEach(row => {
            const tr = document.createElement('tr');
            row.forEach(cell => {
                const td = document.createElement('td');
                td.innerText = cell;
                tr.appendChild(td);
            });
            tbody.appendChild(tr);
        });
    } catch (e) {
        console.error('Failed to fetch report', e);
    }
}

function exportCurrentReportCsv() {
    window.location.href = `/api/reports/${currentReportId}/export`;
}

// --- TRUST SCORE & REVIEWS ---

async function loadTrustScore() {
    if (!currentUser) return;
    try {
        const res = await fetch(`/api/trust-score/${currentUser.user_id}`);
        const trust = await res.json();
        
        document.getElementById('trustScoreValue').innerText = trust.score;
        document.getElementById('trustRatingMeta').innerText = `Avg Rating: ${trust.avg_rating} / 5.0 | Total Rentals: ${trust.total_rentals}`;
    } catch (e) {
        console.error('Failed to load trust score', e);
    }
}

async function submitReview(e) {
    e.preventDefault();
    if (!currentUser) return;
    
    const payload = {
        transaction_id: document.getElementById('reviewTxId').value,
        reviewer_id: currentUser.user_id,
        reviewee_id: 2,
        reviewee_type: document.getElementById('revieweeType').value,
        rating: document.getElementById('reviewRating').value,
        comment: document.getElementById('reviewComment').value
    };
    
    try {
        const res = await fetch('/api/reviews', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const data = await res.json();
        if (data.success) {
            showToast('Review submitted successfully!', 'success');
            loadTrustScore();
        } else {
            showToast(data.message || 'Error submitting review', 'error');
        }
    } catch (err) {
        showToast('Error submitting review', 'error');
    }
}

// --- TOAST UTILITY ---

function showToast(message, type = 'info') {
    const container = document.getElementById('toastContainer');
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.innerText = message;
    
    container.appendChild(toast);
    setTimeout(() => {
        toast.remove();
    }, 4000);
}
