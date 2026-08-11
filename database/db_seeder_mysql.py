import os
import sys
import hashlib
from datetime import datetime, timedelta

# Import unified db_engine
try:
    import db_engine
    from database import database_schema as db_schema
except ImportError:
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    import db_engine
    import database_schema as db_schema

def hash_password(password, salt="umat_campuslink_2026"):
    key = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt.encode('utf-8'),
        100000
    )
    return f"pbkdf2_sha256$100000${salt}${key.hex()}"

def seed_database_engine():
    print("[SEEDER] Initializing CampusLink Database Seeding...")
    db_type, conn = db_engine.get_connection()
    conn.close()
    
    print(f"[SEEDER] Target Database Engine: {db_type.upper()}")

    # Ensure SQLite tables exist if running on SQLite
    if db_type == "sqlite":
        db_schema.create_tables()

    # 1. Clear existing data
    tables = ["saved_listings", "wishlist", "reviews", "maintenance", "rental_transactions", "rental_requests", "listings", "categories", "users"]
    for tbl in tables:
        try:
            db_engine.execute_query(f"DELETE FROM {tbl};", fetch="rowcount")
        except Exception:
            pass

    if db_type == "sqlite":
        try:
            db_engine.execute_query("DELETE FROM sqlite_sequence;", fetch="rowcount")
        except Exception:
            pass

    # 2. Seed Categories (13 Categories)
    categories = [
        ('Computing Devices', 'Laptops, tablets, monitors, and computer accessories.'),
        ('Surveying Equipment', 'Total Stations, GPS units, theodolites, levelling instruments.'),
        ('Mining PPE & Gear', 'Safety helmets, boots, high-vis vests, respirators, safety goggles.'),
        ('Geology Field Equipment', 'Geological hammers, hand lenses, compasses, streak plates.'),
        ('Electrical & Lab Tools', 'Oscilloscopes, digital multimeters, soldering stations, breadboards.'),
        ('Calculators & Books', 'Financial and scientific calculators, engineering textbooks.'),
        ('Presentation Gear', 'Projectors, clickers, portable screens, laser pointers.'),
        ('Hostel Appliances', 'Mini refrigerators, microwave ovens, kettles, fans, irons.'),
        ('Sports & Fitness', 'Table tennis bats, footballs, basketballs, gym equipment.'),
        ('Cameras & Media', 'DSLR cameras, tripods, microphones, lighting kits.'),
        ('Musical Instruments', 'Acoustic guitars, keyboards, amplifiers, rhythm pads.'),
        ('Bicycles & Transport', 'Mountain bikes, electric scooters, helmets.'),
        ('Drawing & Drafting', 'T-squares, drafting boards, set squares, technical pens.')
    ]
    for c in categories:
        db_engine.execute_query("INSERT INTO categories (name, description) VALUES (?, ?);", c, fetch="rowcount")
    print(f"[SEEDER] Seeded {len(categories)} categories.")

    # 3. Seed Users
    pass_student = hash_password('Student123')
    pass_staff   = hash_password('Staff123')
    pass_admin   = hash_password('Admin123')

    users = [
        ('Albert Boateng', 'ce-aavoryi8125@st.umat.edu.gh', pass_student, 'FCM.41.008.043.25', '+233241234567', 'Verified Student', 'Active', 'Geomatic Engineering', 'Chamber of Mines Hostel'),
        ('Benedict Osei', 'benedict@st.umat.edu.gh', pass_student, 'FCM.41.008.044.25', '+233209876543', 'Verified Student', 'Active', 'Mining Engineering', 'Gold Refinery Hostel'),
        ('Grace Mensah', 'grace@st.umat.edu.gh', pass_student, 'FCM.41.008.045.25', '+233551122334', 'Unverified', 'Active', 'Petroleum Engineering', 'K.T. Hall'),
        ('Dr. Kwame Asante', 'kasante@umat.edu.gh', pass_staff, None, '+233277889900', 'Verified Staff', 'Active', 'Electrical & Electronic Engineering', 'Staff Quarters'),
        ('Abena Owusu', 'abena@st.umat.edu.gh', pass_student, 'FCM.41.008.046.25', '+233543210987', 'Unverified', 'Active', 'Geological Engineering', 'Dr. M.T. Kofi Hall'),
        ('Admin CampusLink', 'admin@umat.edu.gh', pass_admin, None, '+233200000000', 'Admin', 'Active', 'Computer Science & Engineering', 'Main Admin Block')
    ]
    for u in users:
        db_engine.execute_query("""
        INSERT INTO users (name, email, password_hash, student_id, phone, verification_level, account_status, department, hostel)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, u, fetch="rowcount")
    print(f"[SEEDER] Seeded {len(users)} users.")

    # 4. Fetch category & user IDs dynamically
    cat_rows = db_engine.execute_query("SELECT category_id, name FROM categories ORDER BY category_id ASC;")
    cat_map = {r['name']: r['category_id'] for r in cat_rows}

    user_rows = db_engine.execute_query("SELECT user_id, email FROM users ORDER BY user_id ASC;")
    user_map = {r['email']: r['user_id'] for r in user_rows}

    today = datetime.now().date()
    start_avail = today.strftime("%Y-%m-%d")
    end_avail = (today + timedelta(days=90)).strftime("%Y-%m-%d")

    # Sample listings
    albert_id = user_map.get('ce-aavoryi8125@st.umat.edu.gh', 1)
    benedict_id = user_map.get('benedict@st.umat.edu.gh', 2)
    grace_id = user_map.get('grace@st.umat.edu.gh', 3)
    kwame_id = user_map.get('kasante@umat.edu.gh', 4)

    listings = [
        (albert_id, cat_map.get('Computing Devices', 1), 'Dell XPS 15 Laptop (Core i7, 32GB RAM)', 'Laptop', 'Dell', 'XPS 9510', 2022, 90.0, 400.0, 'Good', 'Available', 'Chamber of Mines Hostel', 'assets/products/dell_xps15.png', start_avail, end_avail, 'High performance laptop for CAD, GIS, and rendering.'),
        (albert_id, cat_map.get('Surveying Equipment', 2), 'Leica Total Station TS07', 'Total Station', 'Leica', 'FlexLine TS07', 2022, 120.0, 500.0, 'Good', 'Available', 'Chamber of Mines Hostel', 'assets/products/leica_total_station_ts07.png', start_avail, end_avail, 'High precision surveying total station for field practicals.'),
        (benedict_id, cat_map.get('Mining PPE & Gear', 3), 'Mining Safety Helmet & Boots Combo', 'PPE Kit', 'JSP / CAT', 'EVO3 / Holton', 2023, 25.0, 80.0, 'New', 'Available', 'Gold Refinery Hostel', 'assets/products/mining_ppe_combo.png', start_avail, end_avail, 'Hard hat plus size 43 steel toe work boots for industrial visits.'),
        (benedict_id, cat_map.get('Hostel Appliances', 8), 'Hisense 90L Compact Mini Refrigerator', 'Fridge', 'Hisense', 'REF093DR 90L', 2022, 15.0, 200.0, 'Good', 'Available', 'Gold Refinery Hostel', 'assets/products/hisense_mini_fridge.png', start_avail, end_avail, 'Compact hostel room fridge. Low power consumption.'),
        (kwame_id, cat_map.get('Electrical & Lab Tools', 5), 'Rigol Digital Oscilloscope 100MHz (2-CH)', 'Oscilloscope', 'Rigol', 'DS1102Z-E', 2021, 50.0, 300.0, 'Good', 'Available', 'Staff Quarters', 'assets/products/rigol_oscilloscope_100mhz.png', start_avail, end_avail, '2-channel digital oscilloscope for lab experiments.'),
        (grace_id, cat_map.get('Geology Field Equipment', 4), 'Estwing 22oz Pointed Tip Rock Hammer', 'Rock Hammer', 'Estwing', 'E3-22P 22oz', 2020, 15.0, 60.0, 'Good', 'Available', 'Gold Refinery Hostel', 'assets/products/estwing_rock_hammer.png', start_avail, end_avail, 'Pointed tip 22oz rock pick hammer for field geology work.')
    ]

    for lst in listings:
        db_engine.execute_query("""
        INSERT INTO listings (owner_id, category_id, title, subcategory, brand, model, purchase_year, rental_rate_per_day, deposit_amount, `condition`, status, pickup_location, thumbnail_path, available_from, available_until, description)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, lst, fetch="rowcount")

    print(f"[SEEDER] Seeded {len(listings)} core marketplace listings.")

    # 5. Sample Transactions
    r_start = (today - timedelta(days=10)).strftime("%Y-%m-%d")
    r_end = (today - timedelta(days=5)).strftime("%Y-%m-%d")

    req_id = db_engine.execute_query("""
    INSERT INTO rental_requests (listing_id, borrower_id, rent_start_date, rent_end_date, rental_purpose, status, notes)
    VALUES (2, 3, ?, ?, 'Field Trip', 'Approved', 'Need Total Station for surveying practicals.');
    """, (r_start, r_end), fetch="lastrowid")

    if req_id:
        tx_id = db_engine.execute_query("""
        INSERT INTO rental_transactions (request_id, listing_id, borrower_id, rent_start_date, rent_end_date, actual_return_date, total_days, gross_amount, commission_amount, owner_earnings, deposit_held, payment_status, rental_status, return_notes)
        VALUES (?, 2, 3, ?, ?, ?, 5, 600.00, 60.00, 540.00, 500.00, 'Paid', 'Returned', 'Equipment returned in pristine condition.');
        """, (req_id, r_start, r_end, r_end), fetch="lastrowid")

        if tx_id:
            db_engine.execute_query("INSERT INTO reviews (transaction_id, reviewer_id, reviewee_id, reviewee_type, rating, comment) VALUES (?, 3, 1, 'Lender', 5, 'Exceptional equipment, very helpful owner!');", (tx_id,), fetch="rowcount")

    print("[SEEDER] CampusLink Database Seeding Completed Successfully.")

if __name__ == "__main__":
    seed_database_engine()
