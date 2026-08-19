# UNIVERSITY OF MINES AND TECHNOLOGY
## A REPORT ON
### DATABASE SYSTEMS
**PROJECT TITLE:**  
**DESIGN AND IMPLEMENTATION OF THE CAMPUSLINK PEER-TO-PEER EQUIPMENT RENTAL DATABASE SYSTEM**  

**BY: ALBERT ATSU AVORYI**  

**LECTURER: DR. AFFUM**  

**SUBMISSION DATE: 6TH AUGUST, 2026**  

---

## DECLARATION
I solemnly declare that this report is my original work, prepared specifically for the Database Systems Project Two assignment. It has not been submitted, either in full or in part, for any other assignment, examination, or academic qualification at this or any other institution. All sources of information and materials used in the preparation of this report have been appropriately acknowledged and referenced.

---

## ABSTRACT
This report presents the design and implementation of CampusLink, a relational database system and desktop marketplace application developed for the University of Mines and Technology (UMaT), Tarkwa campus community as part of the Database Systems (CE 170) Project Two assignment. The project demonstrates the end-to-end development of a real-world database platform, including domain-constrained schema design across 9 interconnected tables, insertion of sample records, schema evolution (ALTER TABLE), record updates and deletions, enforcement of primary/foreign keys and CHECK constraints, execution of aggregate functions, implementation of table joins (INNER, LEFT, and RIGHT join emulation), pattern matching using wildcard operators (LIKE), cryptographic security via PBKDF2-HMAC-SHA256, and the development of a modern Graphical User Interface (GUI) in Python using PySide6 (Qt6).

The CampusLink database comprises 9 related entities: USERS, CATEGORIES, LISTINGS, RENTAL_REQUESTS, RENTAL_TRANSACTIONS, MAINTENANCE, REVIEWS, WISHLIST, and SAVED_LISTINGS. The completed application was verified through an automated end-to-end test suite executing 100 verification checks across all SQL queries, business logic controllers, financial calculations, and constraint rules with a 100% pass rate.

---

## ACKNOWLEDGEMENTS
I would like to express my sincere appreciation to my lecturer, Dr. Affum, for the invaluable guidance, encouragement, and course instruction provided throughout the Database Systems course. I am also grateful to my colleagues in the Department of Computer Science and Engineering for insightful technical discussions, and to my family for their unwavering support throughout the duration of this assignment.

---

## TABLE OF CONTENTS
1. INTRODUCTION
1.1 Background
1.2 The Platform: CampusLink
1.3 Objectives of the Project
1.4 Tools Used
2. SYSTEM ANALYSIS
2.1 Actors and System Roles
2.2 System Use Case Overview
2.3 Rental Lifecycle Flow
3. DATABASE DESIGN AND ENTITY RELATIONSHIP MODEL
3.1 Database Creation
3.2 Table Structure and Data Dictionary
3.3 CLI Screenshots of Database Tables
3.4 Relationships and Normalization
3.5 Entity Relationship (ER) Diagram
4. DATABASE OPERATIONS AND SQL IMPLEMENTATION
4.1 Table Creation DDL (SQLite and MySQL Syntax)
4.2 Data Insertion (DML)
4.3 Schema Modification (ALTER TABLE)
4.4 Data Update and Delete Operations
4.5 Data Selection and Ordering (SELECT, ORDER BY)
4.6 Data Integrity Constraints and Aggregate Functions
4.7 Relational Join Operations (INNER, LEFT, RIGHT Emulation)
4.8 Wildcards and LIKE Statements
5. GRAPHICAL USER INTERFACE (GUI) IMPLEMENTATION
5.1 Design Overview and Architecture
5.2 How the GUI Interacts with the Database
5.3 Interface Screenshots and Descriptions
6. SYSTEM TESTING AND VERIFICATION
6.1 Automated Test Results (100/100 Passed)
6.2 Workflow Verification
7. CONCLUSION
REFERENCES

---

## 1. INTRODUCTION

### 1.1 Background
This report presents the design, implementation, and testing of a relational database and interactive graphical user interface developed for an academic equipment-sharing business platform as part of the Database Systems (CE/IS/CY 170) Project Two assignment. The project focuses on designing a robust relational database capable of supporting peer-to-peer equipment rentals across campus, enforcing data integrity constraints, tracking rental payments, managing asset maintenance, executing analytical queries, and providing a non-technical GUI interface for real-time interaction.

### 1.2 The Platform: CampusLink
CampusLink is a peer-to-peer equipment rental marketplace designed specifically for students and staff at the University of Mines and Technology (UMaT), Tarkwa. Specialized engineering disciplines-such as Geomatic, Mining, Geological, Electrical, and Computer Engineering-require costly equipment including Leica Total Stations, Trimble GNSS Receivers, Rigol Digital Oscilloscopes, Rock Hammers, Safety Boots, and High-Performance Laptops.

CampusLink connects equipment owners (Lenders) with students needing short-term equipment (Borrowers). The database tracks registered users, item listings, borrowing requests, financial transactions, peer reviews, wishlist alerts, and maintenance logs.

### 1.3 Objectives of the Project
1. Design and create a relational database named campuslink_umat containing 9 related tables with primary/foreign keys and data integrity constraints.
2. Populate the database with realistic sample records representing UMaT campus transactions.
3. Demonstrate schema modification by adding and dropping columns (ALTER TABLE), and data modification through UPDATE and DELETE queries.
4. Execute SELECT queries with ascending and descending data ordering (ORDER BY).
5. Apply database integrity constraints (PRIMARY KEY, FOREIGN KEY, UNIQUE, NOT NULL, CHECK, DEFAULT) and perform aggregate calculations (COUNT, SUM, AVG, MIN, MAX).
6. Perform INNER JOIN, LEFT JOIN, and RIGHT JOIN operations (including SQLite compatibility emulation).
7. Implement pattern matching using the LIKE wildcard operator (%).
8. Design and build a responsive Graphical User Interface (GUI) in Python (PySide6) supporting CRUD operations and dark/light UI themes.
9. Execute automated end-to-end test suite to verify 100% system compliance.

### 1.4 Tools Used
- Database Management System: SQLite 3 (with PRAGMA foreign_keys = ON;) and MySQL 8.0 DDL Compatibility
- GUI / Application Language: Python 3.10+ using PySide6 (Qt6) framework
- Cryptographic Library: Python hashlib implementing PBKDF2-HMAC-SHA256 (100,000 iterations)
- Development Environment: VS Code and Python IDLE
- Operating System: Windows 11

---

## 2. SYSTEM ANALYSIS

### 2.1 Actors and System Roles
1. Student / Borrower: Browses available equipment, filters items by category/condition/rate, submits rental requests, pays deposits, returns items, and rates lenders.
2. Equipment Owner / Lender: Posts equipment listings, sets daily rental rates and deposits, approves or rejects borrowing requests, inspects returned items, and receives net rental earnings (90% of gross fee).
3. Administrator: Manages user verification levels (Unverified, Verified Student, Verified Staff, Admin), inspects student credentials, suspends delinquent accounts, monitors maintenance tickets, and runs 15 Business Intelligence (BI) analytical reports.

### 2.2 System Use Case Overview
![Figure 2.1: System Use Case Overview](file:///C:/Users/Albert/.gemini/antigravity/brain/3b620b1f-7281-460b-a2ff-2eecc0398bcd/use_case_diagram.png)

### 2.3 Rental Lifecycle and Workflow
![Figure 2.2: Rental Lifecycle and Workflow Flowchart](file:///C:/Users/Albert/.gemini/antigravity/brain/3b620b1f-7281-460b-a2ff-2eecc0398bcd/flowchart_diagram.png)

---

## 3. DATABASE DESIGN AND ENTITY RELATIONSHIP MODEL

### 3.1 Database Creation
The database is named campuslink_umat and initialized with foreign key enforcement:
PRAGMA foreign_keys = ON;

### 3.2 Table Structure and Data Dictionary
The database consists of 9 normalized tables:

Table Name | Description | Key Attributes
--- | --- | ---
USERS | Stores user identity, UMaT email, password hash, student ID, verification status, and hostel. | user_id (PK), email (UK)
CATEGORIES | Defines equipment categories (Surveying, Mining PPE, Computing, Electronics, Laboratory, etc.). | category_id (PK), name (UK)
LISTINGS | Equipment posted for rental with daily rates, deposit amounts, condition, and status. | listing_id (PK), owner_id (FK), category_id (FK)
RENTAL_REQUESTS | Booking requests submitted by borrowers with requested date ranges and purpose. | request_id (PK), listing_id (FK), borrower_id (FK)
RENTAL_TRANSACTIONS | Active and completed rental contracts tracking gross fees, 10% commission, and payouts. | transaction_id (PK), request_id (FK, UK)
MAINTENANCE | Damage logs tracking repair costs, issue descriptions, and maintenance completion dates. | maintenance_id (PK), listing_id (FK)
REVIEWS | Peer rating scores (1-5 stars) and feedback comments between lenders and borrowers. | review_id (PK), transaction_id (FK)
WISHLIST | Category and keyword interest alerts configured by students. | wishlist_id (PK), user_id (FK)
SAVED_LISTINGS | Bookmarked marketplace listings saved by users for quick reference. | saved_id (PK), user_id (FK), listing_id (FK)

### 3.3 CLI Screenshots of Database Tables
The following command line interface screenshots show the populated sample records across all 9 database tables.

![Figure 3.1: CLI Screenshot - USERS Table Output](file:///C:/Users/Albert/.gemini/antigravity/brain/3b620b1f-7281-460b-a2ff-2eecc0398bcd/cli_users_table.png)
Figure 3.1: Command line output showing populated records in the USERS table.

![Figure 3.2: CLI Screenshot - CATEGORIES Table Output](file:///C:/Users/Albert/.gemini/antigravity/brain/3b620b1f-7281-460b-a2ff-2eecc0398bcd/cli_categories_table.png)
Figure 3.2: Command line output showing populated records in the CATEGORIES table.

![Figure 3.3: CLI Screenshot - LISTINGS Table Output](file:///C:/Users/Albert/.gemini/antigravity/brain/3b620b1f-7281-460b-a2ff-2eecc0398bcd/cli_listings_table.png)
Figure 3.3: Command line output showing populated records in the LISTINGS table.

![Figure 3.4: CLI Screenshot - RENTAL_REQUESTS Table Output](file:///C:/Users/Albert/.gemini/antigravity/brain/3b620b1f-7281-460b-a2ff-2eecc0398bcd/cli_requests_table.png)
Figure 3.4: Command line output showing populated records in the RENTAL_REQUESTS table.

![Figure 3.5: CLI Screenshot - RENTAL_TRANSACTIONS Table Output](file:///C:/Users/Albert/.gemini/antigravity/brain/3b620b1f-7281-460b-a2ff-2eecc0398bcd/cli_transactions_table.png)
Figure 3.5: Command line output showing populated records in the RENTAL_TRANSACTIONS table.

![Figure 3.6: CLI Screenshot - MAINTENANCE Table Output](file:///C:/Users/Albert/.gemini/antigravity/brain/3b620b1f-7281-460b-a2ff-2eecc0398bcd/cli_maintenance_table.png)
Figure 3.6: Command line output showing populated records in the MAINTENANCE table.

![Figure 3.7: CLI Screenshot - REVIEWS Table Output](file:///C:/Users/Albert/.gemini/antigravity/brain/3b620b1f-7281-460b-a2ff-2eecc0398bcd/cli_reviews_table.png)
Figure 3.7: Command line output showing populated records in the REVIEWS table.

![Figure 3.8: CLI Screenshot - WISHLIST Table Output](file:///C:/Users/Albert/.gemini/antigravity/brain/3b620b1f-7281-460b-a2ff-2eecc0398bcd/cli_wishlist_table.png)
Figure 3.8: Command line output showing populated records in the WISHLIST table.

![Figure 3.9: CLI Screenshot - SAVED_LISTINGS Table Output](file:///C:/Users/Albert/.gemini/antigravity/brain/3b620b1f-7281-460b-a2ff-2eecc0398bcd/cli_saved_table.png)
Figure 3.9: Command line output showing populated records in the SAVED_LISTINGS table.

### 3.4 Relationships and Normalization
- LISTINGS.owner_id references USERS(user_id) (One User to Many Listings).
- LISTINGS.category_id references CATEGORIES(category_id) (One Category to Many Listings).
- RENTAL_REQUESTS.listing_id references LISTINGS(listing_id) and borrower_id references USERS(user_id).
- RENTAL_TRANSACTIONS.request_id references RENTAL_REQUESTS(request_id) (One-to-One Unique Relationship).
- MAINTENANCE.listing_id references LISTINGS(listing_id).
- REVIEWS.transaction_id references RENTAL_TRANSACTIONS(transaction_id).

Normalization: All entities satisfy 3rd Normal Form (3NF). Every non-key field depends solely on the primary key, eliminating transitive and partial dependencies.

### 3.5 Entity Relationship (ER) Diagram (Chen Notation)
![Figure 3.10: Entity Relationship (ER) Diagram](file:///C:/Users/Albert/.gemini/antigravity/brain/3b620b1f-7281-460b-a2ff-2eecc0398bcd/er_diagram.png)

---

## 4. DATABASE OPERATIONS AND SQL IMPLEMENTATION

### 4.1 Table Creation DDL (SQLite and MySQL Syntax)
USERS Table Creation:
SQLite Syntax (CampusLink Live Engine):
CREATE TABLE IF NOT EXISTS users (
 user_id INTEGER PRIMARY KEY AUTOINCREMENT,
 name TEXT NOT NULL,
 email TEXT UNIQUE NOT NULL CHECK(email LIKE '%@umat.edu.gh' OR email LIKE '%@student.umat.edu.gh'),
 password_hash TEXT NOT NULL,
 student_id TEXT UNIQUE,
 phone TEXT NOT NULL,
 verification_level TEXT NOT NULL DEFAULT 'Unverified'
 CHECK(verification_level IN ('Unverified', 'Verified Student', 'Verified Staff', 'Admin')),
 account_status TEXT NOT NULL DEFAULT 'Active'
 CHECK(account_status IN ('Active', 'Suspended', 'Pending Verification')),
 department TEXT NOT NULL,
 hostel TEXT,
 last_login DATETIME,
 created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

MySQL 8.0 Equivalent Syntax:
CREATE TABLE IF NOT EXISTS users (
 user_id INT AUTO_INCREMENT PRIMARY KEY,
 name VARCHAR(255) NOT NULL,
 email VARCHAR(255) UNIQUE NOT NULL,
 password_hash VARCHAR(255) NOT NULL,
 student_id VARCHAR(50) UNIQUE,
 phone VARCHAR(30) NOT NULL,
 verification_level ENUM('Unverified', 'Verified Student', 'Verified Staff', 'Admin') DEFAULT 'Unverified',
 account_status ENUM('Active', 'Suspended', 'Pending Verification') DEFAULT 'Active',
 department VARCHAR(150) NOT NULL,
 hostel VARCHAR(150) DEFAULT NULL,
 last_login DATETIME DEFAULT NULL,
 created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
 CONSTRAINT chk_email CHECK (email LIKE '%@umat.edu.gh' OR email LIKE '%@student.umat.edu.gh')
) ENGINE=InnoDB;

LISTINGS Table Creation:
CREATE TABLE IF NOT EXISTS listings (
 listing_id INTEGER PRIMARY KEY AUTOINCREMENT,
 owner_id INTEGER NOT NULL,
 category_id INTEGER NOT NULL,
 title TEXT NOT NULL,
 description TEXT,
 subcategory TEXT NOT NULL,
 brand TEXT NOT NULL,
 model TEXT NOT NULL,
 rental_rate_per_day REAL NOT NULL CHECK(rental_rate_per_day >= 0),
 deposit_amount REAL NOT NULL CHECK(deposit_amount >= 0),
 condition TEXT NOT NULL CHECK(condition IN ('New', 'Good', 'Fair', 'Poor')),
 status TEXT NOT NULL DEFAULT 'Available'
 CHECK(status IN ('Available', 'Reserved', 'Rented', 'Maintenance', 'Delisted')),
 pickup_location TEXT NOT NULL,
 thumbnail_path TEXT,
 available_from TEXT NOT NULL,
 available_until TEXT NOT NULL,
 FOREIGN KEY (owner_id) REFERENCES users (user_id) ON DELETE CASCADE,
 FOREIGN KEY (category_id) REFERENCES categories (category_id) ON DELETE CASCADE
);

### 4.2 Data Insertion (DML)
INSERT INTO users (name, email, password_hash, student_id, phone, verification_level, department, hostel)
VALUES ('Albert Boateng', 'albert@student.umat.edu.gh', 'pbkdf2_sha256$100000$umat...$hash', 'UMT-2021-0001', '+233241234567', 'Verified Student', 'Geomatic Engineering', 'Chamber of Mines Hostel');

INSERT INTO listings (owner_id, category_id, title, subcategory, brand, model, rental_rate_per_day, deposit_amount, condition, status, pickup_location, available_from, available_until)
VALUES (1, 1, 'Leica Total Station TS07', 'Total Station', 'Leica', 'TS07', 150.00, 500.00, 'Good', 'Available', 'KT Hall Room B12', '2026-08-01', '2026-12-31');

### 4.3 Schema Modification (ALTER TABLE)
-- Demonstrate Adding a Column
ALTER TABLE users ADD COLUMN bio TEXT DEFAULT 'UMaT Student';

-- Demonstrate Dropping a Column (Compatibility helper in database_schema.py)
ALTER TABLE users DROP COLUMN bio;

### 4.4 Data Update and Delete Operations
-- UPDATE Statement
UPDATE users SET verification_level = 'Verified Student' WHERE user_id = 3;

-- DELETE Statement
DELETE FROM users WHERE email = 'temp_user@student.umat.edu.gh';

### 4.5 Data Selection and Ordering (SELECT, ORDER BY)
-- Ascending Order
SELECT title, rental_rate_per_day, condition FROM listings ORDER BY rental_rate_per_day ASC;

-- Descending Order
SELECT title, deposit_amount FROM listings ORDER BY deposit_amount DESC;

### 4.6 Data Integrity Constraints and Aggregate Functions

Constraint Type | Table / Field Applied | Significance
--- | --- | ---
PRIMARY KEY | user_id, listing_id, request_id, etc. | Uniquely identifies each row in every table.
FOREIGN KEY | listings.owner_id, rental_transactions.request_id | Maintains referential integrity and prevents orphan records.
UNIQUE | users.email, users.student_id | Prevents duplicate student registrations.
NOT NULL | users.name, listings.title, listings.rental_rate_per_day | Ensures critical fields are never left blank.
CHECK | users.email domain, listings.rental_rate_per_day >= 0 | Rejects logically invalid data at the database engine level.
DEFAULT | users.verification_level ('Unverified') | Assigns standard default values automatically.

Aggregate Functions Execution:
SELECT COUNT(ALL) AS total_listings FROM listings;
SELECT SUM(gross_amount) AS total_gross_revenue FROM rental_transactions;
SELECT AVG(rental_rate_per_day) AS avg_daily_rate FROM listings;
SELECT MIN(rental_rate_per_day) AS min_rate, MAX(rental_rate_per_day) AS max_rate FROM listings;
SELECT DISTINCT category_id FROM listings;

### 4.7 Relational Join Operations (INNER, LEFT, RIGHT Emulation)

#### 1. Inner Join
SELECT t.transaction_id, u.name AS borrower, l.title AS item, t.gross_amount
FROM rental_transactions t
INNER JOIN users u ON t.borrower_id = u.user_id
INNER JOIN listings l ON t.listing_id = l.listing_id;

![Figure 4.1: CLI Screenshot - INNER JOIN Query Output](file:///C:/Users/Albert/.gemini/antigravity/brain/3b620b1f-7281-460b-a2ff-2eecc0398bcd/cli_inner_join.png)
Figure 4.1: Command line output executing an INNER JOIN query.

#### 2. Left Join (Un-borrowed Listings)
SELECT l.listing_id, l.title, t.transaction_id
FROM listings l
LEFT JOIN rental_transactions t ON l.listing_id = t.listing_id
WHERE t.transaction_id IS NULL;

![Figure 4.2: CLI Screenshot - LEFT JOIN Query Output](file:///C:/Users/Albert/.gemini/antigravity/brain/3b620b1f-7281-460b-a2ff-2eecc0398bcd/cli_left_join.png)
Figure 4.2: Command line output executing a LEFT JOIN query.

#### 3. Right Join Emulation (SQLite Swapped Table Order)
-- Emulates 'listings RIGHT JOIN users' in SQLite by reversing table order:
SELECT u.name AS user_name, l.title AS owned_item
FROM users u
LEFT JOIN listings l ON u.user_id = l.owner_id;

![Figure 4.3: CLI Screenshot - RIGHT JOIN Emulation Query Output](file:///C:/Users/Albert/.gemini/antigravity/brain/3b620b1f-7281-460b-a2ff-2eecc0398bcd/cli_right_join.png)
Figure 4.3: Command line output executing a RIGHT JOIN emulation query.

### 4.8 Wildcards and LIKE Statements
-- 1. Prefix Match (Names starting with 'A')
SELECT name, email FROM users WHERE name LIKE 'A%';

-- 2. Suffix Match (Official student emails)
SELECT name, email FROM users WHERE email LIKE '%@student.umat.edu.gh';

-- 3. Substring Match (Equipment containing 'GPS')
SELECT title, description FROM listings WHERE description LIKE '%GPS%';

---

## 5. GRAPHICAL USER INTERFACE (GUI) IMPLEMENTATION

### 5.1 Design Overview and Architecture
The GUI was constructed using Python 3 and PySide6 (Qt6). The interface employs a responsive multi-tab layout (QStackedWidget and sidebar navigation) supporting dynamic dark and light visual themes (CampusLinkTheme).

### 5.2 How the GUI Interacts with the Database
Every GUI action invokes parameterized helper controller functions in controllers.py, executing safe SQL queries:
- Add Listing / Submit Request: Translates form input into INSERT INTO queries using parameterized tuple bindings (?, ?).
- Approve Request / Return Item: Executes atomic UPDATE statements modifying listing and transaction status records.
- Delete Record: Executes DELETE FROM ... WHERE id = ?.
- Search and View: Executes parameterized SELECT queries and repopulates Qt item cards and data tables in real time.

### 5.3 Interface Screenshots and Descriptions

![Figure 5.1: CampusLink Main Dashboard View](file:///C:/Users/Albert/.gemini/antigravity/brain/3b620b1f-7281-460b-a2ff-2eecc0398bcd/dashboard_view.png)
Figure 5.1: CampusLink Main Dashboard View
Figure 5.1 shows the main student dashboard displaying active rental counts, trust score badge (92/100), dark UI theme toggle, and navigation sidebar.

![Figure 5.2: Marketplace Equipment Directory View](file:///C:/Users/Albert/.gemini/antigravity/brain/3b620b1f-7281-460b-a2ff-2eecc0398bcd/marketplace_view.png)
Figure 5.2: Marketplace Equipment Directory View
Figure 5.2 displays the marketplace grid. Product images scale using Qt.KeepAspectRatio inside dark containers #0F172A without cropping product details, featuring View Details and Rent Now action buttons.

![Figure 5.3: My Listings and Incoming Requests Interface](file:///C:/Users/Albert/.gemini/antigravity/brain/3b620b1f-7281-460b-a2ff-2eecc0398bcd/listings_view.png)
Figure 5.3: My Listings and Incoming Requests Interface
Figure 5.3 illustrates the owner management view showing listed equipment items and incoming rental requests with one-click Approve buttons.

![Figure 5.4: Business Intelligence Reports Interface](file:///C:/Users/Albert/.gemini/antigravity/brain/3b620b1f-7281-460b-a2ff-2eecc0398bcd/reports_view.png)
Figure 5.4: Business Intelligence Reports Interface
Figure 5.4 displays the administrative reporting panel rendering 15 Business Intelligence analytical queries in real-time data tables.

![Figure 5.5: Administrator Control Panel](file:///C:/Users/Albert/.gemini/antigravity/brain/3b620b1f-7281-460b-a2ff-2eecc0398bcd/admin_view.png)
Figure 5.5: Administrator Control Panel
Figure 5.5 shows the administration module for managing student verification levels and account statuses.

---

## 6. SYSTEM TESTING AND VERIFICATION

### 6.1 Automated Test Results (100/100 Passed)
An end-to-end regression test suite (tests/end_to_end_test.py) was executed to verify all system components.

![Figure 6.1: Automated Test Verification Results Summary](file:///C:/Users/Albert/.gemini/antigravity/brain/3b620b1f-7281-460b-a2ff-2eecc0398bcd/test_results_summary.png)
Figure 6.1: Automated test summary chart showing 100/100 tests passed across all 12 test sections.

### 6.2 Workflow Verification
1. P2P Rental Lifecycle: Submit Request -> Status Pending -> Lender Approves -> Status Approved -> Listing Reserved -> Transaction Active -> Return Item -> Listing Available -> Peer Reviews logged -> VERIFIED
2. Damage Lifecycle: Return with Damage -> Listing Maintenance -> Ticket Auto-Created -> Repair Completed -> Listing Available -> VERIFIED

---

## 7. CONCLUSION
This project successfully demonstrated practical competence across the full range of relational database systems skills taught in the Database Systems (CE/IS/CY 170) course. The CampusLink platform was designed with 9 normalized tables, populated with realistic campus rental data, and modified through column-level (ALTER TABLE) and record-level (UPDATE, DELETE) operations. Data integrity was strictly enforced via primary/foreign keys and 17 CHECK/UNIQUE domain rules. Data was retrieved and organized using SELECT, ORDER BY, LIKE wildcards, aggregate functions, and INNER/LEFT/RIGHT table joins. Finally, an interactive PySide6 GUI was developed, allowing non-technical campus users to perform equipment rentals smoothly. All assignment specifications were satisfied and verified with a 100% test pass rate.

---

## REFERENCES
1. Oracle Corporation (2026). MySQL 8.0 Reference Manual. Oracle Documentation.
2. Python Software Foundation (2026). Hashlib - Secure hashes and message digests (PBKDF2). Python 3 Documentation.
3. Qt Group (2024). PySide6 / Qt for Python GUI Framework Documentation. https://doc.qt.io/qtforpython-6/
4. Hipp, D. R. (2020). SQLite Architecture and Internal Design. SQLite Consortium. https://www.sqlite.org/arch.html
5. National Institute of Standards and Technology (NIST) (2017). Digital Identity Guidelines: Authentication and Lifecycle Management (NIST SP 800-63B). U.S. Department of Commerce.
6. Silberschatz, A., Korth, H. F., and Sudarshan, S. (2020). Database System Concepts (7th ed.). McGraw-Hill Education.
