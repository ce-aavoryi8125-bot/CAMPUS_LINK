import sqlite3
import os
import sys
from datetime import datetime

try:
    from database import database_schema as db_schema
except ImportError:
    import database_schema as db_schema

import db_engine

# Load commission rate from setting (mock config file)
COMMISSION_RATE = 0.10  # 10% commission

def execute_query(query, params=(), fetch=False, fetchone=False):
    """Utility to execute queries safely across MySQL and SQLite."""
    try:
        if fetch:
            res = db_engine.execute_query(query, params, fetch="all")
            return [tuple(r.values()) for r in res] if res else []
        elif fetchone:
            res = db_engine.execute_query(query, params, fetch="one")
            return tuple(res.values()) if res else None
        else:
            return db_engine.execute_query(query, params, fetch="rowcount")
    except Exception as e:
        print(f"Database Error: {e}")
        if fetch or fetchone:
            return None if fetchone else []
        return -1

import hashlib

def hash_password(password, salt="umat_campuslink_2026"):
    """
    Securely hashes password using PBKDF2-HMAC-SHA256 with 100,000 iterations.
    Format: pbkdf2_sha256$100000$salt$hash_hex
    """
    key = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt.encode('utf-8'),
        100000
    )
    return f"pbkdf2_sha256$100000${salt}${key.hex()}"

def verify_password(password, stored_hash):
    """
    Verifies a raw password against a stored PBKDF2 hash string or legacy hash.
    """
    if not stored_hash:
        return False
    parts = stored_hash.split('$')
    if len(parts) == 4 and parts[0] == 'pbkdf2_sha256':
        iterations = int(parts[1])
        salt = parts[2]
        expected_hex = parts[3]
        key = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('utf-8'), iterations)
        return key.hex() == expected_hex
    return stored_hash == hashlib.sha256(password.encode('utf-8')).hexdigest() or stored_hash == password

# --- USER FUNCTIONS ---

def authenticate_user(email, password):
    """
    Validates user credentials against password hash and checks account_status.
    Returns (user_id, name, email, verification_level, department, hostel, account_status) on success,
    -1 for invalid email/password, or -2 for suspended account.
    """
    user = execute_query(
        "SELECT user_id, name, email, verification_level, department, hostel, account_status, password_hash FROM users WHERE email = ?;",
        (email,), fetchone=True
    )
    if not user:
        return -1 # User not found
    
    if not verify_password(password, user[7]):
        return -1 # Invalid password
        
    if user[6] == 'Suspended':
        return -2 # Suspended account
        
    # Update last login timestamp
    execute_query("UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE user_id = ?;", (user[0],))
    
    return {
        'user_id': user[0],
        'name': user[1],
        'email': user[2],
        'verification_level': user[3],
        'department': user[4],
        'hostel': user[5],
        'account_status': user[6]
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
    user = execute_query("SELECT password_hash FROM users WHERE user_id = ?;", (user_id,), fetchone=True)
    if not user or not verify_password(old_password, user[0]):
        return -1 # Invalid old password
    new_hash = hash_password(new_password)
    return execute_query("UPDATE users SET password_hash = ? WHERE user_id = ?;", (new_hash, user_id))

# --- CATEGORY FUNCTIONS ---

def get_categories():
    return execute_query("SELECT category_id, name, description FROM categories ORDER BY name;", fetch=True)

# --- LISTINGS FUNCTIONS ---

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
        
    # Date range filters (Availability Calendar Checks)
    if req_start and req_end:
        query += " AND l.available_from <= ? AND l.available_until >= ?"
        params.extend([req_start, req_end])
        
        # Subquery: Exclude any listing which has an overlapping approved transaction
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

# --- RENTAL REQUESTS ---

def submit_rental_request(listing_id, borrower_id, start_date, end_date, purpose, notes):
    query = """
    INSERT INTO rental_requests (listing_id, borrower_id, rent_start_date, rent_end_date, rental_purpose, status, notes)
    VALUES (?, ?, ?, ?, ?, 'Pending', ?);
    """
    return execute_query(query, (listing_id, borrower_id, start_date, end_date, purpose, notes))

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
    Approves request, sets listing status to 'Reserved',
    and spawns a Transaction record.
    """
    conn = db_schema.get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT listing_id, borrower_id, rent_start_date, rent_end_date, rental_purpose FROM rental_requests WHERE request_id = ?;", (request_id,))
        req = cursor.fetchone()
        if not req:
            return -1
            
        listing_id, borrower_id, start_date, end_date, purpose = req
        
        # Verify listing exists
        cursor.execute("SELECT rental_rate_per_day, deposit_amount, status FROM listings WHERE listing_id = ?;", (listing_id,))
        lst = cursor.fetchone()
        if not lst or lst[2] == 'Delisted':
            return -2  # Listing not available
            
        rate, deposit = lst[0], lst[1]
        
        # Calculate days and amounts
        d1 = datetime.strptime(start_date, "%Y-%m-%d")
        d2 = datetime.strptime(end_date, "%Y-%m-%d")
        total_days = max((d2 - d1).days + 1, 1)
        gross_amount = rate * total_days
        commission = gross_amount * COMMISSION_RATE
        earnings = gross_amount - commission
        
        # Start transaction modifications
        cursor.execute("UPDATE rental_requests SET status = 'Approved' WHERE request_id = ?;", (request_id,))
        cursor.execute("UPDATE listings SET status = 'Reserved' WHERE listing_id = ?;", (listing_id,))
        
        # Check if transaction already created
        cursor.execute("SELECT transaction_id FROM rental_transactions WHERE request_id = ?;", (request_id,))
        tx_exists = cursor.fetchone()
        if not tx_exists:
            cursor.execute("""
            INSERT INTO rental_transactions (
                request_id, listing_id, borrower_id, rent_start_date, rent_end_date, total_days,
                gross_amount, commission_amount, owner_earnings, deposit_held, payment_status, rental_status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'Paid', 'Active');
            """, (request_id, listing_id, borrower_id, start_date, end_date, total_days, gross_amount, commission, earnings, deposit))
        
        # Reject any other overlapping pending requests for this listing
        cursor.execute("""
        UPDATE rental_requests 
        SET status = 'Rejected', notes = 'Another request was approved for overlapping dates.'
        WHERE listing_id = ? AND status = 'Pending' AND request_id != ?
        AND NOT (rent_end_date < ? OR rent_start_date > ?);
        """, (listing_id, request_id, start_date, end_date))
        
        conn.commit()
        return 1
    except sqlite3.Error as e:
        print(f"Error approving: {e}")
        conn.rollback()
        return -3
    finally:
        conn.close()

def reject_request(request_id, notes="Declined by owner."):
    return execute_query("UPDATE rental_requests SET status = 'Rejected', notes = ? WHERE request_id = ?;", (notes, request_id))

def cancel_request(request_id):
    return execute_query("UPDATE rental_requests SET status = 'Cancelled' WHERE request_id = ?;", (request_id,))

# --- RENTAL TRANSACTIONS & RETURNS ---

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
    Processes the return of an item.
    - Updates transaction actual_return_date and status to 'Returned'.
    - Updates listing status based on damage condition (if severe ➔ Maintenance).
    - Calculates final deposit refund.
    - If there are damages, spawns a maintenance ticket.
    """
    conn = db_schema.get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT listing_id, borrower_id, deposit_held FROM rental_transactions WHERE transaction_id = ?;", (transaction_id,))
        tx = cursor.fetchone()
        if not tx:
            return -1
            
        listing_id, borrower_id, deposit = tx
        today_str = datetime.now().strftime("%Y-%m-%d")
        
        # 1. Update Transaction
        cursor.execute("""
        UPDATE rental_transactions 
        SET actual_return_date = ?, rental_status = 'Returned', return_notes = ?
        WHERE transaction_id = ?;
        """, (today_str, return_notes, transaction_id))
        
        # 2. Update Listing Status and handle deposit / maintenance
        if damage_condition == 'Good':
            cursor.execute("UPDATE listings SET status = 'Available' WHERE listing_id = ?;", (listing_id,))
        elif damage_condition == 'Minor':
            cursor.execute("UPDATE listings SET status = 'Maintenance' WHERE listing_id = ?;", (listing_id,))
            # Create maintenance record
            cursor.execute("""
            INSERT INTO maintenance (listing_id, reported_by, issue_description, cost, status, start_date)
            VALUES (?, ?, ?, ?, 'Pending', ?);
            """, (listing_id, borrower_id, f"Minor damage logged upon return. Return notes: {return_notes}", claim_amount, today_str))
        else: # Severe damage
            cursor.execute("UPDATE listings SET status = 'Maintenance' WHERE listing_id = ?;", (listing_id,))
            # Create maintenance record (costs full deposit or more)
            cursor.execute("""
            INSERT INTO maintenance (listing_id, reported_by, issue_description, cost, status, start_date)
            VALUES (?, ?, ?, ?, 'In Progress', ?);
            """, (listing_id, borrower_id, f"SEVERE damage logged upon return. Return notes: {return_notes}", deposit, today_str))
            
        conn.commit()
        return 1
    except sqlite3.Error as e:
        print(f"Error processing return: {e}")
        conn.rollback()
        return -2
    finally:
        conn.close()

# --- PEER REVIEWS ---

def submit_review(transaction_id, reviewer_id, reviewee_id, reviewee_type, rating, comment):
    # Verify if a review already exists from this reviewer for this transaction
    exists = execute_query("""
    SELECT count(*) FROM reviews 
    WHERE transaction_id = ? AND reviewer_id = ? AND reviewee_type = ?;
    """, (transaction_id, reviewer_id, reviewee_type), fetchone=True)
    
    if exists and exists[0] > 0:
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

# --- WISHLIST & SAVES ---

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

# --- MAINTENANCE RECORDS ---

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
    conn = db_schema.get_db_connection()
    cursor = conn.cursor()
    try:
        today_str = datetime.now().strftime("%Y-%m-%d") if status == 'Completed' else None
        
        # Update maintenance log
        if status == 'Completed':
            cursor.execute("UPDATE maintenance SET cost = ?, status = ?, end_date = ? WHERE maintenance_id = ?;", (cost, status, today_str, maintenance_id))
            # Restore listing to Available
            cursor.execute("UPDATE listings SET status = 'Available' WHERE listing_id = ?;", (listing_id,))
        else:
            cursor.execute("UPDATE maintenance SET cost = ?, status = ? WHERE maintenance_id = ?;", (cost, status, maintenance_id))
            
        conn.commit()
        return 1
    except sqlite3.Error as e:
        print(f"Error updating maintenance: {e}")
        conn.rollback()
        return -1
    finally:
        conn.close()

# --- ANALYTICS / DERIVED METRICS ---

def calculate_trust_score(user_id):
    """
    Derives trust score in Python based on rating averages, total rentals, and late returns.
    Formula: Base (50) + (Avg Rating * 8) + (Completed Rentals * 0.5) - (Late Returns * 5)
    Capped [0, 100]. Returns dict with score and components.
    """
    conn = db_schema.get_db_connection()
    cursor = conn.cursor()
    
    # 1. Avg Rating received as both borrower and lender
    cursor.execute("SELECT AVG(rating), COUNT(review_id) FROM reviews WHERE reviewee_id = ?;", (user_id,))
    res_rating = cursor.fetchone()
    avg_rating = res_rating[0] if res_rating[0] is not None else 5.0
    rating_count = res_rating[1]
    
    # 2. Completed rentals as borrower
    cursor.execute("SELECT COUNT(transaction_id) FROM rental_transactions WHERE borrower_id = ? AND rental_status = 'Returned';", (user_id,))
    completed_borrowed = cursor.fetchone()[0]
    
    # 3. Completed rentals as lender
    cursor.execute("""
    SELECT COUNT(t.transaction_id) 
    FROM rental_transactions t
    INNER JOIN listings l ON t.listing_id = l.listing_id
    WHERE l.owner_id = ? AND t.rental_status = 'Returned';
    """, (user_id,))
    completed_lent = cursor.fetchone()[0]
    
    total_completed = completed_borrowed + completed_lent
    
    # 4. Late returns as borrower (actual_return_date > rent_end_date)
    cursor.execute("""
    SELECT COUNT(transaction_id) FROM rental_transactions 
    WHERE borrower_id = ? AND actual_return_date > rent_end_date;
    """, (user_id,))
    late_returns = cursor.fetchone()[0]
    
    conn.close()
    
    # Calculate Score
    score = 50 + (avg_rating * 8) + (total_completed * 0.5) - (late_returns * 5)
    score = max(0, min(100, int(score)))
    
    return {
        "score": score,
        "avg_rating": round(avg_rating, 1),
        "total_rentals": total_completed,
        "late_returns": late_returns,
        "rating_count": rating_count
    }

# --- REPORTS DATA RETRIEVAL ---

def get_report_data(report_index):
    """
    Executes one of the 15 requested Business Intelligence Reports.
    Returns: (list_of_column_headers, list_of_rows)
    """
    conn = db_schema.get_db_connection()
    cursor = conn.cursor()
    
    headers = []
    rows = []
    
    try:
        if report_index == 1:
            # 1. Platform Revenue Summary
            headers = ["Total Transactions", "Total Gross volume (GH₵)", "Platform Commissions (GH₵)", "Lenders Net Earnings (GH₵)"]
            cursor.execute("""
            SELECT COUNT(transaction_id), SUM(gross_amount), SUM(commission_amount), SUM(owner_earnings)
            FROM rental_transactions WHERE payment_status = 'Paid';
            """)
            rows = cursor.fetchall()
            
        elif report_index == 2:
            # 2. Highest Earning Owners
            headers = ["Lender Name", "Department", "Hostel", "Items Listed", "Total Net Earnings (GH₵)"]
            cursor.execute("""
            SELECT u.name, u.department, u.hostel, COUNT(DISTINCT l.listing_id), SUM(t.owner_earnings)
            FROM users u
            INNER JOIN listings l ON u.user_id = l.owner_id
            INNER JOIN rental_transactions t ON l.listing_id = t.listing_id
            GROUP BY u.user_id
            ORDER BY SUM(t.owner_earnings) DESC;
            """)
            rows = cursor.fetchall()
            
        elif report_index == 3:
            # 3. Highest Spending Borrowers
            headers = ["Borrower Name", "Department", "Hostel", "Total Rentals", "Total Amount Spent (GH₵)"]
            cursor.execute("""
            SELECT u.name, u.department, u.hostel, COUNT(t.transaction_id), SUM(t.gross_amount)
            FROM users u
            INNER JOIN rental_transactions t ON u.user_id = t.borrower_id
            GROUP BY u.user_id
            ORDER BY SUM(t.gross_amount) DESC;
            """)
            rows = cursor.fetchall()
            
        elif report_index == 4:
            # 4. Most Popular Listing Categories
            headers = ["Category Name", "Total Listed Assets", "Total Rentals Generated", "Gross Volume Generated (GH₵)"]
            cursor.execute("""
            SELECT c.name, COUNT(DISTINCT l.listing_id), COUNT(t.transaction_id), SUM(t.gross_amount)
            FROM categories c
            LEFT JOIN listings l ON c.category_id = l.category_id
            LEFT JOIN rental_transactions t ON l.listing_id = t.listing_id
            GROUP BY c.category_id
            ORDER BY COUNT(t.transaction_id) DESC;
            """)
            rows = cursor.fetchall()
            
        elif report_index == 5:
            # 5. Most Borrowed Listings
            headers = ["Listing Title", "Category", "Brand", "Model", "Owner", "Daily Rate (GH₵)", "Total Rentals"]
            cursor.execute("""
            SELECT l.title, c.name, l.brand, l.model, u.name, l.rental_rate_per_day, COUNT(t.transaction_id)
            FROM listings l
            INNER JOIN categories c ON l.category_id = c.category_id
            INNER JOIN users u ON l.owner_id = u.user_id
            INNER JOIN rental_transactions t ON l.listing_id = t.listing_id
            GROUP BY l.listing_id
            ORDER BY COUNT(t.transaction_id) DESC;
            """)
            rows = cursor.fetchall()
            
        elif report_index == 6:
            # 6. Listings Never Borrowed (LEFT JOIN with NULL checks)
            headers = ["Listing Title", "Category", "Brand", "Model", "Owner", "Daily Rate (GH₵)", "Date Created"]
            cursor.execute("""
            SELECT l.title, c.name, l.brand, l.model, u.name, l.rental_rate_per_day, l.created_at
            FROM listings l
            INNER JOIN categories c ON l.category_id = c.category_id
            INNER JOIN users u ON l.owner_id = u.user_id
            LEFT JOIN rental_transactions t ON l.listing_id = t.listing_id
            WHERE t.transaction_id IS NULL;
            """)
            rows = cursor.fetchall()
            
        elif report_index == 7:
            # 7. Current Overdue Rentals
            headers = ["Renter Name", "Listing Title", "Owner Name", "Rent End Date", "Days Overdue", "Held Deposit (GH₵)"]
            # Filter active rentals where today is greater than rent_end_date
            today_str = datetime.now().strftime("%Y-%m-%d")
            cursor.execute("""
            SELECT u_b.name, l.title, u_o.name, t.rent_end_date,
                   (strftime('%s', ?) - strftime('%s', t.rent_end_date)) / 86400 AS days_overdue,
                   t.deposit_held
            FROM rental_transactions t
            INNER JOIN listings l ON t.listing_id = l.listing_id
            INNER JOIN users u_b ON t.borrower_id = u_b.user_id
            INNER JOIN users u_o ON l.owner_id = u_o.user_id
            WHERE t.rental_status = 'Active' AND t.rent_end_date < ?;
            """, (today_str, today_str))
            rows = cursor.fetchall()
            
        elif report_index == 8:
            # 8. Maintenance & Damage Cost Summary
            headers = ["Listing Title", "Brand", "Model", "Damage Issue", "Total Repair Costs (GH₵)", "Repair Status", "Logged Date"]
            cursor.execute("""
            SELECT l.title, l.brand, l.model, m.issue_description, m.cost, m.status, m.start_date
            FROM maintenance m
            INNER JOIN listings l ON m.listing_id = l.listing_id
            ORDER BY m.cost DESC;
            """)
            rows = cursor.fetchall()
            
        elif report_index == 9:
            # 9. Most Common Rental Purpose
            headers = ["Rental Purpose", "Rental Request Count", "Gross Value Supported (GH₵)"]
            cursor.execute("""
            SELECT r.rental_purpose, COUNT(r.request_id), SUM(t.gross_amount)
            FROM rental_requests r
            LEFT JOIN rental_transactions t ON r.request_id = t.request_id
            GROUP BY r.rental_purpose
            ORDER BY COUNT(r.request_id) DESC;
            """)
            rows = cursor.fetchall()
            
        elif report_index == 10:
            # 10. Average Rental Duration
            headers = ["Category Name", "Average Rental Period (Days)", "Max Period (Days)"]
            cursor.execute("""
            SELECT c.name, AVG(t.total_days), MAX(t.total_days)
            FROM categories c
            INNER JOIN listings l ON c.category_id = l.category_id
            INNER JOIN rental_transactions t ON l.listing_id = t.listing_id
            GROUP BY c.category_id;
            """)
            rows = cursor.fetchall()
            
        elif report_index == 11:
            # 11. Average Review Rating (Owners)
            headers = ["Lender Name", "Avg Star Rating", "Reviews Received", "Hostel"]
            cursor.execute("""
            SELECT u.name, AVG(r.rating), COUNT(r.review_id), u.hostel
            FROM users u
            INNER JOIN reviews r ON u.user_id = r.reviewee_id
            WHERE r.reviewee_type = 'Lender'
            GROUP BY u.user_id
            ORDER BY AVG(r.rating) DESC;
            """)
            rows = cursor.fetchall()
            
        elif report_index == 12:
            # 12. Average Review Rating (Borrowers)
            headers = ["Borrower Name", "Avg Star Rating", "Reviews Received", "Department"]
            cursor.execute("""
            SELECT u.name, AVG(r.rating), COUNT(r.review_id), u.department
            FROM users u
            INNER JOIN reviews r ON u.user_id = r.reviewee_id
            WHERE r.reviewee_type = 'Borrower'
            GROUP BY u.user_id
            ORDER BY AVG(r.rating) DESC;
            """)
            rows = cursor.fetchall()
            
        elif report_index == 13:
            # 13. Active Listings Count by Hostel
            headers = ["Hostel Name", "Active Assets Available", "Most Listed Category"]
            cursor.execute("""
            SELECT u.hostel, COUNT(l.listing_id), c.name
            FROM users u
            INNER JOIN listings l ON u.user_id = l.owner_id
            INNER JOIN categories c ON l.category_id = c.category_id
            WHERE l.status = 'Available'
            GROUP BY u.hostel
            ORDER BY COUNT(l.listing_id) DESC;
            """)
            rows = cursor.fetchall()
            
        elif report_index == 14:
            # 14. Monthly Revenue & Transaction Trend
            headers = ["Year-Month", "Total Rentals Completed", "Total gross Volume (GH₵)", "Platform Commissions (GH₵)"]
            cursor.execute("""
            SELECT strftime('%Y-%m', created_at) AS ym, COUNT(transaction_id), SUM(gross_amount), SUM(commission_amount)
            FROM rental_transactions
            GROUP BY ym
            ORDER BY ym DESC;
            """)
            rows = cursor.fetchall()
            
        elif report_index == 15:
            # 15. Frequently Late Borrowers
            headers = ["Borrower Name", "Department", "Hostel", "Late Return Incidents"]
            cursor.execute("""
            SELECT u.name, u.department, u.hostel, COUNT(t.transaction_id)
            FROM users u
            INNER JOIN rental_transactions t ON u.user_id = t.borrower_id
            WHERE t.actual_return_date > t.rent_end_date
            GROUP BY u.user_id
            ORDER BY COUNT(t.transaction_id) DESC;
            """)
            rows = cursor.fetchall()
            
    except sqlite3.Error as e:
        print(f"Report execution failed: {e}")
    finally:
        conn.close()
        
    return headers, rows

def get_intelligence_report(report_index):
    headers, rows = get_report_data(report_index)
    return {"headers": headers, "data": rows}

approve_rental_request = approve_request
get_owner_rental_requests = get_incoming_requests
get_borrower_transactions = get_my_borrowed_items
get_all_maintenance_records = get_maintenance_records

def update_maintenance_status(maintenance_id, status, listing_id, cost=0.0):
    return update_maintenance(maintenance_id, cost, status, listing_id)

def process_item_return(transaction_id, actual_return_date=None, is_damaged=False, cost=0.0, notes=""):
    damage_cond = "Damaged" if is_damaged else "Good"
    return process_return(transaction_id, notes, damage_cond, claim_amount=cost)




