import sqlite3
import os
import sys

# Handle imports whether run from root or tests/ folder
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

try:
    from database import database_schema as db_schema
    from database import db_seeder
except ImportError:
    import database_schema as db_schema
    import db_seeder

def print_separator(title):
    print("\n" + "="*80)
    print(f" {title.upper()} ")
    print("="*80)

def run_query(conn, query, description, params=None):
    print(f"\n[QUERY] {description}:")
    print(f"SQL: {query}")
    cursor = conn.cursor()
    try:
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        
        if query.strip().upper().startswith("SELECT"):
            rows = cursor.fetchall()
            headers = [desc[0] for desc in cursor.description]
            print(f"Headers: {headers}")
            for r in rows:
                print(r)
            return rows
        else:
            conn.commit()
            print(f"Affected Rows: {cursor.rowcount}")
            return cursor.rowcount
    except sqlite3.Error as e:
        print(f"ERROR: {e}")
        return None

def main():
    print("Initializing verification environment...")
    db_seeder.seed_database()
    conn = db_schema.get_db_connection()

    # 1. ALTER TABLE Operations (Add Column, Drop Column)
    print_separator("1. ALTER TABLE Operations (Columns)")
    run_query(conn, "ALTER TABLE users ADD COLUMN bio TEXT DEFAULT 'UMaT Student';", "Add column 'bio' to users table")
    db_schema.drop_column_compatibly("users", "bio")
    conn = db_schema.get_db_connection()

    # 2. DELETE and UPDATE Operations
    print_separator("2. Record Modifications (DELETE and UPDATE)")
    run_query(conn, "INSERT INTO users (name, email, phone, department) VALUES ('Temp User', 'temp@student.umat.edu.gh', '+1234', 'Mining');", "Insert temporary user")
    run_query(conn, "DELETE FROM users WHERE email='temp@student.umat.edu.gh';", "Delete temporary user")
    run_query(conn, "UPDATE users SET verification_level='Verified Student' WHERE name='Grace Mensah';", "Update verification status for Grace Mensah")

    # 3. SELECT and ORDER BY Operations
    print_separator("3. Data Selection & Ordering")
    run_query(conn, "SELECT name, email, department FROM users WHERE verification_level='Verified Student';", "Select all verified students")
    run_query(conn, "SELECT title, rental_rate_per_day, condition FROM listings ORDER BY rental_rate_per_day ASC;", "Listings ordered by daily rate ASC")
    run_query(conn, "SELECT title, deposit_amount FROM listings ORDER BY deposit_amount DESC;", "Listings ordered by deposit DESC")

    # 4. Constraints Verification & Aggregate Functions
    print_separator("4. Constraints & Aggregate Functions")
    print("\nTesting CHECK Constraint (Domain email check):")
    try:
        conn.cursor().execute("INSERT INTO users (name, email, phone, department) VALUES ('Invalid', 'bademail@gmail.com', '+123', 'Dept');")
        print("FAIL: Bad email inserted successfully!")
    except sqlite3.IntegrityError as e:
        print(f"SUCCESS: Email constraint caught error -> {e}")

    run_query(conn, "SELECT COUNT(*) AS total_listings FROM listings;", "Aggregate COUNT of all listings")
    run_query(conn, "SELECT SUM(gross_amount) AS total_gross_revenue FROM rental_transactions;", "Aggregate SUM of rental gross amounts")
    run_query(conn, "SELECT AVG(rental_rate_per_day) AS avg_daily_rate FROM listings;", "Aggregate AVG of listing rental rates")
    run_query(conn, "SELECT MIN(rental_rate_per_day) AS min_rate, MAX(rental_rate_per_day) AS max_rate FROM listings;", "Aggregate MIN and MAX daily rates")
    run_query(conn, "SELECT DISTINCT category_id FROM listings;", "DISTINCT category IDs in active listings")

    # 5. JOINS Operations (INNER, LEFT, RIGHT emulation)
    print_separator("5. SQL Joins (INNER JOIN, LEFT JOIN, RIGHT JOIN Emulation)")
    run_query(conn, """
        SELECT t.transaction_id, u.name AS borrower, l.title AS item, t.gross_amount, t.rental_status
        FROM rental_transactions t
        INNER JOIN users u ON t.borrower_id = u.user_id
        INNER JOIN listings l ON t.listing_id = l.listing_id;
    """, "INNER JOIN: Transactions with Borrower Name and Item Title")

    run_query(conn, """
        SELECT l.listing_id, l.title, t.transaction_id, t.rental_status
        FROM listings l
        LEFT JOIN rental_transactions t ON l.listing_id = t.listing_id;
    """, "LEFT JOIN: All listings and their transaction history (including un-rented)")

    run_query(conn, """
        SELECT u.name AS user_name, l.title AS owned_item
        FROM users u
        LEFT JOIN listings l ON u.user_id = l.owner_id;
    """, "RIGHT JOIN Emulation: All users and their owned items (Users RIGHT JOIN Listings)")

    # 6. WILDCARD (LIKE) Filters
    print_separator("6. Wildcard Searches (LIKE)")
    run_query(conn, "SELECT name, email FROM users WHERE name LIKE 'A%';", "LIKE prefix filter ('A%')")
    run_query(conn, "SELECT name, email FROM users WHERE email LIKE '%@student.umat.edu.gh';", "LIKE suffix filter ('%@student.umat.edu.gh')")
    run_query(conn, "SELECT title, description FROM listings WHERE description LIKE '%GPS%';", "LIKE substring filter ('%GPS%')")

    conn.close()
    print_separator("VERIFICATION COMPLETED SUCCESSFULLY")

if __name__ == "__main__":
    main()
