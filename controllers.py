import os
import sys
import hashlib
import random
from datetime import datetime

import db_engine
from core.config import CommissionService
from core.security import hash_password, verify_password
from core.wallet_service import FinancialService

# Platform commission rate delegated to centralized CommissionService
COMMISSION_RATE = float(CommissionService.get_rental_commission_rate())

def execute_query(query, params=(), fetch=False, fetchone=False):
    """
    Central database query execution utility.
    Routes all queries through db_engine with automatic dialect adaptation.
    """
    try:
        if fetch == "lastrowid":
            return db_engine.execute_query(query, params, fetch="lastrowid")
        elif fetch is True or fetch == "all":
            res = db_engine.execute_query(query, params, fetch="all")
            if isinstance(res, list):
                return [tuple(r.values()) for r in res]
            return res
        elif fetchone or fetch == "one":
            res = db_engine.execute_query(query, params, fetch="one")
            if isinstance(res, dict):
                return tuple(res.values())
            return res
        else:
            q_upper = query.strip().upper()
            if q_upper.startswith("INSERT"):
                return db_engine.execute_query(query, params, fetch="lastrowid")
            return db_engine.execute_query(query, params, fetch="rowcount")
    except Exception as e:
        print(f"Database Error: {e}")
        if fetch is True or fetchone:
            return None if fetchone else []
        return -1

# --- USER & IDENTITY MODULE ---

def authenticate_user(email, password):
    """
    Validates user credentials against PBKDF2 password hash and checks account_status.
    Returns user dict on success, -1 for invalid email/password, or -2 for suspended account.
    """
    user = db_engine.execute_query(
        "SELECT user_id, name, email, verification_level, department, hostel, account_status, password_hash FROM users WHERE email = ?;",
        (email,), fetchone=True
    )
    if not user:
        return -1 # User not found
    
    if not verify_password(password, user["password_hash"]):
        return -1 # Invalid password
        
    if user["account_status"] == 'Suspended':
        return -2 # Suspended account
        
    # Automatic Legacy Password Hash Migration to dynamic per-user salt
    stored_hash = user["password_hash"]
    if "$umat_campuslink_2026$" in stored_hash or not stored_hash.startswith("pbkdf2_sha256$100000$"):
        new_dynamic_hash = hash_password(password)
        db_engine.execute_query("UPDATE users SET password_hash = ? WHERE user_id = ?;", (new_dynamic_hash, user["user_id"]))
        
    # Update last login timestamp
    db_engine.execute_query("UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE user_id = ?;", (user["user_id"],))
    
    return {
        'user_id': user["user_id"],
        'name': user["name"],
        'email': user["email"],
        'verification_level': user["verification_level"],
        'department': user["department"],
        'hostel': user["hostel"],
        'account_status': user["account_status"]
    }

def get_all_users():
    return execute_query("SELECT user_id, name, email, student_id, phone, verification_level, department, hostel, account_status FROM users ORDER BY name;", fetch=True)

def register_user(name, email, password, student_id, phone, department, hostel, verification_level='Unverified'):
    hashed = hash_password(password)
    query = """
    INSERT INTO users (name, email, password_hash, student_id, phone, verification_level, account_status, department, hostel)
    VALUES (?, ?, ?, ?, ?, ?, 'Active', ?, ?);
    """
    return execute_query(query, (name, email, hashed, student_id if student_id else None, phone, verification_level, department, hostel))

def update_user_verification(user_id, level):
    return execute_query("UPDATE users SET verification_level = ? WHERE user_id = ?;", (level, user_id))

def update_user_profile(user_id, phone, department, hostel, avatar_path=None):
    if avatar_path:
        return execute_query("UPDATE users SET phone = ?, department = ?, hostel = ?, avatar_path = ? WHERE user_id = ?;", (phone, department, hostel, avatar_path, user_id))
    else:
        return execute_query("UPDATE users SET phone = ?, department = ?, hostel = ? WHERE user_id = ?;", (phone, department, hostel, user_id))

def change_user_password(user_id, old_password, new_password):
    user = db_engine.execute_query("SELECT password_hash FROM users WHERE user_id = ?;", (user_id,), fetchone=True)
    if not user or not verify_password(old_password, user["password_hash"]):
        return -1 # Invalid old password
    new_hash = hash_password(new_password)
    return execute_query("UPDATE users SET password_hash = ? WHERE user_id = ?;", (new_hash, user_id))

# --- CATEGORY MODULE ---

def get_categories():
    return execute_query("SELECT category_id, name, description FROM categories ORDER BY name;", fetch=True)

# --- LISTINGS & MARKETPLACE MODULE ---

def create_listing(owner_id, category_id, title, description, subcategory, brand, model, purchase_year, rate, deposit, condition, location, start_date, end_date, thumbnail_path="assets/logo.jpg"):
    query = """
    INSERT INTO listings (
        owner_id, category_id, title, description, subcategory, brand, model, purchase_year,
        rental_rate_per_day, deposit_amount, condition, status, pickup_location, available_from, available_until, thumbnail_path
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'Available', ?, ?, ?, ?);
    """
    return execute_query(query, (owner_id, category_id, title, description, subcategory, brand, model, purchase_year, rate, deposit, condition, location, start_date, end_date, thumbnail_path))

def get_filtered_listings(keyword=None, category_id=None, max_price=None, condition=None, location=None, exclude_owner_id=None, req_start=None, req_end=None, owner_id=None):
    """
    Returns listings matching the query filters.
    If req_start and req_end are provided, checks that the listing is available for those dates:
      1. Dates fall within the listing's available_from/until.
      2. No overlapping active rental transaction exists.
    """
    query = """
    SELECT l.listing_id, l.title, l.description, l.subcategory, l.brand, l.model, 
           l.rental_rate_per_day, l.deposit_amount, l.condition, l.status, l.pickup_location,
           u.name AS owner_name, c.name AS category_name, l.available_from, l.available_until,
           l.owner_id, l.category_id, l.thumbnail_path, u.department
    FROM listings l
    INNER JOIN users u ON l.owner_id = u.user_id
    INNER JOIN categories c ON l.category_id = c.category_id
    WHERE l.status != 'Delisted'
    """
    params = []
    
    if owner_id:
        query += " AND l.owner_id = ?"
        params.append(owner_id)

    if exclude_owner_id:
        query += " AND l.owner_id != ?"
        params.append(exclude_owner_id)
        
    if keyword:
        query += " AND (l.title LIKE ? OR l.description LIKE ? OR l.brand LIKE ? OR l.model LIKE ?)"
        lk = f"%{keyword}%"
        params.extend([lk, lk, lk, lk])
        
    if category_id:
        query += " AND l.category_id = ?"
        params.append(category_id)
        
    if max_price:
        query += " AND l.rental_rate_per_day <= ?"
        params.append(max_price)
        
    if condition:
        query += " AND l.condition = ?"
        params.append(condition)
        
    if location:
        query += " AND l.pickup_location LIKE ?"
        params.append(f"%{location}%")
        
    # Date range filters (Availability Calendar Collision Checks)
    if req_start and req_end:
        query += " AND l.available_from <= ? AND l.available_until >= ?"
        params.extend([req_start, req_end])
        
        # Exclude any listing which has an overlapping active transaction
        query += """
        AND l.listing_id NOT IN (
            SELECT t.listing_id 
            FROM rental_transactions t
            WHERE t.rental_status IN ('Active', 'Overdue')
            AND NOT (t.rent_end_date < ? OR t.rent_start_date > ?)
        )
        """
        params.extend([req_start, req_end])
        
    query += " ORDER BY l.rental_rate_per_day ASC;"
    return execute_query(query, params, fetch=True)

def get_my_listings(owner_id):
    query = """
    SELECT l.listing_id, l.title, l.category_id, c.name, l.subcategory, l.brand, l.model, 
           l.rental_rate_per_day, l.deposit_amount, l.condition, l.status, l.pickup_location,
           l.available_from, l.available_until
    FROM listings l
    INNER JOIN categories c ON l.category_id = c.category_id
    WHERE l.owner_id = ? AND l.status != 'Delisted'
    ORDER BY l.created_at DESC;
    """
    return execute_query(query, (owner_id,), fetch=True)

# --- RENTAL REQUESTS MODULE ---

VALID_RENTAL_PURPOSES = {
    'Field Trip', 'Final Year Project', 'Laboratory Session', 'Research', 'Presentation', 'Personal Use'
}

def normalize_purpose(purpose_str):
    if not purpose_str:
        return 'Field Trip'
    p = str(purpose_str).strip()
    if p in VALID_RENTAL_PURPOSES:
        return p
    low = p.lower()
    if 'survey' in low or 'field' in low or 'trip' in low:
        return 'Field Trip'
    if 'lab' in low or 'experiment' in low or 'assignment' in low:
        return 'Laboratory Session'
    if 'project' in low:
        return 'Final Year Project'
    if 'research' in low:
        return 'Research'
    if 'present' in low or 'seminar' in low:
        return 'Presentation'
    return 'Personal Use'

def submit_rental_request(listing_id, borrower_id, start_date, end_date, purpose, notes):
    clean_purpose = normalize_purpose(purpose)
    query = """
    INSERT INTO rental_requests (listing_id, borrower_id, rent_start_date, rent_end_date, rental_purpose, status, notes)
    VALUES (?, ?, ?, ?, ?, 'Pending', ?);
    """
    req_id = execute_query(query, (listing_id, borrower_id, start_date, end_date, clean_purpose, notes), fetch="lastrowid")
    if req_id > 0:
        # Notify listing owner
        owner_res = db_engine.execute_query("SELECT owner_id, title FROM listings WHERE listing_id = ?;", (listing_id,), fetchone=True)
        if owner_res:
            owner_id, title = owner_res["owner_id"], owner_res["title"]
            create_notification(owner_id, "New Rental Request Received", f"A student requested to rent '{title}' ({start_date} to {end_date}).", "info")
    return req_id

def get_incoming_requests(owner_id):
    query = """
    SELECT r.request_id, l.title, u.name AS borrower_name, r.rent_start_date, r.rent_end_date, 
           r.rental_purpose, r.status, r.notes, r.listing_id, r.borrower_id
    FROM rental_requests r
    INNER JOIN listings l ON r.listing_id = l.listing_id
    INNER JOIN users u ON r.borrower_id = u.user_id
    WHERE l.owner_id = ? AND r.status = 'Pending'
    ORDER BY r.created_at DESC;
    """
    return execute_query(query, (owner_id,), fetch=True)

def get_my_requests(borrower_id):
    query = """
    SELECT r.request_id, l.title, u.name AS owner_name, r.rent_start_date, r.rent_end_date, 
           r.rental_purpose, r.status, r.notes, l.listing_id
    FROM rental_requests r
    INNER JOIN listings l ON r.listing_id = l.listing_id
    INNER JOIN users u ON l.owner_id = u.user_id
    WHERE r.borrower_id = ?
    ORDER BY r.created_at DESC;
    """
    return execute_query(query, (borrower_id,), fetch=True)

def approve_request(request_id):
    """
    Atomically approves a rental request, reserves the listing, creates a financial transaction
    record (calculating 10% platform fee and 90% owner earnings), and rejects conflicting requests.
    Uses atomic transaction context manager across SQLite and MySQL.
    """
    try:
        with db_engine.transaction() as tx:
            req = tx.execute(
                "SELECT listing_id, borrower_id, rent_start_date, rent_end_date, rental_purpose FROM rental_requests WHERE request_id = ?;",
                (request_id,), fetchone=True
            )
            if not req:
                return -1
                
            listing_id = req["listing_id"]
            borrower_id = req["borrower_id"]
            start_date = str(req["rent_start_date"])
            end_date = str(req["rent_end_date"])
            
            # Verify listing exists and is available
            lst = tx.execute(
                "SELECT rental_rate_per_day, deposit_amount, status, title FROM listings WHERE listing_id = ?;",
                (listing_id,), fetchone=True
            )
            if not lst or lst["status"] == 'Delisted':
                return -2  # Listing not available
                
            rate = float(lst["rental_rate_per_day"])
            deposit = float(lst["deposit_amount"])
            title = lst["title"]
            
            # Calculate days and amounts
            d1 = datetime.strptime(start_date, "%Y-%m-%d")
            d2 = datetime.strptime(end_date, "%Y-%m-%d")
            total_days = max((d2 - d1).days + 1, 1)
            gross_amount = rate * total_days
            split = CommissionService.calculate_rental_split(gross_amount)
            commission = float(split["commission_amount"])
            earnings = float(split["owner_earnings"])
            
            # 1. Update Request & Listing Status
            tx.execute("UPDATE rental_requests SET status = 'Approved' WHERE request_id = ?;", (request_id,))
            tx.execute("UPDATE listings SET status = 'Reserved' WHERE listing_id = ?;", (listing_id,))
            
            # 2. Create Transaction Record if not already created
            tx_exists = tx.execute("SELECT transaction_id FROM rental_transactions WHERE request_id = ?;", (request_id,), fetchone=True)
            if not tx_exists:
                rent_tx_id = tx.execute("""
                INSERT INTO rental_transactions (
                    request_id, listing_id, borrower_id, rent_start_date, rent_end_date, total_days,
                    gross_amount, commission_amount, owner_earnings, deposit_held, payment_status, rental_status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'Paid', 'Active');
                """, (request_id, listing_id, borrower_id, start_date, end_date, total_days, gross_amount, commission, earnings, deposit), fetch="lastrowid")
            else:
                rent_tx_id = tx_exists["transaction_id"]

            # Dual-Sided Balanced Rental Escrow Hold
            FinancialService.hold_rental_escrow(tx, rent_tx_id, borrower_id, gross_amount, deposit)
            
            # 3. Reject any conflicting overlapping pending requests
            tx.execute("""
            UPDATE rental_requests 
            SET status = 'Rejected', notes = 'Another request was approved for overlapping dates.'
            WHERE listing_id = ? AND status = 'Pending' AND request_id != ?
            AND NOT (rent_end_date < ? OR rent_start_date > ?);
            """, (listing_id, request_id, start_date, end_date))
            
            # 4. Notify borrower
            tx.execute("""
            INSERT INTO notifications (user_id, title, message, type, is_read)
            VALUES (?, 'Rental Request Approved!', ?, 'success', 0);
            """, (borrower_id, f"Your booking request for '{title}' ({start_date} to {end_date}) was approved."))

        return 1
    except Exception as e:
        print(f"Error approving request #{request_id}: {e}")
        return -3

def reject_request(request_id, notes="Declined by owner."):
    return execute_query("UPDATE rental_requests SET status = 'Rejected', notes = ? WHERE request_id = ?;", (notes, request_id))

def cancel_request(request_id):
    return execute_query("UPDATE rental_requests SET status = 'Cancelled' WHERE request_id = ?;", (request_id,))

# --- RENTAL TRANSACTIONS & RETURNS MODULE ---

def get_my_borrowed_items(borrower_id):
    """Get all items (Active, Overdue, Returned) borrowed by the user."""
    query = """
    SELECT t.transaction_id, l.listing_id, l.title, u.name AS owner_name, t.rent_start_date, t.rent_end_date, 
           t.gross_amount, t.rental_status, l.owner_id
    FROM rental_transactions t
    INNER JOIN listings l ON t.listing_id = l.listing_id
    INNER JOIN users u ON l.owner_id = u.user_id
    WHERE t.borrower_id = ?
    ORDER BY t.created_at DESC;
    """
    return execute_query(query, (borrower_id,), fetch=True)

def get_my_lent_items(owner_id):
    """Get items listed by user currently rented out."""
    query = """
    SELECT t.transaction_id, l.title, u.name AS borrower_name, t.rent_start_date, t.rent_end_date, 
           t.rental_status, t.deposit_held, t.gross_amount, l.listing_id, t.borrower_id
    FROM rental_transactions t
    INNER JOIN listings l ON t.listing_id = l.listing_id
    INNER JOIN users u ON t.borrower_id = u.user_id
    WHERE l.owner_id = ? AND t.rental_status IN ('Active', 'Overdue')
    ORDER BY t.rent_end_date ASC;
    """
    return execute_query(query, (owner_id,), fetch=True)

def process_return(transaction_id, return_notes, damage_condition, claim_amount=0.0):
    """
    Atomically processes the return of a rented item.
    - Updates transaction actual_return_date and status to 'Returned'.
    - Performs dual-sided balanced escrow release (90% owner, 10% platform fee, deposit refund).
    - If damaged, auto-spawns a maintenance ticket with claim cost.
    Uses atomic transaction context manager across SQLite and MySQL.
    """
    try:
        with db_engine.transaction() as tx:
            tx_rec = tx.execute("""
            SELECT t.listing_id, t.borrower_id, t.deposit_held, t.gross_amount, l.owner_id
            FROM rental_transactions t
            INNER JOIN listings l ON t.listing_id = l.listing_id
            WHERE t.transaction_id = ?;
            """, (transaction_id,), fetchone=True)
            if not tx_rec:
                return -1
                
            listing_id = tx_rec["listing_id"]
            borrower_id = tx_rec["borrower_id"]
            owner_id = tx_rec["owner_id"]
            gross = float(tx_rec["gross_amount"])
            deposit = float(tx_rec["deposit_held"])
            today_str = datetime.now().strftime("%Y-%m-%d")
            
            # 1. Update Transaction record
            tx.execute("""
            UPDATE rental_transactions 
            SET actual_return_date = ?, rental_status = 'Returned', return_notes = ?
            WHERE transaction_id = ?;
            """, (today_str, return_notes, transaction_id))

            # 2. Dual-Sided Balanced Rental Escrow Release
            FinancialService.release_rental_escrow(
                tx=tx,
                transaction_id=transaction_id,
                borrower_id=borrower_id,
                owner_id=owner_id,
                gross_amount=gross,
                deposit_amount=deposit,
                damage_claim=claim_amount
            )
            
            # 3. Update Listing Status and handle deposit / maintenance
            if damage_condition == 'Good':
                tx.execute("UPDATE listings SET status = 'Available' WHERE listing_id = ?;", (listing_id,))
            elif damage_condition == 'Minor':
                tx.execute("UPDATE listings SET status = 'Maintenance' WHERE listing_id = ?;", (listing_id,))
                tx.execute("""
                INSERT INTO maintenance (listing_id, reported_by, issue_description, cost, status, start_date)
                VALUES (?, ?, ?, ?, 'Pending', ?);
                """, (listing_id, borrower_id, f"Minor damage logged upon return. Return notes: {return_notes}", claim_amount, today_str))
            else: # Severe damage
                tx.execute("UPDATE listings SET status = 'Maintenance' WHERE listing_id = ?;", (listing_id,))
                tx.execute("""
                INSERT INTO maintenance (listing_id, reported_by, issue_description, cost, status, start_date)
                VALUES (?, ?, ?, ?, 'In Progress', ?);
                """, (listing_id, borrower_id, f"SEVERE damage logged upon return. Return notes: {return_notes}", deposit, today_str))

        return 1
    except Exception as e:
        print(f"Error processing return for tx #{transaction_id}: {e}")
        return -2

# --- PEER REVIEWS MODULE ---

def submit_review(transaction_id, reviewer_id, reviewee_id, reviewee_type, rating, comment):
    exists = db_engine.execute_query("""
    SELECT count(*) as cnt FROM reviews 
    WHERE transaction_id = ? AND reviewer_id = ? AND reviewee_type = ?;
    """, (transaction_id, reviewer_id, reviewee_type), fetchone=True)
    
    if exists and exists["cnt"] > 0:
        return -1  # Review already submitted
        
    query = """
    INSERT INTO reviews (transaction_id, reviewer_id, reviewee_id, reviewee_type, rating, comment)
    VALUES (?, ?, ?, ?, ?, ?);
    """
    return execute_query(query, (transaction_id, reviewer_id, reviewee_id, reviewee_type, rating, comment))

def get_reviews_for_user(user_id):
    query = """
    SELECT r.rating, r.comment, r.created_at, u.name AS reviewer_name, r.reviewee_type
    FROM reviews r
    INNER JOIN users u ON r.reviewer_id = u.user_id
    WHERE r.reviewee_id = ?
    ORDER BY r.created_at DESC;
    """
    return execute_query(query, (user_id,), fetch=True)

# --- WISHLIST & SAVED LISTINGS MODULE ---

def add_to_wishlist(user_id, category_id, keyword):
    query = "INSERT OR IGNORE INTO wishlist (user_id, category_id, keyword) VALUES (?, ?, ?);"
    return execute_query(query, (user_id, category_id if category_id else None, keyword if keyword else None))

def remove_from_wishlist(wishlist_id):
    return execute_query("DELETE FROM wishlist WHERE wishlist_id = ?;", (wishlist_id,))

def get_my_wishlist(user_id):
    query = """
    SELECT w.wishlist_id, c.name, w.keyword, w.created_at, w.category_id
    FROM wishlist w
    LEFT JOIN categories c ON w.category_id = c.category_id
    WHERE w.user_id = ?
    ORDER BY w.created_at DESC;
    """
    return execute_query(query, (user_id,), fetch=True)

def save_listing(user_id, listing_id):
    query = "INSERT OR IGNORE INTO saved_listings (user_id, listing_id) VALUES (?, ?);"
    return execute_query(query, (user_id, listing_id))

def unsave_listing(saved_id):
    return execute_query("DELETE FROM saved_listings WHERE saved_id = ?;", (saved_id,))

def get_my_saved_listings(user_id):
    query = """
    SELECT s.saved_id, l.listing_id, l.title, l.rental_rate_per_day, l.deposit_amount, l.condition, l.status, u.name
    FROM saved_listings s
    INNER JOIN listings l ON s.listing_id = l.listing_id
    INNER JOIN users u ON l.owner_id = u.user_id
    WHERE s.user_id = ?
    ORDER BY s.created_at DESC;
    """
    return execute_query(query, (user_id,), fetch=True)

# --- MAINTENANCE RECORDS MODULE ---

def get_maintenance_records():
    query = """
    SELECT m.maintenance_id, m.listing_id, l.title, u.name AS reported_by_name, m.issue_description, m.cost, m.status, m.start_date, m.end_date
    FROM maintenance m
    INNER JOIN listings l ON m.listing_id = l.listing_id
    INNER JOIN users u ON m.reported_by = u.user_id
    ORDER BY m.status DESC, m.start_date DESC;
    """
    return execute_query(query, fetch=True)

def update_maintenance(maintenance_id, cost, status, listing_id):
    try:
        with db_engine.transaction() as tx:
            today_str = datetime.now().strftime("%Y-%m-%d") if status == 'Completed' else None
            
            if status == 'Completed':
                tx.execute("UPDATE maintenance SET cost = ?, status = ?, end_date = ? WHERE maintenance_id = ?;", (cost, status, today_str, maintenance_id))
                tx.execute("UPDATE listings SET status = 'Available' WHERE listing_id = ?;", (listing_id,))
            else:
                tx.execute("UPDATE maintenance SET cost = ?, status = ? WHERE maintenance_id = ?;", (cost, status, maintenance_id))
                
        return 1
    except Exception as e:
        print(f"Error updating maintenance #{maintenance_id}: {e}")
        return -1

# --- TRUST SCORE & DERIVED METRICS ---

def calculate_trust_score(user_id):
    """
    Derives trust score based on combined rental & service rating averages, completed transactions, and late returns.
    Formula: Base (50) + (Avg Rating * 8) + (Total Completed Rentals & Services * 0.5) - (Late Returns * 5)
    Capped [0, 100]. Returns dict with score and components.
    Uses centralized db_engine queries.
    """
    # 1. Combined Rating: Rental reviews + Service reviews
    res_rating = db_engine.execute_query("SELECT AVG(rating) as avg_r, COUNT(review_id) as cnt FROM reviews WHERE reviewee_id = ?;", (user_id,), fetchone=True)
    res_svc_rating = db_engine.execute_query("SELECT AVG(rating) as avg_r, COUNT(review_id) as cnt FROM service_reviews WHERE provider_id = ?;", (user_id,), fetchone=True)
    
    rental_cnt = int(res_rating["cnt"]) if res_rating else 0
    service_cnt = int(res_svc_rating["cnt"]) if res_svc_rating else 0
    total_reviews = rental_cnt + service_cnt
    
    if total_reviews > 0:
        rental_sum = float(res_rating["avg_r"]) * rental_cnt if (res_rating and res_rating["avg_r"] is not None) else 0.0
        service_sum = float(res_svc_rating["avg_r"]) * service_cnt if (res_svc_rating and res_svc_rating["avg_r"] is not None) else 0.0
        avg_rating = (rental_sum + service_sum) / total_reviews
    else:
        avg_rating = 5.0
        
    rating_count = total_reviews
    
    # 2. Completed rentals as borrower
    borrowed_res = db_engine.execute_query("SELECT COUNT(transaction_id) as cnt FROM rental_transactions WHERE borrower_id = ? AND rental_status = 'Returned';", (user_id,), fetchone=True)
    completed_borrowed = int(borrowed_res["cnt"]) if borrowed_res else 0
    
    # 3. Completed rentals as lender
    lent_res = db_engine.execute_query("""
    SELECT COUNT(t.transaction_id) as cnt
    FROM rental_transactions t
    INNER JOIN listings l ON t.listing_id = l.listing_id
    WHERE l.owner_id = ? AND t.rental_status = 'Returned';
    """, (user_id,), fetchone=True)
    completed_lent = int(lent_res["cnt"]) if lent_res else 0
    
    # 4. Completed services as provider
    svc_completed_res = db_engine.execute_query("SELECT COUNT(order_id) as cnt FROM service_orders WHERE provider_id = ? AND status = 'Completed';", (user_id,), fetchone=True)
    completed_services = int(svc_completed_res["cnt"]) if svc_completed_res else 0
    
    total_completed = completed_borrowed + completed_lent + completed_services
    
    # 5. Late returns as borrower (actual_return_date > rent_end_date)
    late_res = db_engine.execute_query("""
    SELECT COUNT(transaction_id) as cnt FROM rental_transactions 
    WHERE borrower_id = ? AND actual_return_date > rent_end_date;
    """, (user_id,), fetchone=True)
    late_returns = int(late_res["cnt"]) if late_res else 0
    
    # Calculate Score
    score = 50 + (avg_rating * 8) + (total_completed * 0.5) - (late_returns * 5)
    score = max(0, min(100, int(score)))
    
    return {
        "score": score,
        "avg_rating": round(avg_rating, 1),
        "total_rentals": completed_borrowed + completed_lent,
        "total_services": completed_services,
        "late_returns": late_returns,
        "rating_count": rating_count,
        "damage_claims": 0
    }

# --- BUSINESS INTELLIGENCE REPORTS (ALL 15) ---

def get_report_data(report_index):
    """
    Executes one of the 15 requested Business Intelligence Reports across SQLite & MySQL.
    Returns: (list_of_column_headers, list_of_rows)
    """
    headers = []
    rows = []
    
    try:
        if report_index == 1:
            headers = ["Total Transactions", "Total Gross volume (GH₵)", "Platform Commissions (GH₵)", "Lenders Net Earnings (GH₵)"]
            raw = db_engine.execute_query("""
            SELECT COUNT(transaction_id) as total_tx, SUM(gross_amount) as total_gross, SUM(commission_amount) as total_comm, SUM(owner_earnings) as total_net
            FROM rental_transactions WHERE payment_status = 'Paid';
            """, fetch="all")
            rows = [tuple(r.values()) for r in (raw or [])]
            
        elif report_index == 2:
            headers = ["Lender Name", "Department", "Hostel", "Items Listed", "Total Net Earnings (GH₵)"]
            raw = db_engine.execute_query("""
            SELECT u.name, u.department, u.hostel, COUNT(DISTINCT l.listing_id) as items_listed, SUM(t.owner_earnings) as net_earnings
            FROM users u
            INNER JOIN listings l ON u.user_id = l.owner_id
            INNER JOIN rental_transactions t ON l.listing_id = t.listing_id
            GROUP BY u.user_id, u.name, u.department, u.hostel
            ORDER BY SUM(t.owner_earnings) DESC;
            """, fetch="all")
            rows = [tuple(r.values()) for r in (raw or [])]
            
        elif report_index == 3:
            headers = ["Borrower Name", "Department", "Hostel", "Total Rentals", "Total Amount Spent (GH₵)"]
            raw = db_engine.execute_query("""
            SELECT u.name, u.department, u.hostel, COUNT(t.transaction_id) as total_rentals, SUM(t.gross_amount) as total_spent
            FROM users u
            INNER JOIN rental_transactions t ON u.user_id = t.borrower_id
            GROUP BY u.user_id, u.name, u.department, u.hostel
            ORDER BY SUM(t.gross_amount) DESC;
            """, fetch="all")
            rows = [tuple(r.values()) for r in (raw or [])]
            
        elif report_index == 4:
            headers = ["Category Name", "Total Listed Assets", "Total Rentals Generated", "Gross Volume Generated (GH₵)"]
            raw = db_engine.execute_query("""
            SELECT c.name, COUNT(DISTINCT l.listing_id) as listed_assets, COUNT(t.transaction_id) as rentals_count, SUM(t.gross_amount) as gross_volume
            FROM categories c
            LEFT JOIN listings l ON c.category_id = l.category_id
            LEFT JOIN rental_transactions t ON l.listing_id = t.listing_id
            GROUP BY c.category_id, c.name
            ORDER BY COUNT(t.transaction_id) DESC;
            """, fetch="all")
            rows = [tuple(r.values()) for r in (raw or [])]
            
        elif report_index == 5:
            headers = ["Listing Title", "Category", "Brand", "Model", "Owner", "Daily Rate (GH₵)", "Total Rentals"]
            raw = db_engine.execute_query("""
            SELECT l.title, c.name, l.brand, l.model, u.name, l.rental_rate_per_day, COUNT(t.transaction_id) as rentals_count
            FROM listings l
            INNER JOIN categories c ON l.category_id = c.category_id
            INNER JOIN users u ON l.owner_id = u.user_id
            INNER JOIN rental_transactions t ON l.listing_id = t.listing_id
            GROUP BY l.listing_id, l.title, c.name, l.brand, l.model, u.name, l.rental_rate_per_day
            ORDER BY COUNT(t.transaction_id) DESC;
            """, fetch="all")
            rows = [tuple(r.values()) for r in (raw or [])]
            
        elif report_index == 6:
            headers = ["Listing Title", "Category", "Brand", "Model", "Owner", "Daily Rate (GH₵)", "Date Created"]
            raw = db_engine.execute_query("""
            SELECT l.title, c.name, l.brand, l.model, u.name, l.rental_rate_per_day, l.created_at
            FROM listings l
            INNER JOIN categories c ON l.category_id = c.category_id
            INNER JOIN users u ON l.owner_id = u.user_id
            LEFT JOIN rental_transactions t ON l.listing_id = t.listing_id
            WHERE t.transaction_id IS NULL;
            """, fetch="all")
            rows = [tuple(r.values()) for r in (raw or [])]
            
        elif report_index == 7:
            # Report 07: Current Overdue Rentals (Dialect-neutral calculation)
            headers = ["Renter Name", "Listing Title", "Owner Name", "Rent End Date", "Days Overdue", "Held Deposit (GH₵)"]
            today_str = datetime.now().strftime("%Y-%m-%d")
            today_d = datetime.now().date()
            raw = db_engine.execute_query("""
            SELECT u_b.name AS renter_name, l.title, u_o.name AS owner_name, t.rent_end_date, t.deposit_held
            FROM rental_transactions t
            INNER JOIN listings l ON t.listing_id = l.listing_id
            INNER JOIN users u_b ON t.borrower_id = u_b.user_id
            INNER JOIN users u_o ON l.owner_id = u_o.user_id
            WHERE t.rental_status = 'Active' AND t.rent_end_date < ?;
            """, (today_str,), fetch="all")
            
            rows = []
            for r in (raw or []):
                try:
                    end_d = datetime.strptime(str(r["rent_end_date"]), "%Y-%m-%d").date()
                    days_over = max((today_d - end_d).days, 0)
                except Exception:
                    days_over = 1
                rows.append((r["renter_name"], r["title"], r["owner_name"], r["rent_end_date"], days_over, r["deposit_held"]))
            
        elif report_index == 8:
            headers = ["Listing Title", "Brand", "Model", "Damage Issue", "Total Repair Costs (GH₵)", "Repair Status", "Logged Date"]
            raw = db_engine.execute_query("""
            SELECT l.title, l.brand, l.model, m.issue_description, m.cost, m.status, m.start_date
            FROM maintenance m
            INNER JOIN listings l ON m.listing_id = l.listing_id
            ORDER BY m.cost DESC;
            """, fetch="all")
            rows = [tuple(r.values()) for r in (raw or [])]
            
        elif report_index == 9:
            headers = ["Rental Purpose", "Rental Request Count", "Gross Value Supported (GH₵)"]
            raw = db_engine.execute_query("""
            SELECT r.rental_purpose, COUNT(r.request_id) as req_count, SUM(t.gross_amount) as gross_val
            FROM rental_requests r
            LEFT JOIN rental_transactions t ON r.request_id = t.request_id
            GROUP BY r.rental_purpose
            ORDER BY COUNT(r.request_id) DESC;
            """, fetch="all")
            rows = [tuple(r.values()) for r in (raw or [])]
            
        elif report_index == 10:
            headers = ["Category Name", "Average Rental Period (Days)", "Max Period (Days)"]
            raw = db_engine.execute_query("""
            SELECT c.name, AVG(t.total_days) as avg_days, MAX(t.total_days) as max_days
            FROM categories c
            INNER JOIN listings l ON c.category_id = l.category_id
            INNER JOIN rental_transactions t ON l.listing_id = t.listing_id
            GROUP BY c.category_id, c.name;
            """, fetch="all")
            rows = [tuple(r.values()) for r in (raw or [])]
            
        elif report_index == 11:
            headers = ["Lender Name", "Avg Star Rating", "Reviews Received", "Hostel"]
            raw = db_engine.execute_query("""
            SELECT u.name, AVG(r.rating) as avg_r, COUNT(r.review_id) as rev_count, u.hostel
            FROM users u
            INNER JOIN reviews r ON u.user_id = r.reviewee_id
            WHERE r.reviewee_type = 'Lender'
            GROUP BY u.user_id, u.name, u.hostel
            ORDER BY AVG(r.rating) DESC;
            """, fetch="all")
            rows = [tuple(r.values()) for r in (raw or [])]
            
        elif report_index == 12:
            headers = ["Borrower Name", "Avg Star Rating", "Reviews Received", "Department"]
            raw = db_engine.execute_query("""
            SELECT u.name, AVG(r.rating) as avg_r, COUNT(r.review_id) as rev_count, u.department
            FROM users u
            INNER JOIN reviews r ON u.user_id = r.reviewee_id
            WHERE r.reviewee_type = 'Borrower'
            GROUP BY u.user_id, u.name, u.department
            ORDER BY AVG(r.rating) DESC;
            """, fetch="all")
            rows = [tuple(r.values()) for r in (raw or [])]
            
        elif report_index == 13:
            headers = ["Hostel Name", "Active Assets Available", "Most Listed Category"]
            raw = db_engine.execute_query("""
            SELECT u.hostel, COUNT(l.listing_id) as asset_count, MAX(c.name) as category_name
            FROM users u
            INNER JOIN listings l ON u.user_id = l.owner_id
            INNER JOIN categories c ON l.category_id = c.category_id
            WHERE l.status = 'Available'
            GROUP BY u.hostel
            ORDER BY COUNT(l.listing_id) DESC;
            """, fetch="all")
            rows = [tuple(r.values()) for r in (raw or [])]
            
        elif report_index == 14:
            headers = ["Year-Month", "Total Rentals Completed", "Total gross Volume (GH₵)", "Platform Commissions (GH₵)"]
            raw = db_engine.execute_query("""
            SELECT SUBSTR(created_at, 1, 7) AS ym, COUNT(transaction_id) as total_tx, SUM(gross_amount) as total_gross, SUM(commission_amount) as total_comm
            FROM rental_transactions
            GROUP BY SUBSTR(created_at, 1, 7)
            ORDER BY ym DESC;
            """, fetch="all")
            rows = [tuple(r.values()) for r in (raw or [])]
            
        elif report_index == 15:
            headers = ["Borrower Name", "Department", "Hostel", "Late Return Incidents"]
            raw = db_engine.execute_query("""
            SELECT u.name, u.department, u.hostel, COUNT(t.transaction_id) as late_count
            FROM users u
            INNER JOIN rental_transactions t ON u.user_id = t.borrower_id
            WHERE t.actual_return_date > t.rent_end_date
            GROUP BY u.user_id, u.name, u.department, u.hostel
            ORDER BY COUNT(t.transaction_id) DESC;
            """, fetch="all")
            rows = [tuple(r.values()) for r in (raw or [])]
            
    except Exception as e:
        print(f"Report #{report_index} execution failed: {e}")
        
    return headers, rows

def get_intelligence_report(report_index):
    headers, rows = get_report_data(report_index)
    return {"headers": headers, "data": rows}

# Aliases for backward compatibility
approve_rental_request = approve_request
get_owner_rental_requests = get_incoming_requests
get_borrower_transactions = get_my_borrowed_items
get_all_maintenance_records = get_maintenance_records

def update_maintenance_status(maintenance_id, status, listing_id, cost=0.0):
    return update_maintenance(maintenance_id, cost, status, listing_id)

def process_item_return(transaction_id, actual_return_date=None, is_damaged=False, cost=0.0, notes=""):
    damage_cond = "Damaged" if is_damaged else "Good"
    return process_return(transaction_id, notes, damage_cond, claim_amount=cost)

# --- NOTIFICATION MODULE ---

def create_notification(user_id, title, message, type='info'):
    query = "INSERT INTO notifications (user_id, title, message, type, is_read) VALUES (?, ?, ?, ?, 0);"
    return execute_query(query, (user_id, title, message, type), fetch="lastrowid")

def get_user_notifications(user_id):
    query = "SELECT notification_id, title, message, type, is_read, created_at FROM notifications WHERE user_id = ? ORDER BY created_at DESC;"
    return execute_query(query, (user_id,), fetch=True)

def mark_notification_as_read(notification_id):
    query = "UPDATE notifications SET is_read = 1 WHERE notification_id = ?;"
    return execute_query(query, (notification_id,))

def get_unread_notification_count(user_id):
    res = execute_query("SELECT COUNT(*) FROM notifications WHERE user_id = ? AND is_read = 0;", (user_id,), fetchone=True)
    return res[0] if res else 0

# --- MOBILE MONEY (MOMO) SIMULATOR MODULE ---

def process_momo_payment(user_id, amount, network, phone_number, reference_note="CampusLink Payment"):
    """
    Simulates Mobile Money payment processing (MTN MoMo, Telecel Cash, AirtelTigo Money).
    Returns a dict with success state, transaction reference, and timestamp.
    """
    clean_phone = str(phone_number).strip().replace(" ", "").replace("-", "")
    if len(clean_phone) < 9 or not clean_phone.replace("+", "").isdigit():
        return {"success": False, "message": "Invalid phone number format."}
        
    momo_ref = f"MOMO_{network[:3].upper()}_{int(datetime.now().timestamp())}_{random.randint(1000, 9999)}"
    
    # Log notification
    create_notification(
        user_id,
        "Mobile Money Payment Successful",
        f"Payment of GH₵ {amount:.2f} via {network} ({clean_phone}) succeeded. Ref: {momo_ref}",
        "success"
    )
    
    return {
        "success": True,
        "transaction_ref": momo_ref,
        "network": network,
        "phone_number": clean_phone,
        "amount": amount,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "message": f"Payment of GH₵ {amount:.2f} confirmed via {network}."
    }

# --- UMAT CAMPUS LOCATIONS & GEOLOCATION MODULE ---

UMAT_CAMPUS_LOCATIONS = [
    {"id": "mines_hall", "name": "Chamber of Mines Hall", "lat": 5.2981, "lng": -1.9962, "category": "Hostel", "zone": "South Campus"},
    {"id": "kt_hall", "name": "KT Hall / Goldfields Hall", "lat": 5.2995, "lng": -1.9950, "category": "Hostel", "zone": "South Campus"},
    {"id": "main_admin", "name": "Main Campus Gate & Admin Block", "lat": 5.3012, "lng": -1.9975, "category": "Administration", "zone": "Main Campus"},
    {"id": "petroleum_block", "name": "Petroleum Engineering Complex", "lat": 5.3005, "lng": -1.9982, "category": "Academic Block", "zone": "Engineering Zone"},
    {"id": "geomatic_annex", "name": "Geomatic Engineering Lab Annex", "lat": 5.3018, "lng": -1.9968, "category": "Laboratory", "zone": "Engineering Zone"},
    {"id": "library_complex", "name": "Main University Library Complex", "lat": 5.3010, "lng": -1.9960, "category": "Academic Support", "zone": "Central Campus"}
]

def get_campus_locations():
    return UMAT_CAMPUS_LOCATIONS

def resolve_location_coordinates(location_name):
    low_name = str(location_name).lower()
    for loc in UMAT_CAMPUS_LOCATIONS:
        if loc["name"].lower() in low_name or loc["id"] in low_name:
            return loc
    return UMAT_CAMPUS_LOCATIONS[2]

# =============================================================================
# PHASE 3: SERVICES & SKILLS MARKETPLACE MODULE
# =============================================================================

def get_services(category_id=None, keyword=None, status='Active'):
    """
    Returns list of active student services with provider info and review ratings.
    """
    query = """
    SELECT s.service_id, s.provider_id, u.name AS provider_name, u.department AS provider_department,
           u.verification_level, s.category_id, c.name AS category_name, s.title, s.description,
           s.subcategory, s.pricing_model, s.price, s.delivery_time_days, s.portfolio_urls, s.status,
           COALESCE(AVG(sr.rating), 5.0) as avg_rating, COUNT(sr.review_id) as review_count
    FROM services s
    INNER JOIN users u ON s.provider_id = u.user_id
    INNER JOIN categories c ON s.category_id = c.category_id
    LEFT JOIN service_reviews sr ON s.provider_id = sr.provider_id
    WHERE 1=1
    """
    params = []
    if status:
        query += " AND s.status = ?"
        params.append(status)
    if category_id and category_id != 'all':
        query += " AND s.category_id = ?"
        params.append(int(category_id))
    if keyword:
        query += " AND (s.title LIKE ? OR s.description LIKE ? OR s.subcategory LIKE ?)"
        term = f"%{keyword}%"
        params.extend([term, term, term])
        
    query += " GROUP BY s.service_id ORDER BY s.created_at DESC;"
    return execute_query(query, params, fetch=True)

def get_service_by_id(service_id):
    """
    Fetches full service details, provider profile summary, and historical service reviews.
    """
    svc = db_engine.execute_query("""
    SELECT s.service_id, s.provider_id, u.name AS provider_name, u.email AS provider_email,
           u.phone AS provider_phone, u.department AS provider_department, u.hostel AS provider_hostel,
           u.verification_level, s.category_id, c.name AS category_name, s.title, s.description,
           s.subcategory, s.pricing_model, s.price, s.delivery_time_days, s.portfolio_urls, s.status,
           s.created_at
    FROM services s
    INNER JOIN users u ON s.provider_id = u.user_id
    INNER JOIN categories c ON s.category_id = c.category_id
    WHERE s.service_id = ?;
    """, (service_id,), fetchone=True)
    
    if not svc:
        return None
        
    # Fetch reviews
    reviews_raw = db_engine.execute_query("""
    SELECT sr.review_id, sr.order_id, u.name AS client_name, sr.rating, sr.comment, sr.created_at
    FROM service_reviews sr
    INNER JOIN users u ON sr.client_id = u.user_id
    WHERE sr.provider_id = ?
    ORDER BY sr.created_at DESC;
    """, (svc["provider_id"],), fetch="all")
    
    svc_dict = dict(svc)
    svc_dict["reviews"] = [dict(r) for r in (reviews_raw or [])]
    svc_dict["avg_rating"] = round(sum(r["rating"] for r in svc_dict["reviews"]) / len(svc_dict["reviews"]), 1) if svc_dict["reviews"] else 5.0
    svc_dict["review_count"] = len(svc_dict["reviews"])
    return svc_dict

def get_my_services(provider_id):
    """Returns all services offered by the authenticated provider."""
    query = """
    SELECT s.service_id, s.category_id, c.name AS category_name, s.title, s.description,
           s.subcategory, s.pricing_model, s.price, s.delivery_time_days, s.status, s.created_at
    FROM services s
    INNER JOIN categories c ON s.category_id = c.category_id
    WHERE s.provider_id = ?
    ORDER BY s.created_at DESC;
    """
    return execute_query(query, (provider_id,), fetch=True)

def create_service(provider_id, category_id, title, description, subcategory, pricing_model, price, delivery_time_days, portfolio_urls=None):
    """Creates a new student service listing."""
    query = """
    INSERT INTO services (provider_id, category_id, title, description, subcategory, pricing_model, price, delivery_time_days, portfolio_urls, status)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'Active');
    """
    return execute_query(query, (provider_id, category_id, title, description, subcategory, pricing_model, float(price), int(delivery_time_days), portfolio_urls), fetch="lastrowid")

def update_service(service_id, provider_id, title, description, subcategory, pricing_model, price, delivery_time_days, portfolio_urls=None):
    """Updates service details asserting provider ownership."""
    existing = db_engine.execute_query("SELECT provider_id FROM services WHERE service_id = ?;", (service_id,), fetchone=True)
    if not existing:
        return -1 # Not found
    if int(existing["provider_id"]) != int(provider_id):
        return -3 # Unauthorized
        
    query = """
    UPDATE services 
    SET title = ?, description = ?, subcategory = ?, pricing_model = ?, price = ?, delivery_time_days = ?, portfolio_urls = ?, updated_at = CURRENT_TIMESTAMP
    WHERE service_id = ? AND provider_id = ?;
    """
    return execute_query(query, (title, description, subcategory, pricing_model, float(price), int(delivery_time_days), portfolio_urls, service_id, provider_id))

def update_service_status(service_id, provider_id, status):
    """Toggles service status (Active, Paused, Delisted) asserting provider ownership."""
    if status not in ('Active', 'Paused', 'Delisted'):
        return -2 # Invalid status
    return execute_query("UPDATE services SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE service_id = ? AND provider_id = ?;", (status, service_id, provider_id))

# --- SERVICE ORDERS & ESCROW STATE MACHINE ---

def create_service_order(service_id, client_id, requirements, due_date):
    """
    Atomically places a client service order:
    - Snapshots locked provider_id, price, and fee calculations.
    - Locks client escrow funds with an atomic WalletTransaction (DepositEscrowHold, DEBIT).
    - Sets order status='Pending', escrow_status='Held'.
    """
    try:
        with db_engine.transaction() as tx:
            svc = tx.execute(
                "SELECT service_id, provider_id, title, price, status FROM services WHERE service_id = ?;",
                (service_id,), fetchone=True
            )
            if not svc:
                return -1 # Service not found
            if svc["status"] != 'Active':
                return -2 # Service not active
            if int(svc["provider_id"]) == int(client_id):
                return -4 # Cannot order own service

            provider_id = int(svc["provider_id"])
            price = float(svc["price"])
            
            # Centralized fee split calculation (10% platform, 90% provider)
            split = CommissionService.calculate_service_split(price)
            platform_fee = float(split["platform_fee"])
            provider_earnings = float(split["provider_earnings"])
            
            # 1. Insert Service Order with immutable provider snapshot
            order_id = tx.execute("""
            INSERT INTO service_orders (
                service_id, client_id, provider_id, requirements, amount, platform_fee,
                provider_earnings, status, escrow_status, due_date
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 'Pending', 'Held', ?);
            """, (service_id, client_id, provider_id, requirements, price, platform_fee, provider_earnings, due_date), fetch="lastrowid")

            # 2. Centralized Dual-Sided Escrow Hold
            FinancialService.hold_service_escrow(
                tx=tx,
                order_id=order_id,
                client_id=client_id,
                amount=price,
                service_title=svc["title"]
            )

            # 3. Notify provider
            tx.execute("""
            INSERT INTO notifications (user_id, title, message, type, is_read)
            VALUES (?, 'New Service Order Received!', ?, 'info', 0);
            """, (provider_id, f"A client booked your service '{svc['title']}' for GH₵ {price:.2f} (Due: {due_date})."))

            return order_id
    except Exception as e:
        print(f"Error creating service order for svc #{service_id}: {e}")
        return -3

def get_client_orders(client_id):
    """Returns all service orders placed by the client."""
    query = """
    SELECT o.order_id, o.service_id, s.title AS service_title, o.provider_id, u.name AS provider_name,
           o.requirements, o.amount, o.status, o.escrow_status, o.due_date, o.delivered_at, o.completed_at, o.created_at
    FROM service_orders o
    INNER JOIN services s ON o.service_id = s.service_id
    INNER JOIN users u ON o.provider_id = u.user_id
    WHERE o.client_id = ?
    ORDER BY o.created_at DESC;
    """
    return execute_query(query, (client_id,), fetch=True)

def get_provider_orders(provider_id):
    """Returns all service orders received by the provider."""
    query = """
    SELECT o.order_id, o.service_id, s.title AS service_title, o.client_id, u.name AS client_name,
           o.requirements, o.amount, o.platform_fee, o.provider_earnings, o.status, o.escrow_status,
           o.due_date, o.delivered_at, o.completed_at, o.created_at
    FROM service_orders o
    INNER JOIN services s ON o.service_id = s.service_id
    INNER JOIN users u ON o.client_id = u.user_id
    WHERE o.provider_id = ?
    ORDER BY o.created_at DESC;
    """
    return execute_query(query, (provider_id,), fetch=True)

def get_service_order_details(order_id, user_id):
    """Returns detailed order status asserting that caller is party to the order."""
    order = db_engine.execute_query("""
    SELECT o.order_id, o.service_id, s.title AS service_title, o.client_id, u_c.name AS client_name,
           u_c.email AS client_email, u_c.phone AS client_phone, o.provider_id, u_p.name AS provider_name,
           u_p.email AS provider_email, u_p.phone AS provider_phone, o.requirements, o.amount,
           o.platform_fee, o.provider_earnings, o.status, o.escrow_status, o.due_date, o.delivered_at,
           o.completed_at, o.created_at
    FROM service_orders o
    INNER JOIN services s ON o.service_id = s.service_id
    INNER JOIN users u_c ON o.client_id = u_c.user_id
    INNER JOIN users u_p ON o.provider_id = u_p.user_id
    WHERE o.order_id = ?;
    """, (order_id,), fetchone=True)
    
    if not order:
        return None
    if int(user_id) not in (int(order["client_id"]), int(order["provider_id"])) and user_id != 6: # Admin
        return -3 # Unauthorized
        
    return dict(order)

def accept_service_order(order_id, provider_id):
    """Provider formally accepts a pending service order."""
    try:
        with db_engine.transaction() as tx:
            order = tx.execute("SELECT provider_id, client_id, status FROM service_orders WHERE order_id = ?;", (order_id,), fetchone=True)
            if not order:
                return -1
            if int(order["provider_id"]) != int(provider_id):
                return -3 # Unauthorized
            if order["status"] != 'Pending':
                return -2 # Invalid state transition
                
            tx.execute("UPDATE service_orders SET status = 'Accepted' WHERE order_id = ?;", (order_id,))
            tx.execute("""
            INSERT INTO notifications (user_id, title, message, type, is_read)
            VALUES (?, 'Service Order Accepted', 'The provider accepted your order and will start work soon.', 'success', 0);
            """, (order["client_id"],))
        return 1
    except Exception as e:
        print(f"Error accepting order #{order_id}: {e}")
        return -4

def start_service_order(order_id, provider_id):
    """Provider marks order as In Progress."""
    try:
        with db_engine.transaction() as tx:
            order = tx.execute("SELECT provider_id, client_id, status FROM service_orders WHERE order_id = ?;", (order_id,), fetchone=True)
            if not order:
                return -1
            if int(order["provider_id"]) != int(provider_id):
                return -3 # Unauthorized
            if order["status"] not in ('Accepted', 'Pending'):
                return -2 # Invalid state
                
            tx.execute("UPDATE service_orders SET status = 'InProgress' WHERE order_id = ?;", (order_id,))
        return 1
    except Exception as e:
        print(f"Error starting order #{order_id}: {e}")
        return -4

def deliver_service_order(order_id, provider_id, delivery_notes=None):
    """Provider marks order as Delivered."""
    try:
        with db_engine.transaction() as tx:
            order = tx.execute("SELECT provider_id, client_id, status FROM service_orders WHERE order_id = ?;", (order_id,), fetchone=True)
            if not order:
                return -1
            if int(order["provider_id"]) != int(provider_id):
                return -3 # Unauthorized
            if order["status"] != 'InProgress':
                return -2 # Must be InProgress to deliver
                
            tx.execute("UPDATE service_orders SET status = 'Delivered', delivered_at = CURRENT_TIMESTAMP WHERE order_id = ?;", (order_id,))
            tx.execute("""
            INSERT INTO notifications (user_id, title, message, type, is_read)
            VALUES (?, 'Service Deliverables Submitted!', 'Your provider submitted the work. Please review and confirm completion.', 'info', 0);
            """, (order["client_id"],))
        return 1
    except Exception as e:
        print(f"Error delivering order #{order_id}: {e}")
        return -4

def complete_service_order(order_id, client_id):
    """
    Client confirms completion:
    - Transitions order status='Completed', escrow_status='Released'.
    - Atomically credits provider earnings to provider wallet via authoritative ledger (ServiceIncome, CREDIT).
    - Atomically credits platform fee to Admin wallet (PlatformCommission, CREDIT).
    """
    try:
        with db_engine.transaction() as tx:
            order = tx.execute("""
            SELECT order_id, client_id, provider_id, amount, platform_fee, provider_earnings, status, escrow_status
            FROM service_orders WHERE order_id = ?;
            """, (order_id,), fetchone=True)
            
            if not order:
                return -1
            if int(order["client_id"]) != int(client_id):
                return -3 # Unauthorized
            if order["status"] != 'Delivered' or order["escrow_status"] != 'Held':
                return -2 # Invalid state
                
            # 1. Update Order Status
            tx.execute("UPDATE service_orders SET status = 'Completed', escrow_status = 'Released', completed_at = CURRENT_TIMESTAMP WHERE order_id = ?;", (order_id,))
            
            provider_id = int(order["provider_id"])
            price = float(order["amount"])
            earnings = float(order["provider_earnings"])
            platform_fee = float(order["platform_fee"])
            
            # 2. Centralized Dual-Sided Escrow Release
            FinancialService.release_service_escrow(
                tx=tx,
                order_id=order_id,
                client_id=int(client_id),
                provider_id=provider_id,
                amount=price,
                platform_fee=platform_fee,
                provider_earnings=earnings
            )

            # 3. Notify provider
            tx.execute("""
            INSERT INTO notifications (user_id, title, message, type, is_read)
            VALUES (?, 'Service Order Completed & Earnings Released!', ?, 'success', 0);
            """, (provider_id, f"Client confirmed order #{order_id}. GH₵ {earnings:.2f} was credited to your wallet."))

        return 1
    except Exception as e:
        print(f"Error completing order #{order_id}: {e}")
        return -4

def cancel_service_order(order_id, user_id, reason="Order cancelled"):
    """
    Cancels service order and atomically refunds escrow to client.
    """
    try:
        with db_engine.transaction() as tx:
            order = tx.execute("""
            SELECT order_id, client_id, provider_id, amount, status, escrow_status
            FROM service_orders WHERE order_id = ?;
            """, (order_id,), fetchone=True)
            
            if not order:
                return -1
            if int(user_id) not in (int(order["client_id"]), int(order["provider_id"])) and int(user_id) != 6:
                return -3 # Unauthorized
            if order["status"] in ('Completed', 'Cancelled', 'Delivered'):
                return -2 # Cannot cancel delivered or completed orders
                
            amount = float(order["amount"])
            client_id = int(order["client_id"])
            
            # 1. Update Order Status
            tx.execute("UPDATE service_orders SET status = 'Cancelled', escrow_status = 'Refunded' WHERE order_id = ?;", (order_id,))
            
            # 2. Centralized Dual-Sided Escrow Refund
            FinancialService.refund_service_escrow(
                tx=tx,
                order_id=order_id,
                client_id=client_id,
                amount=amount,
                reason=reason
            )

            # 3. Notify parties
            other_uid = int(order["provider_id"]) if int(user_id) == client_id else client_id
            tx.execute("""
            INSERT INTO notifications (user_id, title, message, type, is_read)
            VALUES (?, 'Service Order Cancelled', ?, 'warning', 0);
            """, (other_uid, f"Order #{order_id} was cancelled. Reason: {reason}"))

        return 1
    except Exception as e:
        print(f"Error cancelling order #{order_id}: {e}")
        return -4

def submit_service_review(order_id, client_id, rating, comment):
    """
    Submits a review for a completed service order.
    Enforces verified client, completed status, and unique review per order.
    """
    try:
        order = db_engine.execute_query("""
        SELECT order_id, client_id, provider_id, status FROM service_orders WHERE order_id = ?;
        """, (order_id,), fetchone=True)
        
        if not order:
            return -1 # Order not found
        if int(order["client_id"]) != int(client_id):
            return -3 # Unauthorized
        if order["status"] != 'Completed':
            return -2 # Must be completed to review
            
        provider_id = int(order["provider_id"])
        
        # Check duplicate
        exists = db_engine.execute_query("SELECT review_id FROM service_reviews WHERE order_id = ?;", (order_id,), fetchone=True)
        if exists:
            return -4 # Duplicate review
            
        query = """
        INSERT INTO service_reviews (order_id, client_id, provider_id, rating, comment)
        VALUES (?, ?, ?, ?, ?);
        """
        rev_id = execute_query(query, (order_id, client_id, provider_id, int(rating), comment), fetch="lastrowid")
        return rev_id
    except Exception as e:
        print(f"Error submitting review for order #{order_id}: {e}")
        return -5

