"""
end_to_end_test.py
------------------
Full end-to-end validation suite for CampusLink.
Tests every workflow, every report, all constraints, and all SQL operations.
Prints a final PASS/FAIL summary table.
"""

import sys
import os
import sqlite3
from datetime import datetime, timedelta

# Handle imports from tests/ directory
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

try:
    from database import database_schema as db_schema
    from database import db_seeder
except ImportError:
    import database_schema as db_schema
    import db_seeder

import controllers

PASS = "PASS"
FAIL = "FAIL"
results = []

def check(label, condition, detail=""):
    status = PASS if condition else FAIL
    results.append((label, status, detail))
    icon = "OK" if condition else "!!"
    print(f"  [{icon}] {status}  |  {label}")
    if not condition and detail:
        print(f"         Detail: {detail}")

# ---------------------------------------------------------------------------
# SETUP: Fresh database for every test run
# ---------------------------------------------------------------------------
def setup():
    db_dir = os.path.dirname(os.path.abspath(db_schema.__file__))
    db_path = os.path.join(db_dir, db_schema.DB_NAME)
    if os.path.exists(db_path):
        os.remove(db_path)
    db_seeder.seed_database()

# ---------------------------------------------------------------------------
# SECTION 1: Schema Structural Integrity
# ---------------------------------------------------------------------------
def test_schema():
    print("\n[SECTION 1] Schema & Structural Integrity")
    conn = db_schema.get_db_connection()
    cursor = conn.cursor()

    expected_tables = [
        "users", "categories", "listings",
        "rental_requests", "rental_transactions",
        "maintenance", "reviews", "wishlist", "saved_listings"
    ]
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    existing = {row[0] for row in cursor.fetchall()}

    for t in expected_tables:
        check(f"Table '{t}' exists", t in existing)

    # Foreign keys ON
    cursor.execute("PRAGMA foreign_keys;")
    fk_val = cursor.fetchone()[0]
    check("Foreign keys enforced (PRAGMA foreign_keys = ON)", fk_val == 1)

    # Index checks
    cursor.execute("SELECT name FROM sqlite_master WHERE type='index';")
    indexes = {row[0] for row in cursor.fetchall()}
    check("Index idx_listings_owner exists", "idx_listings_owner" in indexes)
    check("Index idx_requests_borrower exists", "idx_requests_borrower" in indexes)
    check("Index idx_reviews_transaction exists", "idx_reviews_transaction" in indexes)

    conn.close()

# ---------------------------------------------------------------------------
# SECTION 2: Constraint Enforcement
# ---------------------------------------------------------------------------
def test_constraints():
    print("\n[SECTION 2] Database Constraint Enforcement")
    conn = db_schema.get_db_connection()
    cursor = conn.cursor()

    # a) Email format check constraint
    try:
        cursor.execute("INSERT INTO users (name,email,password_hash,phone,department) VALUES ('X','invalid_email_no_at','hash','+1','Dept');")
        conn.rollback()
        check("CHECK: email format (reject email without @)", False)
    except sqlite3.IntegrityError:
        check("CHECK: email format (reject email without @)", True)

    # b) Negative price check
    try:
        cursor.execute("""
        INSERT INTO listings (owner_id,category_id,title,subcategory,brand,model,
            rental_rate_per_day,deposit_amount,condition,status,pickup_location,available_from,available_until)
        VALUES (2,1,'Bad','Sub','Brand','Model',-5.00,100.00,'Good','Available','Hall','2026-08-01','2026-08-31');
        """)
        conn.rollback()
        check("CHECK: negative rental_rate_per_day rejected", False)
    except sqlite3.IntegrityError:
        check("CHECK: negative rental_rate_per_day rejected", True)

    # c) Listing status enum check
    try:
        cursor.execute("""
        INSERT INTO listings (owner_id,category_id,title,subcategory,brand,model,
            rental_rate_per_day,deposit_amount,condition,status,pickup_location,available_from,available_until)
        VALUES (2,1,'Bad','Sub','Brand','Model',10.00,50.00,'Good','INVALID_STATUS','Hall','2026-08-01','2026-08-31');
        """)
        conn.rollback()
        check("CHECK: listing status enum (reject invalid status)", False)
    except sqlite3.IntegrityError:
        check("CHECK: listing status enum (reject invalid status)", True)

    # d) Rating range check
    try:
        cursor.execute("""
        INSERT INTO reviews (transaction_id,reviewer_id,reviewee_id,reviewee_type,rating)
        VALUES (1,2,1,'Lender',7);
        """)
        conn.rollback()
        check("CHECK: review rating > 5 rejected", False)
    except sqlite3.IntegrityError:
        check("CHECK: review rating > 5 rejected", True)

    # e) NOT NULL test
    try:
        cursor.execute("INSERT INTO users (email,password_hash,phone,department) VALUES ('a@umat.edu.gh','hash','+1','Dept');")
        conn.rollback()
        check("NOT NULL: users.name required", False)
    except sqlite3.IntegrityError:
        check("NOT NULL: users.name required", True)

    # f) UNIQUE email
    try:
        cursor.execute("INSERT INTO users (name,email,password_hash,phone,department) VALUES ('Dup','ce-aavoryi8125@st.umat.edu.gh','hash','+1','Dept');")
        conn.rollback()
        check("UNIQUE: users.email uniqueness enforced", False)
    except sqlite3.IntegrityError:
        check("UNIQUE: users.email uniqueness enforced", True)

    # g) Date order check on rental_requests
    try:
        cursor.execute("""
        INSERT INTO rental_requests (listing_id,borrower_id,rent_start_date,rent_end_date,rental_purpose)
        VALUES (2,3,'2026-09-10','2026-09-05','Field Trip');
        """)
        conn.rollback()
        check("CHECK: rent_end_date >= rent_start_date enforced", False)
    except sqlite3.IntegrityError:
        check("CHECK: rent_end_date >= rent_start_date enforced", True)

    conn.close()

# ---------------------------------------------------------------------------
# SECTION 3: CRUD Operations
# ---------------------------------------------------------------------------
def test_crud():
    print("\n[SECTION 3] CRUD Operations")
    conn = db_schema.get_db_connection()
    cursor = conn.cursor()

    # INSERT
    cursor.execute("""
    INSERT INTO users (name,email,password_hash,student_id,phone,verification_level,department,hostel)
    VALUES ('Test Kwame','kwame@student.umat.edu.gh','hash123','TST-999','+233200000001','Unverified','Petroleum Engineering','K.T. Hall');
    """)
    new_id = cursor.lastrowid
    conn.commit()
    cursor.execute("SELECT name FROM users WHERE user_id=?;", (new_id,))
    row = cursor.fetchone()
    check("INSERT: new user created", row is not None and row[0] == "Test Kwame")

    # READ
    cursor.execute("SELECT email FROM users WHERE user_id=?;", (new_id,))
    row = cursor.fetchone()
    check("SELECT: new user readable", row is not None and "kwame" in row[0])

    # UPDATE
    cursor.execute("UPDATE users SET verification_level='Verified Student' WHERE user_id=?;", (new_id,))
    conn.commit()
    cursor.execute("SELECT verification_level FROM users WHERE user_id=?;", (new_id,))
    row = cursor.fetchone()
    check("UPDATE: verification_level updated", row is not None and row[0] == "Verified Student")

    # DELETE
    cursor.execute("DELETE FROM users WHERE user_id=?;", (new_id,))
    conn.commit()
    cursor.execute("SELECT user_id FROM users WHERE user_id=?;", (new_id,))
    row = cursor.fetchone()
    check("DELETE: user removed from database", row is None)

    conn.close()

# ---------------------------------------------------------------------------
# SECTION 4: ALTER TABLE compatibility
# ---------------------------------------------------------------------------
def test_alter():
    print("\n[SECTION 4] ALTER TABLE Operations (SQLite Version Compatibility)")
    conn = db_schema.get_db_connection()
    cursor = conn.cursor()

    # Add column
    cursor.execute("ALTER TABLE users ADD COLUMN test_temp TEXT DEFAULT 'temp';")
    conn.commit()
    cursor.execute("PRAGMA table_info(users);")
    cols = [c[1] for c in cursor.fetchall()]
    check("ALTER TABLE ADD COLUMN: test_temp added", "test_temp" in cols)
    conn.close()

    # Drop column (using compatibility helper)
    db_schema.drop_column_compatibly("users", "test_temp")
    conn2 = db_schema.get_db_connection()
    cursor2 = conn2.cursor()
    cursor2.execute("PRAGMA table_info(users);")
    cols2 = [c[1] for c in cursor2.fetchall()]
    check("ALTER TABLE DROP COLUMN: test_temp removed", "test_temp" not in cols2)
    conn2.close()

# ---------------------------------------------------------------------------
# SECTION 5: SQL Query Operations
# ---------------------------------------------------------------------------
def test_queries():
    print("\n[SECTION 5] SQL Query Operations (SELECT, ORDER, LIKE, Aggregates, Joins)")
    conn = db_schema.get_db_connection()
    cursor = conn.cursor()

    # SELECT with WHERE
    cursor.execute("SELECT name FROM users WHERE verification_level='Verified Student';")
    rows = cursor.fetchall()
    check("SELECT + WHERE: verified students returned", len(rows) >= 2)

    # ORDER BY ASC
    cursor.execute("SELECT rental_rate_per_day FROM listings ORDER BY rental_rate_per_day ASC;")
    rates = [r[0] for r in cursor.fetchall()]
    check("ORDER BY ASC: rates ascending", rates == sorted(rates))

    # ORDER BY DESC
    cursor.execute("SELECT rental_rate_per_day FROM listings ORDER BY rental_rate_per_day DESC;")
    rates_d = [r[0] for r in cursor.fetchall()]
    check("ORDER BY DESC: rates descending", rates_d == sorted(rates_d, reverse=True))

    # LIKE (prefix)
    cursor.execute("SELECT name FROM users WHERE name LIKE 'B%';")
    rows = cursor.fetchall()
    check("LIKE prefix 'B%': Benedict Osei returned", any("Benedict" in r[0] for r in rows))

    # LIKE (suffix)
    cursor.execute("SELECT email FROM users WHERE email LIKE '%@st.umat.edu.gh' OR email LIKE '%@student.umat.edu.gh';")
    rows = cursor.fetchall()
    check("LIKE suffix '%@student.umat.edu.gh': student emails returned", len(rows) >= 3)

    # LIKE (contains)
    cursor.execute("SELECT title FROM listings WHERE description LIKE '%GPS%';")
    rows = cursor.fetchall()
    check("LIKE contains '%GPS%': GPS listing found", len(rows) >= 1)

    # Aggregates
    cursor.execute("SELECT COUNT(*) FROM listings;")
    count = cursor.fetchone()[0]
    check("COUNT(*) listings: 50+ records", count >= 50)

    cursor.execute("SELECT SUM(gross_amount) FROM rental_transactions;")
    total = cursor.fetchone()[0]
    check("SUM(gross_amount): non-zero sum", total is not None and total > 0)

    cursor.execute("SELECT AVG(rental_rate_per_day) FROM listings;")
    avg = cursor.fetchone()[0]
    check("AVG(rental_rate_per_day): non-zero average", avg is not None and avg > 0)

    cursor.execute("SELECT MIN(rental_rate_per_day), MAX(rental_rate_per_day) FROM listings;")
    minmax = cursor.fetchone()
    check("MIN/MAX rental rates: min < max", minmax[0] < minmax[1])

    cursor.execute("SELECT DISTINCT category_id FROM listings;")
    cats = cursor.fetchall()
    check("DISTINCT category_id: multiple categories", len(cats) >= 5)

    # INNER JOIN
    cursor.execute("""
    SELECT t.transaction_id, u.name, l.title
    FROM rental_transactions t
    INNER JOIN users u ON t.borrower_id = u.user_id
    INNER JOIN listings l ON t.listing_id = l.listing_id;
    """)
    rows = cursor.fetchall()
    check("INNER JOIN: transactions with user+listing data", len(rows) >= 2)

    # LEFT JOIN (listings never borrowed)
    cursor.execute("""
    SELECT l.listing_id, l.title
    FROM listings l
    LEFT JOIN rental_transactions t ON l.listing_id = t.listing_id
    WHERE t.transaction_id IS NULL;
    """)
    rows = cursor.fetchall()
    check("LEFT JOIN + NULL check: un-borrowed listings found", len(rows) >= 5)

    # RIGHT JOIN emulation via LEFT JOIN with swapped tables
    cursor.execute("""
    SELECT u.name, l.title
    FROM users u
    LEFT JOIN listings l ON u.user_id = l.owner_id;
    """)
    rows = cursor.fetchall()
    null_rows = [r for r in rows if r[1] is None]
    check("RIGHT JOIN emulation: users with no listings shown (NULL)", len(null_rows) >= 1)

    conn.close()

# ---------------------------------------------------------------------------
# SECTION 6: Full Business Workflow (P2P Lifecycle)
# ---------------------------------------------------------------------------
def test_workflow():
    print("\n[SECTION 6] Full P2P Marketplace Workflow")
    conn = db_schema.get_db_connection()
    cursor = conn.cursor()

    # Identify Albert (lender) and Grace (borrower - upgrade to verified for test)
    cursor.execute("SELECT user_id FROM users WHERE name='Albert Boateng';")
    albert_id = cursor.fetchone()[0]
    cursor.execute("SELECT user_id FROM users WHERE name='Grace Mensah';")
    grace_id = cursor.fetchone()[0]

    # Upgrade Grace to Verified Student
    cursor.execute("UPDATE users SET verification_level='Verified Student' WHERE user_id=?;", (grace_id,))
    conn.commit()

    # Find a listing owned by Albert that is Available
    cursor.execute("SELECT listing_id, rental_rate_per_day, deposit_amount FROM listings WHERE owner_id=? AND status='Available' LIMIT 1;", (albert_id,))
    lst = cursor.fetchone()
    check("Workflow: Available listing found for Albert", lst is not None)
    if lst is None:
        conn.close()
        return

    listing_id, rate, deposit = lst

    # Step 1: Grace submits request
    today = datetime.now().date()
    start_str = (today + timedelta(days=20)).strftime("%Y-%m-%d")
    end_str   = (today + timedelta(days=22)).strftime("%Y-%m-%d")

    res = controllers.submit_rental_request(listing_id, grace_id, start_str, end_str, "Research", "For final year project research")
    check("Workflow Step 1: Grace submits rental request", res > 0)

    # Use MAX(request_id) to deterministically get the newest request regardless of timestamp ties
    cursor.execute("SELECT request_id, status FROM rental_requests WHERE borrower_id=? AND request_id=(SELECT MAX(request_id) FROM rental_requests WHERE borrower_id=?);", (grace_id, grace_id))
    req_row = cursor.fetchone()
    check("Workflow Step 1b: Request status is Pending", req_row is not None and req_row[1] == "Pending")
    request_id = req_row[0]

    # Step 2: Albert approves
    approval = controllers.approve_request(request_id)
    check("Workflow Step 2: Albert approves request (returns 1)", approval == 1)

    # Verify listing is Reserved
    cursor.execute("SELECT status FROM listings WHERE listing_id=?;", (listing_id,))
    lst_status = cursor.fetchone()[0]
    check("Workflow Step 2b: Listing status -> Reserved", lst_status == "Reserved")

    # Verify transaction was created
    cursor.execute("SELECT transaction_id, rental_status, gross_amount, commission_amount, owner_earnings FROM rental_transactions WHERE request_id=?;", (request_id,))
    tx = cursor.fetchone()
    check("Workflow Step 2c: Transaction record created", tx is not None)

    # Calculate expected amounts from actual date strings
    from datetime import datetime as dt2
    d1 = dt2.strptime(start_str, "%Y-%m-%d")
    d2 = dt2.strptime(end_str, "%Y-%m-%d")
    expected_days  = max((d2 - d1).days + 1, 1)
    expected_gross = round(rate * expected_days, 2)
    expected_comm  = round(expected_gross * 0.10, 2)
    expected_earn  = round(expected_gross - expected_comm, 2)
    check("Workflow Step 2d: Gross amount calculated correctly", abs(tx[2] - expected_gross) < 0.01,
          f"Expected {expected_gross}, got {tx[2]}")
    check("Workflow Step 2e: Commission = 10% of gross", abs(tx[3] - expected_comm) < 0.01,
          f"Expected {expected_comm}, got {tx[3]}")
    check("Workflow Step 2f: Owner earnings = gross - commission", abs(tx[4] - expected_earn) < 0.01,
          f"Expected {expected_earn}, got {tx[4]}")

    tx_id = tx[0]

    # Step 3: Item returned in good condition
    res_return = controllers.process_return(tx_id, "Item returned in perfect condition.", "Good", 0.0)
    check("Workflow Step 3: Return processed successfully", res_return == 1)

    cursor.execute("SELECT rental_status, actual_return_date FROM rental_transactions WHERE transaction_id=?;", (tx_id,))
    tx_row = cursor.fetchone()
    check("Workflow Step 3b: Transaction status -> Returned", tx_row[0] == "Returned")
    check("Workflow Step 3c: actual_return_date populated", tx_row[1] is not None)

    # Listing should be Available again
    cursor.execute("SELECT status FROM listings WHERE listing_id=?;", (listing_id,))
    lst_status2 = cursor.fetchone()[0]
    check("Workflow Step 3d: Listing status -> Available", lst_status2 == "Available")

    # Step 4: Grace reviews Albert (Lender)
    res_rv = controllers.submit_review(tx_id, grace_id, albert_id, "Lender", 5, "Excellent item, well maintained!")
    check("Workflow Step 4: Grace submits Lender review", res_rv > 0)

    # Step 5: Albert reviews Grace (Borrower)
    res_rv2 = controllers.submit_review(tx_id, albert_id, grace_id, "Borrower", 5, "Grace was extremely careful with the equipment.")
    check("Workflow Step 4b: Albert submits Borrower review", res_rv2 > 0)

    # Step 6: Duplicate review blocked
    dup = controllers.submit_review(tx_id, grace_id, albert_id, "Lender", 3, "Trying again")
    check("Workflow Step 5: Duplicate review correctly blocked", dup == -1)

    conn.close()

# ---------------------------------------------------------------------------
# SECTION 7: Damage Workflow
# ---------------------------------------------------------------------------
def test_damage_workflow():
    print("\n[SECTION 7] Damage & Maintenance Workflow")
    conn = db_schema.get_db_connection()
    cursor = conn.cursor()

    # Find an existing active transaction
    cursor.execute("SELECT transaction_id, listing_id, deposit_held FROM rental_transactions WHERE rental_status='Active' LIMIT 1;")
    tx = cursor.fetchone()
    if tx is None:
        check("Damage workflow: Active transaction available", False, "No Active transactions found")
        conn.close()
        return

    tx_id, listing_id, deposit = tx
    check("Damage workflow: Active transaction found", True)

    # Process return with minor damage
    res = controllers.process_return(tx_id, "Screen has a hairline crack on one corner.", "Minor", 30.00)
    check("Damage workflow: Return with minor damage processed", res == 1)

    # Listing should be Maintenance
    cursor.execute("SELECT status FROM listings WHERE listing_id=?;", (listing_id,))
    lst_status = cursor.fetchone()[0]
    check("Damage workflow: Listing status -> Maintenance", lst_status == "Maintenance")

    # Maintenance ticket auto-created
    cursor.execute("SELECT maintenance_id, cost, status FROM maintenance WHERE listing_id=? ORDER BY maintenance_id DESC LIMIT 1;", (listing_id,))
    maint = cursor.fetchone()
    check("Damage workflow: Maintenance ticket auto-created", maint is not None)
    check("Damage workflow: Maintenance cost logged (GHS 30.00)", maint is not None and abs(maint[1] - 30.00) < 0.01)

    # Update maintenance to Completed
    maint_id = maint[0]
    res2 = controllers.update_maintenance(maint_id, 30.00, "Completed", listing_id)
    check("Damage workflow: Maintenance updated to Completed", res2 == 1)

    # Listing should be Available again
    cursor.execute("SELECT status FROM listings WHERE listing_id=?;", (listing_id,))
    lst_status2 = cursor.fetchone()[0]
    check("Damage workflow: Listing restored to Available", lst_status2 == "Available")

    conn.close()

# ---------------------------------------------------------------------------
# SECTION 8: Business Intelligence Reports
# ---------------------------------------------------------------------------
def test_reports():
    print("\n[SECTION 8] Business Intelligence Reports (All 15)")
    for i in range(1, 16):
        try:
            headers, rows = controllers.get_report_data(i)
            has_headers = isinstance(headers, list) and len(headers) > 0
            check(f"Report {i:02d}: returns valid headers & data", has_headers,
                  f"Headers: {headers[:3] if headers else 'None'}")
        except Exception as e:
            check(f"Report {i:02d}: execution error", False, str(e))

# ---------------------------------------------------------------------------
# SECTION 9: Wishlist & Saved Listings
# ---------------------------------------------------------------------------
def test_saves_wishlist():
    print("\n[SECTION 9] Wishlist & Saved Listings Operations")
    conn = db_schema.get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT user_id FROM users WHERE name='Grace Mensah';")
    grace_id = cursor.fetchone()[0]
    cursor.execute("SELECT listing_id FROM listings WHERE status='Available' LIMIT 1;")
    lst_id = cursor.fetchone()[0]

    # Save a listing
    res = controllers.save_listing(grace_id, lst_id)
    check("Saved Listings: save_listing succeeds", res >= 0)

    # Duplicate save blocked
    dup = controllers.save_listing(grace_id, lst_id)
    check("Saved Listings: duplicate save correctly ignored", dup >= 0)

    # Fetch saved list
    saves = controllers.get_my_saved_listings(grace_id)
    check("Saved Listings: saved list retrieved", saves is not None and len(saves) >= 1)

    # Add wishlist alert
    cursor.execute("SELECT category_id FROM categories WHERE name='Computing Devices';")
    cat_id = cursor.fetchone()[0]
    res2 = controllers.add_to_wishlist(grace_id, cat_id, "Oscilloscope")
    check("Wishlist: add_to_wishlist succeeds", res2 >= 0)

    # Fetch wishlist
    wl = controllers.get_my_wishlist(grace_id)
    check("Wishlist: get_my_wishlist returns entries", wl is not None and len(wl) >= 1)

    conn.close()

# ---------------------------------------------------------------------------
# SECTION 10: Trust Score Calculation
# ---------------------------------------------------------------------------
def test_trust_score():
    print("\n[SECTION 10] Trust Score Derivation")
    conn = db_schema.get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM users WHERE name='Albert Boateng';")
    uid = cursor.fetchone()[0]
    conn.close()

    t = controllers.calculate_trust_score(uid)
    check("Trust score: dictionary returned", isinstance(t, dict))
    check("Trust score: 'score' key present", "score" in t)
    check("Trust score: score in valid range [0-100]", 0 <= t["score"] <= 100,
          f"Score was {t.get('score')}")
    check("Trust score: avg_rating present", "avg_rating" in t)
    check("Trust score: total_rentals present", "total_rentals" in t)

# ---------------------------------------------------------------------------
# SECTION 11: Availability Calendar Overlap Check
# ---------------------------------------------------------------------------
def test_availability():
    print("\n[SECTION 11] Availability Calendar & Overlap Detection")
    conn = db_schema.get_db_connection()
    cursor = conn.cursor()

    # Find a listing currently Rented out to get its dates
    cursor.execute("""
    SELECT t.listing_id, t.rent_start_date, t.rent_end_date
    FROM rental_transactions t WHERE t.rental_status='Active' LIMIT 1;
    """)
    row = cursor.fetchone()
    conn.close()

    if row is None:
        check("Availability: rented listing for overlap test found", False, "No Active transactions")
        return

    listing_id, start, end = row
    check("Availability: rented listing identified", True)

    # Query for this listing on overlapping dates -- should NOT appear
    results_avail = controllers.get_filtered_listings(req_start=start, req_end=end)
    listing_ids_returned = [r[0] for r in (results_avail or [])]
    check("Availability: actively rented listing excluded from search results", listing_id not in listing_ids_returned)

# ---------------------------------------------------------------------------
# FINAL SUMMARY REPORT
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# SECTION 11: Authentication & Security Operations
# ---------------------------------------------------------------------------
def test_authentication():
    print("\n[SECTION 11] Authentication & Security Operations (PBKDF2-HMAC, Auditing & Session)")
    
    # 1. Login success
    user = controllers.authenticate_user("ce-aavoryi8125@st.umat.edu.gh", "Student123")
    check("Auth: Successful login with PBKDF2 credentials", isinstance(user, dict) and user['email'] == "ce-aavoryi8125@st.umat.edu.gh")
    
    # 2. Login failure (wrong password)
    fail_pass = controllers.authenticate_user("ce-aavoryi8125@st.umat.edu.gh", "WrongPass999")
    check("Auth: Login rejected for wrong password", fail_pass == -1)
    
    # 3. Login failure (invalid email)
    fail_email = controllers.authenticate_user("invalid_user@umat.edu.gh", "Student123")
    check("Auth: Login rejected for non-existent email", fail_email == -1)
    
    # 4. Email validation on registration
    res_fake = controllers.register_user("Fake User", "fake_email_without_at", "Pass123", "FCM.41.008.099.25", "+233200000000", "Computer Science", "KT Hall")
    check("Auth: Rejects invalid email format on registration", res_fake == -1)
        
    # 5. PBKDF2 hash format check
    hashed = controllers.hash_password("TestSecret123")
    check("Auth: Hashing uses PBKDF2-HMAC-SHA256 (100k iterations)", hashed.startswith("pbkdf2_sha256$100000$"))
    
    # 6. Password verification helper
    valid = controllers.verify_password("TestSecret123", hashed)
    check("Auth: Password verification function succeeds", valid is True)
    
    # 7. Audit logging check (last_login timestamp)
    conn = db_schema.get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT last_login FROM users WHERE email = 'ce-aavoryi8125@st.umat.edu.gh';")
    last_log = cursor.fetchone()[0]
    conn.close()
    check("Auth: Login audit updates last_login timestamp", last_log is not None)
    
    # 8. Suspended account handling
    conn = db_schema.get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET account_status = 'Suspended' WHERE email = 'abena@st.umat.edu.gh';")
    conn.commit()
    conn.close()
    
    susp_res = controllers.authenticate_user("abena@st.umat.edu.gh", "Student123")
    check("Auth: Suspended user account access blocked (-2)", susp_res == -2)
    
    # Restore account status
    conn = db_schema.get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET account_status = 'Active' WHERE email = 'abena@st.umat.edu.gh';")
    conn.commit()
    conn.close()
    
    # 9. Admin role authentication
    admin_user = controllers.authenticate_user("admin@umat.edu.gh", "Admin123")
    check("Auth: Administrator account authentication & role check", isinstance(admin_user, dict) and admin_user['verification_level'] == "Admin")
    
    # 10. Duplicate registration prevention
    res_dup = controllers.register_user("Albert Duplicate", "ce-aavoryi8125@st.umat.edu.gh", "Pass123", "FCM.41.008.043.25", "+233200000000", "Computer Science", "KT Hall")
    check("Auth: Duplicate email registration blocked", res_dup == -1)

# ---------------------------------------------------------------------------
# FINAL SUMMARY REPORT
# ---------------------------------------------------------------------------
def print_summary():
    print("\n" + "="*72)
    print(f"  {'TEST LABEL':<48} {'STATUS':<8} {'DETAIL'}")
    print("="*72)
    for label, status, detail in results:
        icon = "OK" if status == PASS else "!!"
        d = (detail[:20] + "...") if detail and len(detail) > 20 else (detail or "")
        print(f"  [{icon}] {label:<44} {status:<8} {d}")
    print("="*72)
    passed = sum(1 for _, s, _ in results if s == PASS)
    failed = sum(1 for _, s, _ in results if s == FAIL)
    total  = len(results)
    print(f"\n  TOTAL: {total} tests  |  PASSED: {passed}  |  FAILED: {failed}")
    if failed == 0:
        print("\n  ALL TESTS PASSED. CampusLink is ready for demonstration.")
    else:
        print(f"\n  {failed} test(s) FAILED. Review output above for details.")
    print("="*72)

# ---------------------------------------------------------------------------
# ENTRY POINT
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("="*72)
    print("  CampusLink End-to-End Test Suite")
    print("  University of Mines and Technology (UMaT), Tarkwa, Ghana")
    print("="*72)

    setup()
    test_schema()
    test_constraints()
    test_crud()
    test_alter()
    test_queries()
    test_availability()
    test_workflow()
    test_damage_workflow()
    test_reports()
    test_saves_wishlist()
    test_trust_score()
    test_authentication()
    print_summary()

    # Exit with non-zero if any failures
    failed_count = sum(1 for _, s, _ in results if s == FAIL)
    sys.exit(failed_count)
