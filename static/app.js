/* ==========================================================================
   CampusLink — Peer-to-Peer Student Equipment Marketplace JavaScript Logic
   University of Mines and Technology (UMaT), Tarkwa, Ghana
   ========================================================================== */

// --- GLOBAL APPLICATION STATE ---
let currentUser = null;
let currentTab = 'marketplace';
let currentReportId = 1;
let allCategories = [];
let allListings = [];
let selectedListingForRental = null;
let selectedTxForReturn = null;
let demoAccounts = [];

// --- INITIALIZATION ---
document.addEventListener('DOMContentLoaded', () => {
    initClock();
    loadDemoAccounts();
    loadCategories();

    // Check if user session already exists in localStorage
    const savedUser = localStorage.getItem('campuslink_user');
    if (savedUser) {
        try {
            currentUser = JSON.parse(savedUser);
            showMainApp();
        } catch (e) {
            localStorage.removeItem('campuslink_user');
        }
    }
});

// --- LIVE CLOCK ---
function initClock() {
    const clockEl = document.getElementById('liveClockDisplay');
    if (!clockEl) return;

    function update() {
        const now = new Date();
        clockEl.textContent = now.toLocaleTimeString('en-US', { hour12: false });
    }
    update();
    setInterval(update, 1000);
}

// --- AUTHENTICATION & DEMO ACCOUNTS ---
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

async function loadDemoAccounts() {
    try {
        const res = await fetch('/api/demo-accounts');
        demoAccounts = await res.json();

        // Populate preset chips on login page
        const presetsContainer = document.getElementById('demoPresetsContainer');
        const ddListContainer = document.getElementById('dropdownDemoAccountsList');
        
        if (presetsContainer) presetsContainer.innerHTML = '';
        if (ddListContainer) ddListContainer.innerHTML = '';

        demoAccounts.forEach(acct => {
            // Login page chips
            if (presetsContainer) {
                const btn = document.createElement('button');
                btn.className = 'demo-preset-chip';
                btn.innerHTML = `<i class="fa-solid fa-user"></i> ${acct.name.split(' ')[0]} (${acct.role.includes('Staff') ? 'Staff' : acct.role.includes('Admin') ? 'Admin' : 'Student'})`;
                btn.onclick = () => {
                    document.getElementById('loginEmail').value = acct.email;
                    document.getElementById('loginPassword').value = acct.password;
                    handleLogin(acct.email, acct.password);
                };
                presetsContainer.appendChild(btn);
            }

            // Header dropdown switch list
            if (ddListContainer) {
                const item = document.createElement('button');
                item.className = 'dropdown-item';
                item.innerHTML = `<i class="fa-solid fa-user-gear"></i> ${acct.name} (${acct.role.split(' ')[0]})`;
                item.onclick = () => switchUserAccount(acct.email, acct.password);
                ddListContainer.appendChild(item);
            }
        });
    } catch (e) {
        console.error("Failed to load demo accounts", e);
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
    const email = document.getElementById('loginEmail').value.trim();
    const password = document.getElementById('loginPassword').value.trim();
    await handleLogin(email, password);
}

async function handleLogin(email, password) {
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
            showMainApp();
        } else {
            showToast(data.message || 'Invalid credentials', 'error');
        }
    } catch (e) {
        showToast('Login connection error', 'error');
    }
}

async function handleRegisterSubmit(e) {
    e.preventDefault();
    const name = document.getElementById('regName').value.trim();
    const email = document.getElementById('regEmail').value.trim();
    const student_id = document.getElementById('regStudentId').value.trim();
    const phone = document.getElementById('regPhone').value.trim();
    const department = document.getElementById('regDepartment').value;
    const hostel = document.getElementById('regHostel').value.trim();
    const password = document.getElementById('regPassword').value;
    const confirm = document.getElementById('regConfirm').value;

    if (password !== confirm) {
        showToast('Passwords do not match', 'error');
        return;
    }

    try {
        const res = await fetch('/api/auth/register', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, email, password, student_id, phone, department, hostel })
        });
        const data = await res.json();

        if (data.success) {
            currentUser = data.user;
            localStorage.setItem('campuslink_user', JSON.stringify(currentUser));
            showToast('Account created successfully!', 'success');
            showMainApp();
        } else {
            showToast(data.message || 'Registration failed', 'error');
        }
    } catch (e) {
        showToast('Registration network error', 'error');
    }
}

async function switchUserAccount(email, password) {
    closeUserDropdown();
    await handleLogin(email, password);
}

function handleLogout() {
    currentUser = null;
    localStorage.removeItem('campuslink_user');
    document.getElementById('mainAppScreen').classList.add('hidden');
    document.getElementById('authScreen').classList.remove('hidden');
    showToast('Signed out successfully', 'info');
}

// --- MAIN APP DISPLAY & HEADER USER METADATA ---
function showMainApp() {
    document.getElementById('authScreen').classList.add('hidden');
    document.getElementById('mainAppScreen').classList.remove('hidden');

    // Update Header Metadata
    const initials = currentUser.name.split(' ').map(n => n[0]).join('').substring(0, 2);
    document.getElementById('userAvatar').textContent = initials;
    document.getElementById('headerUserName').textContent = currentUser.name;
    document.getElementById('headerUserRole').textContent = currentUser.verification_level;

    // Dropdown details
    document.getElementById('ddUserName').textContent = currentUser.name;
    document.getElementById('ddUserEmail').textContent = currentUser.email;
    document.getElementById('ddUserId').textContent = `ID: ${currentUser.student_id || 'N/A'}`;

    // Load initial tab data
    switchTab('marketplace');
}

function toggleUserDropdown(e) {
    e.stopPropagation();
    const menu = document.getElementById('userDropdownMenu');
    menu.classList.toggle('hidden');
}

function closeUserDropdown() {
    const menu = document.getElementById('userDropdownMenu');
    if (menu) menu.classList.add('hidden');
}

document.addEventListener('click', closeUserDropdown);

// --- TAB NAVIGATION ---
function switchTab(tabId) {
    currentTab = tabId;

    // Toggle Nav Button Highlight
    const navBtns = {
        'marketplace': 'navBtnMarketplace',
        'my-rentals': 'navBtnMyRentals',
        'list-new': 'navBtnListNew',
        'trust-profile': 'navBtnTrustProfile',
        'reports': 'navBtnReports'
    };

    Object.keys(navBtns).forEach(key => {
        const btn = document.getElementById(navBtns[key]);
        const pane = document.getElementById(`tab${key.split('-').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join('')}`);
        
        if (key === tabId) {
            if (btn) btn.classList.add('active');
            if (pane) pane.classList.remove('hidden');
        } else {
            if (btn) btn.classList.remove('active');
            if (pane) pane.classList.add('hidden');
        }
    });

    // Execute Tab Loaders
    if (tabId === 'marketplace') {
        loadMarketplaceListings();
    } else if (tabId === 'my-rentals') {
        loadMyRentalsData();
    } else if (tabId === 'list-new') {
        populatePostCategoryDropdown();
        initPostFormDates();
    } else if (tabId === 'trust-profile') {
        loadTrustScoreAndProfile();
    } else if (tabId === 'reports') {
        loadReportsList();
        loadReportData(currentReportId);
    }
}

// --- TAB 1: EQUIPMENT MARKETPLACE ---
async function loadCategories() {
    try {
        const res = await fetch('/api/categories');
        allCategories = await res.json();

        const catSelect = document.getElementById('marketCategoryFilter');
        const pillsContainer = document.getElementById('categoryPillsContainer');

        if (catSelect) {
            catSelect.innerHTML = '<option value="all">All Equipment Categories</option>';
            allCategories.forEach(c => {
                catSelect.innerHTML += `<option value="${c.category_id}">${c.name}</option>`;
            });
        }

        if (pillsContainer) {
            pillsContainer.innerHTML = `<button class="cat-pill active" onclick="filterByCategory('all', this)"><i class="fa-solid fa-grid-2"></i> All Equipment</button>`;
            allCategories.forEach(c => {
                pillsContainer.innerHTML += `<button class="cat-pill" onclick="filterByCategory(${c.category_id}, this)">${c.name}</button>`;
            });
        }
    } catch (e) {
        console.error("Failed to fetch categories", e);
    }
}

function filterByCategory(catId, btnEl) {
    document.querySelectorAll('.cat-pill').forEach(el => el.classList.remove('active'));
    if (btnEl) btnEl.classList.add('active');

    const catSelect = document.getElementById('marketCategoryFilter');
    if (catSelect) catSelect.value = catId;

    loadMarketplaceListings();
}

function handleMarketSearch() {
    loadMarketplaceListings();
}

async function loadMarketplaceListings() {
    const search = document.getElementById('marketSearchInput')?.value || '';
    const catId = document.getElementById('marketCategoryFilter')?.value || 'all';
    const condFilter = document.getElementById('marketConditionFilter')?.value || 'all';

    try {
        const res = await fetch(`/api/listings?category_id=${catId}&search=${encodeURIComponent(search)}`);
        allListings = await res.json();

        let filtered = allListings;
        if (condFilter !== 'all') {
            filtered = filtered.filter(l => l.condition === condFilter);
        }

        renderListingsGrid(filtered);
    } catch (e) {
        console.error("Failed to load listings", e);
    }
}

function renderListingsGrid(listings) {
    const grid = document.getElementById('listingsGrid');
    if (!grid) return;

    if (!listings || listings.length === 0) {
        grid.innerHTML = `
            <div class="glass-card" style="grid-column: 1 / -1; padding: 40px; text-align: center; color: var(--text-muted);">
                <i class="fa-solid fa-folder-open" style="font-size: 48px; margin-bottom: 12px;"></i>
                <h3>No Equipment Listings Found</h3>
                <p>Try adjusting your search criteria or category filter.</p>
            </div>
        `;
        return;
    }

    grid.innerHTML = '';
    listings.forEach(item => {
        const isOwner = currentUser && item.owner_id === currentUser.user_id;
        const thumb = item.thumbnail_path && item.thumbnail_path.length > 5 ? item.thumbnail_path : '/assets/logo.jpg';

        const card = document.createElement('div');
        card.className = 'item-card';
        card.innerHTML = `
            <div class="item-card-image">
                <img src="/${thumb}" alt="${item.title}" onerror="this.src='/assets/logo.jpg'">
                <span class="item-badge-avail ${item.status}">${item.status}</span>
                <button class="btn-bookmark-card" title="Bookmark Item" onclick="bookmarkItem(${item.listing_id}, event)">
                    <i class="fa-regular fa-star"></i>
                </button>
            </div>
            <div class="item-card-body">
                <div class="item-category-tag"><i class="fa-solid fa-tag"></i> ${item.category_name || item.subcategory}</div>
                <h3 class="item-title">${item.title}</h3>
                <div class="item-brand-model">${item.brand} ${item.model} • <span class="badge-tag info">${item.condition}</span></div>
                
                <div class="item-price-box">
                    <div>
                        <span class="rate-val">GH₵ ${item.rental_rate_per_day.toFixed(2)}</span>
                        <span class="rate-unit">/ day</span>
                    </div>
                    <div class="deposit-val">
                        Deposit: <strong>GH₵ ${item.deposit_amount.toFixed(2)}</strong>
                    </div>
                </div>

                <div class="item-owner-info">
                    <i class="fa-solid fa-user-circle"></i>
                    <span>Owned by <strong>${item.owner_name}</strong> (${item.pickup_location})</span>
                </div>

                <div class="item-card-footer">
                    ${isOwner ? `
                        <button class="btn btn-block" style="background: rgba(30,41,59,0.8); color: var(--text-muted);" disabled>
                            <i class="fa-solid fa-user-check"></i> Your Equipment
                        </button>
                    ` : item.status === 'Available' ? `
                        <button class="btn btn-emerald btn-block" onclick="openRentalModal(${item.listing_id})">
                            <i class="fa-solid fa-paper-plane"></i> Request Rental
                        </button>
                    ` : `
                        <button class="btn btn-block" style="background: rgba(30,41,59,0.8); color: var(--text-muted);" disabled>
                            <i class="fa-solid fa-lock"></i> Currently ${item.status}
                        </button>
                    `}
                </div>
            </div>
        `;
        grid.appendChild(card);
    });
}

async function bookmarkItem(listingId, e) {
    if (e) e.stopPropagation();
    if (!currentUser) return;

    try {
        await fetch('/api/saved-listings', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id: currentUser.user_id, listing_id: listingId })
        });
        showToast('Item saved to your bookmarks!', 'success');
    } catch (err) {
        showToast('Could not save bookmark', 'error');
    }
}

// --- RENTAL BOOKING MODAL ---
function openRentalModal(listingId) {
    const item = allListings.find(l => l.listing_id === listingId);
    if (!item) return;

    selectedListingForRental = item;

    document.getElementById('modalListingId').value = item.listing_id;
    document.getElementById('modalItemTitle').textContent = item.title;
    document.getElementById('modalItemOwner').textContent = `Owner: ${item.owner_name} (${item.pickup_location})`;
    document.getElementById('modalItemRate').textContent = `GH₵ ${item.rental_rate_per_day.toFixed(2)}`;
    document.getElementById('modalItemDeposit').textContent = `GH₵ ${item.deposit_amount.toFixed(2)}`;
    document.getElementById('modalItemImg').src = `/${item.thumbnail_path || 'assets/logo.jpg'}`;

    // Default dates (Tomorrow to 3 days later)
    const today = new Date();
    const tomorrow = new Date(today);
    tomorrow.setDate(tomorrow.getDate() + 1);
    const end = new Date(tomorrow);
    end.setDate(end.getDate() + 2);

    document.getElementById('modalStartDate').value = tomorrow.toISOString().split('T')[0];
    document.getElementById('modalEndDate').value = end.toISOString().split('T')[0];

    calculateRentalCostSummary();
    document.getElementById('rentalModal').classList.remove('hidden');
}

function calculateRentalCostSummary() {
    if (!selectedListingForRental) return;

    const startStr = document.getElementById('modalStartDate').value;
    const endStr = document.getElementById('modalEndDate').value;

    if (!startStr || !endStr) return;

    const start = new Date(startStr);
    const end = new Date(endStr);
    let diffDays = Math.ceil((end - start) / (1000 * 60 * 60 * 24));
    if (diffDays <= 0) diffDays = 1;

    const rate = selectedListingForRental.rental_rate_per_day;
    const deposit = selectedListingForRental.deposit_amount;
    const gross = rate * diffDays;
    const total = gross + deposit;

    document.getElementById('summaryDuration').textContent = `${diffDays} Day(s)`;
    document.getElementById('summaryGross').textContent = `GH₵ ${gross.toFixed(2)}`;
    document.getElementById('summaryDeposit').textContent = `GH₵ ${deposit.toFixed(2)}`;
    document.getElementById('summaryTotal').textContent = `GH₵ ${total.toFixed(2)}`;
}

function closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) modal.classList.add('hidden');
}

async function handleRentalFormSubmit(e) {
    e.preventDefault();
    if (!currentUser || !selectedListingForRental) return;

    const listing_id = parseInt(document.getElementById('modalListingId').value);
    const rent_start_date = document.getElementById('modalStartDate').value;
    const rent_end_date = document.getElementById('modalEndDate').value;
    const rental_purpose = document.getElementById('modalPurpose').value;
    const notes = document.getElementById('modalNotes').value.trim();

    try {
        const res = await fetch('/api/rentals/request', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                listing_id,
                borrower_id: currentUser.user_id,
                rent_start_date,
                rent_end_date,
                rental_purpose,
                notes
            })
        });
        const data = await res.json();

        if (data.success) {
            showToast('Rental request submitted to owner successfully!', 'success');
            closeModal('rentalModal');
            switchTab('my-rentals');
        } else {
            showToast(data.message || 'Could not submit request', 'error');
        }
    } catch (err) {
        showToast('Request network error', 'error');
    }
}

// --- TAB 2: MY RENTALS & REQUESTS ---
async function loadMyRentalsData() {
    if (!currentUser) return;

    try {
        const res = await fetch(`/api/rentals/my-requests/${currentUser.user_id}`);
        const data = await res.json();

        // 1. Incoming Requests
        const incomingContainer = document.getElementById('incomingRequestsContainer');
        const incomingCountTag = document.getElementById('incomingCountTag');
        const navBadge = document.getElementById('incomingReqBadge');

        const pendingIncoming = (data.incoming || []).filter(r => r.status === 'Pending');
        if (incomingCountTag) incomingCountTag.textContent = `${pendingIncoming.length} Pending`;
        
        if (navBadge) {
            if (pendingIncoming.length > 0) {
                navBadge.textContent = pendingIncoming.length;
                navBadge.classList.remove('hidden');
            } else {
                navBadge.classList.add('hidden');
            }
        }

        if (incomingContainer) {
            if (!data.incoming || data.incoming.length === 0) {
                incomingContainer.innerHTML = '<div style="color: var(--text-muted); font-size: 13px;">No incoming rental requests yet.</div>';
            } else {
                incomingContainer.innerHTML = '';
                data.incoming.forEach(req => {
                    const card = document.createElement('div');
                    card.className = 'request-card';
                    card.innerHTML = `
                        <div class="request-info">
                            <div class="request-title"><i class="fa-solid fa-box"></i> ${req.listing_title}</div>
                            <div class="request-meta">Borrower: <strong>${req.borrower_name}</strong> (${req.rent_start_date} to ${req.rent_end_date})</div>
                            <div class="request-purpose">Purpose: ${req.rental_purpose}</div>
                        </div>
                        <div class="request-actions">
                            <span class="badge-tag ${req.status === 'Pending' ? 'warning' : req.status === 'Approved' ? 'success' : 'danger'}">${req.status}</span>
                            ${req.status === 'Pending' ? `
                                <button class="btn btn-emerald btn-sm" onclick="approveRentalRequest(${req.request_id})">
                                    <i class="fa-solid fa-check"></i> Approve Request
                                </button>
                            ` : ''}
                        </div>
                    `;
                    incomingContainer.appendChild(card);
                });
            }
        }

        // 2. Outgoing Requests
        const outgoingContainer = document.getElementById('outgoingRequestsContainer');
        const outgoingCountTag = document.getElementById('outgoingCountTag');
        if (outgoingCountTag) outgoingCountTag.textContent = `${(data.outgoing || []).length} Submitted`;

        if (outgoingContainer) {
            if (!data.outgoing || data.outgoing.length === 0) {
                outgoingContainer.innerHTML = '<div style="color: var(--text-muted); font-size: 13px;">You have not submitted any rental requests yet.</div>';
            } else {
                outgoingContainer.innerHTML = '';
                data.outgoing.forEach(req => {
                    const card = document.createElement('div');
                    card.className = 'request-card';
                    card.innerHTML = `
                        <div class="request-info">
                            <div class="request-title"><i class="fa-solid fa-paper-plane"></i> ${req.listing_title}</div>
                            <div class="request-meta">Owner: <strong>${req.owner_name}</strong> (${req.rent_start_date} to ${req.rent_end_date})</div>
                            <div class="request-purpose">Purpose: ${req.rental_purpose}</div>
                        </div>
                        <div>
                            <span class="badge-tag ${req.status === 'Pending' ? 'warning' : req.status === 'Approved' ? 'success' : 'danger'}">${req.status}</span>
                        </div>
                    `;
                    outgoingContainer.appendChild(card);
                });
            }
        }

        // 3. Active Rented Items
        const activeContainer = document.getElementById('activeLentContainer');
        const activeCountTag = document.getElementById('activeTxCountTag');

        const activeTx = (data.active_lent || []).filter(t => t.rental_status === 'Active' || t.rental_status === 'Reserved');
        if (activeCountTag) activeCountTag.textContent = `${activeTx.length} Active`;

        if (activeContainer) {
            if (!data.active_lent || data.active_lent.length === 0) {
                activeContainer.innerHTML = '<div style="color: var(--text-muted); font-size: 13px;">No active rental exchanges in progress.</div>';
            } else {
                activeContainer.innerHTML = '';
                data.active_lent.forEach(tx => {
                    const card = document.createElement('div');
                    card.className = 'request-card';
                    card.innerHTML = `
                        <div class="request-info">
                            <div class="request-title"><i class="fa-solid fa-handshake"></i> ${tx.listing_title}</div>
                            <div class="request-meta">Renter: <strong>${tx.borrower_name}</strong> | Gross: <strong>GH₵ ${tx.gross_amount.toFixed(2)}</strong></div>
                            <div class="request-purpose">Dates: ${tx.rent_start_date} to ${tx.rent_end_date}</div>
                        </div>
                        <div class="request-actions">
                            <span class="badge-tag ${tx.rental_status === 'Active' || tx.rental_status === 'Reserved' ? 'success' : 'info'}">${tx.rental_status}</span>
                            ${tx.rental_status === 'Active' || tx.rental_status === 'Reserved' ? `
                                <button class="btn btn-primary btn-sm" onclick="openReturnModal(${tx.transaction_id})">
                                    <i class="fa-solid fa-arrow-rotate-left"></i> Process Return
                                </button>
                            ` : ''}
                        </div>
                    `;
                    activeContainer.appendChild(card);
                });
            }
        }

    } catch (e) {
        console.error("Failed to load my rentals", e);
    }
}

async function approveRentalRequest(requestId) {
    try {
        const res = await fetch('/api/rentals/approve', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ request_id: requestId })
        });
        const data = await res.json();

        if (data.success) {
            showToast('Rental request approved! 10% commission locked.', 'success');
            loadMyRentalsData();
        } else {
            showToast(data.message || 'Could not approve request', 'error');
        }
    } catch (e) {
        showToast('Approval network error', 'error');
    }
}

function openReturnModal(txId) {
    selectedTxForReturn = txId;
    document.getElementById('returnTxId').value = txId;
    document.getElementById('returnModal').classList.remove('hidden');
}

function toggleDamageCostField() {
    const val = document.getElementById('returnDamageCheck').value;
    const group = document.getElementById('damageCostGroup');
    if (val === 'true') {
        group.classList.remove('hidden');
    } else {
        group.classList.add('hidden');
    }
}

async function handleReturnSubmit(e) {
    e.preventDefault();
    const txId = parseInt(document.getElementById('returnTxId').value);
    const hasDamage = document.getElementById('returnDamageCheck').value === 'true';
    const repairCost = parseFloat(document.getElementById('returnRepairCost').value || 0);
    const returnNotes = document.getElementById('returnNotes').value.trim();

    try {
        const res = await fetch('/api/rentals/return', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                transaction_id: txId,
                has_damage: hasDamage,
                repair_cost: repairCost,
                return_notes: returnNotes
            })
        });
        const data = await res.json();

        if (data.success) {
            showToast('Return processed successfully! Equipment restored to Available.', 'success');
            closeModal('returnModal');
            loadMyRentalsData();
        } else {
            showToast(data.message || 'Failed to process return', 'error');
        }
    } catch (err) {
        showToast('Return network error', 'error');
    }
}

// --- TAB 3: POST NEW ITEM ---
function populatePostCategoryDropdown() {
    const select = document.getElementById('postCategory');
    if (!select || allCategories.length === 0) return;

    select.innerHTML = '';
    allCategories.forEach(c => {
        select.innerHTML += `<option value="${c.category_id}">${c.name}</option>`;
    });
}

function initPostFormDates() {
    const today = new Date();
    const startStr = today.toISOString().split('T')[0];
    const end = new Date(today);
    end.setDate(end.getDate() + 90);
    const endStr = end.toISOString().split('T')[0];

    document.getElementById('postStartDate').value = startStr;
    document.getElementById('postEndDate').value = endStr;
}

async function handleCreateListingSubmit(e) {
    e.preventDefault();
    if (!currentUser) return;

    const payload = {
        owner_id: currentUser.user_id,
        category_id: parseInt(document.getElementById('postCategory').value),
        title: document.getElementById('postTitle').value.trim(),
        description: document.getElementById('postDescription').value.trim(),
        subcategory: document.getElementById('postSubcategory').value.trim(),
        brand: document.getElementById('postBrand').value.trim(),
        model: document.getElementById('postModel').value.trim(),
        purchase_year: parseInt(document.getElementById('postYear').value),
        rental_rate_per_day: parseFloat(document.getElementById('postRate').value),
        deposit_amount: parseFloat(document.getElementById('postDeposit').value),
        condition: document.getElementById('postCondition').value,
        pickup_location: document.getElementById('postLocation').value.trim(),
        available_from: document.getElementById('postStartDate').value,
        available_until: document.getElementById('postEndDate').value,
        thumbnail_path: document.getElementById('postImageUrl').value.trim() || 'assets/logo.jpg'
    };

    try {
        const res = await fetch('/api/listings', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const data = await res.json();

        if (data.success) {
            showToast('New equipment listed successfully!', 'success');
            document.getElementById('createListingForm').reset();
            switchTab('marketplace');
        } else {
            showToast(data.message || 'Failed to publish listing', 'error');
        }
    } catch (err) {
        showToast('Creation network error', 'error');
    }
}

// --- TAB 4: TRUST SCORE & USER PROFILE ---
async function loadTrustScoreAndProfile() {
    if (!currentUser) return;

    // Profile Details
    document.getElementById('profName').textContent = currentUser.name;
    document.getElementById('profEmail').textContent = currentUser.email;
    document.getElementById('profStudentId').textContent = currentUser.student_id || 'N/A';
    document.getElementById('profDept').textContent = currentUser.department || 'Geomatic Engineering';
    document.getElementById('profHostel').textContent = currentUser.hostel || 'Chamber of Mines Hostel';
    document.getElementById('profVerification').textContent = currentUser.verification_level;

    // Fetch Trust Score
    try {
        const res = await fetch(`/api/trust-score/${currentUser.user_id}`);
        const trust = await res.json();

        const score = trust.score || 90;
        document.getElementById('trustScoreValue').textContent = score;
        document.getElementById('trustAvgRating').textContent = `${(trust.avg_rating || 5.0).toFixed(1)} ★`;
        document.getElementById('trustTotalRentals').textContent = trust.total_rentals || 0;
        document.getElementById('trustDamageClaims').textContent = trust.damage_claims || 0;

        // SVG Ring animation (stroke-dashoffset range 0 - 264)
        const offset = 264 - (score / 100) * 264;
        const fillRing = document.getElementById('trustGaugeFill');
        if (fillRing) fillRing.style.strokeDashoffset = offset;

        // Trust Tier Badge
        const tierBadge = document.getElementById('trustTierBadge');
        if (tierBadge) {
            if (score >= 90) tierBadge.innerHTML = '<i class="fa-solid fa-award"></i> Platinum Trust Tier';
            else if (score >= 75) tierBadge.innerHTML = '<i class="fa-solid fa-medal"></i> Gold Trust Tier';
            else tierBadge.innerHTML = '<i class="fa-solid fa-shield"></i> Standard Trust Tier';
        }
    } catch (e) {
        console.error("Failed to load trust score", e);
    }

    loadSavedListings();
}

async function loadSavedListings() {
    if (!currentUser) return;
    try {
        const res = await fetch(`/api/saved-listings?user_id=${currentUser.user_id}`);
        const items = await res.json();
        const container = document.getElementById('savedListingsContainer');

        if (container) {
            if (!items || items.length === 0) {
                container.innerHTML = '<div style="color: var(--text-muted); font-size: 13px;">No bookmarked items yet. Click the star icon on any marketplace item to save it.</div>';
            } else {
                container.innerHTML = '';
                items.forEach(item => {
                    container.innerHTML += `
                        <div class="request-card">
                            <div class="request-info">
                                <div class="request-title">${item.title}</div>
                                <div class="request-meta">Rate: <strong>GH₵ ${item.rental_rate_per_day.toFixed(2)}/day</strong> | Owner: ${item.owner_name}</div>
                            </div>
                            <button class="btn btn-emerald btn-sm" onclick="openRentalModal(${item.listing_id})">
                                <i class="fa-solid fa-paper-plane"></i> Rent Now
                            </button>
                        </div>
                    `;
                });
            }
        }
    } catch (e) {
        console.error("Failed to load saved listings", e);
    }
}

function switchSavedTab(type) {
    const btns = document.querySelectorAll('.saved-tabs .tab-mini');
    btns.forEach(b => b.classList.remove('active'));
    event.target.classList.add('active');

    if (type === 'saved') {
        loadSavedListings();
    } else {
        loadWishlist();
    }
}

async function loadWishlist() {
    if (!currentUser) return;
    try {
        const res = await fetch(`/api/wishlist?user_id=${currentUser.user_id}`);
        const items = await res.json();
        const container = document.getElementById('savedListingsContainer');

        if (container) {
            if (!items || items.length === 0) {
                container.innerHTML = '<div style="color: var(--text-muted); font-size: 13px;">No wishlist keyword alerts added yet.</div>';
            } else {
                container.innerHTML = '';
                items.forEach(item => {
                    container.innerHTML += `
                        <div class="request-card">
                            <div class="request-info">
                                <div class="request-title"><i class="fa-solid fa-bell"></i> Keyword Alert: "${item.keyword || 'All Equipment'}"</div>
                                <div class="request-meta">Category: ${item.category_name || 'General'}</div>
                            </div>
                            <span class="badge-tag info">Active Alert</span>
                        </div>
                    `;
                });
            }
        }
    } catch (e) {
        console.error("Failed to load wishlist", e);
    }
}

// --- TAB 5: CAMPUS INTELLIGENCE REPORTS ---
const REPORTS_TITLES = {
    1: "Platform Revenue & 10% Commission Summary",
    2: "Top 10 Lenders by Total Earnings",
    3: "Most Active Borrowers",
    4: "Category Revenue Performance",
    5: "Currently Active Rentals Overview",
    6: "Maintenance & Repair Expenses Log",
    7: "High Risk Overdue Rentals",
    8: "Unborrowed Idle Equipment Listings",
    9: "Rental Purpose Distribution",
    10: "Average Daily Rental Rates by Category",
    11: "User Trust Score Rankings",
    12: "Hostel Equipment Density Report",
    13: "Monthly Rental Trends",
    14: "Lender vs Borrower Ratings Comparison",
    15: "Delisted Equipment Audit Log"
};

function loadReportsList() {
    const container = document.getElementById('reportsMenuList');
    if (!container) return;

    container.innerHTML = '';
    for (let id = 1; id <= 15; id++) {
        const btn = document.createElement('div');
        btn.className = `report-menu-item ${id === currentReportId ? 'active' : ''}`;
        btn.innerHTML = `<i class="fa-solid fa-file-chart-column"></i> ${id < 10 ? '0' + id : id}. ${REPORTS_TITLES[id]}`;
        btn.onclick = () => {
            document.querySelectorAll('.report-menu-item').forEach(el => el.classList.remove('active'));
            btn.classList.add('active');
            currentReportId = id;
            loadReportData(id);
        };
        container.appendChild(btn);
    }
}

async function loadReportData(reportId) {
    currentReportId = reportId;
    const titleEl = document.getElementById('reportTitleDisplay');
    const rowsCountTag = document.getElementById('reportRowsCount');
    const thead = document.getElementById('reportTableHead');
    const tbody = document.getElementById('reportTableBody');

    if (titleEl) titleEl.textContent = `Report ${reportId < 10 ? '0' + reportId : reportId}: ${REPORTS_TITLES[reportId]}`;

    try {
        const res = await fetch(`/api/reports/${reportId}`);
        const data = await res.json();

        if (rowsCountTag) rowsCountTag.textContent = `${(data.data || []).length} Records`;

        // Render Table Headers
        if (thead) {
            thead.innerHTML = '<tr>' + (data.headers || []).map(h => `<th>${h}</th>`).join('') + '</tr>';
        }

        // Render Table Rows
        if (tbody) {
            if (!data.data || data.data.length === 0) {
                tbody.innerHTML = `<tr><td colspan="${(data.headers || []).length || 1}" style="text-align: center; color: var(--text-muted); padding: 30px;">No report records found.</td></tr>`;
            } else {
                tbody.innerHTML = data.data.map(row => {
                    return '<tr>' + row.map(cell => `<td>${cell}</td>`).join('') + '</tr>';
                }).join('');
            }
        }
    } catch (e) {
        console.error("Failed to load report data", e);
    }
}

function exportCurrentReportCSV() {
    window.location.href = `/api/reports/${currentReportId}/export`;
    showToast(`Downloading CSV for Report ${currentReportId}...`, 'info');
}

// --- TOAST SYSTEM ---
function showToast(message, type = 'info') {
    const container = document.getElementById('toastContainer');
    if (!container) return;

    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.innerHTML = `
        <i class="fa-solid ${type === 'success' ? 'fa-circle-check' : type === 'error' ? 'fa-triangle-exclamation' : 'fa-circle-info'}"></i>
        <span>${message}</span>
    `;

    container.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateY(20px)';
        setTimeout(() => toast.remove(), 300);
    }, 3500);
}
