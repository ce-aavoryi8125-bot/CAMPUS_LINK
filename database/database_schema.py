import sqlite3
import os
import sys

DB_NAME = "campuslink_umat.db"

def get_db_connection():
    db_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(db_dir, DB_NAME)
    conn = sqlite3.connect(db_path)
    # Enforce foreign key constraints
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def create_tables():
    conn = get_db_connection()
    cursor = conn.cursor()

    print("Creating tables...")

    # 1. USERS Table (Updated with Authentication & Account Status)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL CHECK(email LIKE '%@umat.edu.gh' OR email LIKE '%@student.umat.edu.gh' OR email LIKE '%@st.umat.edu.gh'),
        password_hash TEXT NOT NULL,
        student_id TEXT UNIQUE,
        phone TEXT NOT NULL,
        verification_level TEXT NOT NULL DEFAULT 'Unverified' CHECK(verification_level IN ('Unverified', 'Verified Student', 'Verified Staff', 'Admin')),
        account_status TEXT NOT NULL DEFAULT 'Active' CHECK(account_status IN ('Active', 'Suspended', 'Pending Verification')),
        department TEXT NOT NULL,
        hostel TEXT,
        last_login DATETIME,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 2. CATEGORIES Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS categories (
        category_id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        description TEXT
    );
    """)

    # 3. LISTINGS Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS listings (
        listing_id INTEGER PRIMARY KEY AUTOINCREMENT,
        owner_id INTEGER NOT NULL,
        category_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        description TEXT,
        subcategory TEXT NOT NULL,
        brand TEXT NOT NULL,
        model TEXT NOT NULL,
        purchase_year INTEGER,
        rental_rate_per_day REAL NOT NULL CHECK(rental_rate_per_day >= 0),
        deposit_amount REAL NOT NULL CHECK(deposit_amount >= 0),
        condition TEXT NOT NULL CHECK(condition IN ('New', 'Good', 'Fair', 'Poor')),
        status TEXT NOT NULL DEFAULT 'Available' CHECK(status IN ('Available', 'Reserved', 'Rented', 'Maintenance', 'Delisted')),
        pickup_location TEXT NOT NULL,
        thumbnail_path TEXT,
        available_from TEXT NOT NULL, -- YYYY-MM-DD format
        available_until TEXT NOT NULL, -- YYYY-MM-DD format
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (owner_id) REFERENCES users (user_id) ON DELETE CASCADE,
        FOREIGN KEY (category_id) REFERENCES categories (category_id) ON DELETE CASCADE,
        CHECK(available_until >= available_from)
    );
    """)

    # 4. RENTAL REQUESTS Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS rental_requests (
        request_id INTEGER PRIMARY KEY AUTOINCREMENT,
        listing_id INTEGER NOT NULL,
        borrower_id INTEGER NOT NULL,
        rent_start_date TEXT NOT NULL, -- YYYY-MM-DD format
        rent_end_date TEXT NOT NULL, -- YYYY-MM-DD format
        rental_purpose TEXT NOT NULL CHECK(rental_purpose IN ('Field Trip', 'Final Year Project', 'Laboratory Session', 'Research', 'Presentation', 'Personal Use')),
        status TEXT NOT NULL DEFAULT 'Pending' CHECK(status IN ('Pending', 'Approved', 'Rejected', 'Cancelled')),
        notes TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (listing_id) REFERENCES listings (listing_id) ON DELETE CASCADE,
        FOREIGN KEY (borrower_id) REFERENCES users (user_id) ON DELETE CASCADE,
        CHECK(rent_end_date >= rent_start_date)
    );
    """)

    # 5. RENTAL TRANSACTIONS Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS rental_transactions (
        transaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
        request_id INTEGER UNIQUE NOT NULL,
        listing_id INTEGER NOT NULL,
        borrower_id INTEGER NOT NULL,
        rent_start_date TEXT NOT NULL, -- YYYY-MM-DD format
        rent_end_date TEXT NOT NULL, -- YYYY-MM-DD format
        actual_return_date TEXT, -- YYYY-MM-DD format
        total_days INTEGER NOT NULL CHECK(total_days > 0),
        gross_amount REAL NOT NULL CHECK(gross_amount >= 0),
        commission_amount REAL NOT NULL CHECK(commission_amount >= 0),
        owner_earnings REAL NOT NULL CHECK(owner_earnings >= 0),
        deposit_held REAL NOT NULL CHECK(deposit_held >= 0),
        payment_status TEXT NOT NULL DEFAULT 'Pending' CHECK(payment_status IN ('Pending', 'Paid', 'Refunded')),
        rental_status TEXT NOT NULL DEFAULT 'Active' CHECK(rental_status IN ('Active', 'Returned', 'Overdue', 'Cancelled')),
        return_notes TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (request_id) REFERENCES rental_requests (request_id) ON DELETE CASCADE,
        FOREIGN KEY (listing_id) REFERENCES listings (listing_id) ON DELETE CASCADE,
        FOREIGN KEY (borrower_id) REFERENCES users (user_id) ON DELETE CASCADE
    );
    """)

    # 6. MAINTENANCE Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS maintenance (
        maintenance_id INTEGER PRIMARY KEY AUTOINCREMENT,
        listing_id INTEGER NOT NULL,
        reported_by INTEGER NOT NULL,
        issue_description TEXT NOT NULL,
        cost REAL NOT NULL DEFAULT 0.00 CHECK(cost >= 0),
        status TEXT NOT NULL DEFAULT 'Pending' CHECK(status IN ('Pending', 'In Progress', 'Completed')),
        start_date TEXT NOT NULL, -- YYYY-MM-DD format
        end_date TEXT, -- YYYY-MM-DD format
        FOREIGN KEY (listing_id) REFERENCES listings (listing_id) ON DELETE CASCADE,
        FOREIGN KEY (reported_by) REFERENCES users (user_id) ON DELETE CASCADE
    );
    """)

    # 7. REVIEWS Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS reviews (
        review_id INTEGER PRIMARY KEY AUTOINCREMENT,
        transaction_id INTEGER NOT NULL,
        reviewer_id INTEGER NOT NULL,
        reviewee_id INTEGER NOT NULL,
        reviewee_type TEXT NOT NULL CHECK(reviewee_type IN ('Lender', 'Borrower')),
        rating INTEGER NOT NULL CHECK(rating >= 1 AND rating <= 5),
        comment TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (transaction_id) REFERENCES rental_transactions (transaction_id) ON DELETE CASCADE,
        FOREIGN KEY (reviewer_id) REFERENCES users (user_id) ON DELETE CASCADE,
        FOREIGN KEY (reviewee_id) REFERENCES users (user_id) ON DELETE CASCADE
    );
    """)

    # 8. WISHLIST Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS wishlist (
        wishlist_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        category_id INTEGER,
        keyword TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE,
        FOREIGN KEY (category_id) REFERENCES categories (category_id) ON DELETE SET NULL,
        UNIQUE(user_id, category_id, keyword)
    );
    """)

    # 9. SAVED LISTINGS Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS saved_listings (
        saved_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        listing_id INTEGER NOT NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE,
        FOREIGN KEY (listing_id) REFERENCES listings (listing_id) ON DELETE CASCADE,
        UNIQUE(user_id, listing_id)
    );
    """)

    # Create indexes for optimization
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_listings_owner ON listings(owner_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_listings_category ON listings(category_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_requests_listing ON rental_requests(listing_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_requests_borrower ON rental_requests(borrower_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_transactions_request ON rental_transactions(request_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_reviews_transaction ON reviews(transaction_id);")

    conn.commit()
    conn.close()
    print("Tables created successfully.")

def drop_column_compatibly(table_name, column_name):
    """
    Safely drops a column from an SQLite table.
    Works natively on SQLite 3.35.0+ and emulates table recreation for older versions.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get SQLite version
    cursor.execute("SELECT sqlite_version();")
    ver_str = cursor.fetchone()[0]
    ver = tuple(map(int, ver_str.split('.')))
    
    print(f"SQLite Version: {ver_str}")
    
    if ver >= (3, 35, 0):
        print(f"Executing: ALTER TABLE {table_name} DROP COLUMN {column_name} (native)")
        cursor.execute(f"ALTER TABLE {table_name} DROP COLUMN {column_name};")
    else:
        print(f"Emulating column drop for {table_name}.{column_name} via table recreation")
        cursor.execute(f"PRAGMA table_info({table_name});")
        columns = cursor.fetchall()
        
        cols_to_keep = [col[1] for col in columns if col[1] != column_name]
        
        if len(cols_to_keep) == len(columns):
            print(f"Column '{column_name}' not found in table '{table_name}'. Skipping.")
            conn.close()
            return
            
        temp_table = f"{table_name}_temp"
        
        cols_def = []
        for col in columns:
            name_c = col[1]
            type_c = col[2]
            notnull_c = "NOT NULL" if col[3] else ""
            default_c = f"DEFAULT {col[4]}" if col[4] is not None else ""
            pk_c = "PRIMARY KEY" if col[5] else ""
            
            if name_c != column_name:
                cols_def.append(f"{name_c} {type_c} {pk_c} {notnull_c} {default_c}".strip())
        
        sql_fields = ", ".join(cols_def)
        cursor.execute(f"CREATE TABLE {temp_table} ({sql_fields});")
            
        cols_str = ", ".join(cols_to_keep)
        cursor.execute(f"INSERT INTO {temp_table} ({cols_str}) SELECT {cols_str} FROM {table_name};")
        
        cursor.execute(f"DROP TABLE {table_name};")
        cursor.execute(f"ALTER TABLE {temp_table} RENAME TO {table_name};")
        
    conn.commit()
    conn.close()
    print(f"Column {column_name} dropped successfully from {table_name}.")

if __name__ == "__main__":
    create_tables()
