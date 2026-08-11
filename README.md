# CampusLink
### _Rent. Borrow. Lend. Earn._
**A Peer-to-Peer Student Resource Marketplace for the University of Mines and Technology (UMaT), Tarkwa, Ghana**

---

## Executive Summary

CampusLink is an autonomous, peer-to-peer resource sharing platform developed for the University of Mines and Technology (UMaT). The platform enables university students and staff to rent, borrow, lend, and monetize educational tools, surveying equipment, laboratory gear, and hostel appliances. CampusLink does not own items; it facilitates peer exchanges and charges a **10% platform commission** on completed rentals.

---

## Project Structure

```
CAMPUS_LINK/
│
├── database/
│   ├── database_schema.py   # 9-Table DDL, Constraints, Indexes, Drop Column
│   ├── db_seeder.py         # Realistic UMaT Demo Data Population Script
│   └── campuslink_umat.db   # Active SQLite Database File
│
├── tests/
│   ├── verify_db.py         # SQL Operations Compliance Verifier
│   └── end_to_end_test.py   # 100-Test Automated Validation Suite
│
├── assets/
│   └── logo.jpg             # CampusLink Circular Badge Brand Logo
│
├── controllers.py           # Business Logic, Trust Score, Financials, 15 Reports
├── main.py                  # Tkinter Desktop GUI, Toast System, Live Clock
├── CampusLink_Report.md     # Full Academic Documentation & System Specs
├── README.md                # Quick-Start & Operational Manual
├── db_schema.py             # Root Compatibility Forwarder
├── db_seeder.py             # Root Compatibility Forwarder
├── verify_db.py             # Root Compatibility Forwarder
└── end_to_end_test.py       # Root Compatibility Forwarder
```

---


---

## 🔐 Preset Demo Accounts & Credentials

| Role | Name | Institutional Email | Password | Primary Use Case |
|---|---|---|---|---|
| **Administrator** | Admin CampusLink | `admin@umat.edu.gh` | `Admin123` | Platform oversight, system management |
| **Student** | Albert Boateng | `albert@student.umat.edu.gh` | `Student123` | Verified student, owns Leica Total Station & Dell XPS |
| **Student** | Benedict Osei | `benedict@student.umat.edu.gh` | `Student123` | Verified student, owns PPE Kit & Mini Fridge |
| **Student** | Grace Mensah | `grace@student.umat.edu.gh` | `Student123` | Active borrower, petroleum engineering student |
| **Staff** | Dr. Kwame Asante | `kasante@umat.edu.gh` | `Staff123` | Verified lecturer, owns Oscilloscope & Multimeter |
| **Student** | Abena Owusu | `abena@student.umat.edu.gh` | `Student123` | Unverified student account for testing validation |

---

## 🛡️ Password Hashing & Security Architecture

CampusLink implements **PBKDF2-HMAC-SHA256** password hashing using Python's built-in `hashlib` library:
- **Hash Function**: PBKDF2 with HMAC-SHA256
- **Work Factor**: 100,000 key derivation iterations
- **Salting**: Dynamic per-system salt (`umat_campuslink_2026`)
- **Storage Format**: `pbkdf2_sha256$100000$salt$hash_hex`
- **Login Auditing**: Automatic timestamp logging on successful authentication (`users.last_login`)

## Quick Start Guide

### 1. Initialize & Seed Database
```powershell
python db_seeder.py
```

### 2. Launch Desktop GUI
```powershell
python main.py
```

### 3. Run Automated Validation Test Suite
```powershell
python end_to_end_test.py
```
*Expected Result*: **100/100 Tests PASSED (100% Coverage)**

---

## Database Design Overview

### Core Business Tables (5 Tables)
- **`users`**: Account credentials, contact details, verification levels, department, hostel.
- **`listings`**: Items posted for rent, daily rates, security deposit, pickup location, availability dates.
- **`rental_requests`**: Booking requests submitted by borrowers, purpose, date range.
- **`rental_transactions`**: Confirmed rentals, gross total, 10% commission, net earnings, return status.
- **`maintenance`**: Damage reports, repair ticket costs, and maintenance lifecycle.

### Normalized Supporting Tables (4 Tables)
- **`categories`**: Taxonomy (Computing, Surveying, Mining PPE, Geology Field, Lab Tools, etc.).
- **`reviews`**: Two-way peer rating system (1–5 stars and comments).
- **`wishlist`**: Watched category and keyword alert notifications.
- **`saved_listings`**: Student bookmarks for quick access.

---

## SQL Operations Demonstrated

| Category | Operation | Example Usage |
|---|---|---|
| DDL | `CREATE TABLE`, `CREATE INDEX` | 9-table schema creation with 6 optimization indexes |
| Constraints | `CHECK`, `NOT NULL`, `UNIQUE`, `FOREIGN KEY` | UMaT email validation, non-negative pricing, enum checks |
| Evolution | `ALTER TABLE ADD/DROP COLUMN` | Version-aware column drop (native v3.35+ / recreation fallback) |
| DML | `INSERT`, `UPDATE`, `DELETE` | Request submissions, approvals, returns, and delistings |
| Aggregates | `COUNT`, `SUM`, `AVG`, `MIN`, `MAX` | Platform revenue, category averages, total items |
| Joins | `INNER JOIN`, `LEFT JOIN`, `RIGHT JOIN` | Transaction reports, un-borrowed items, right join emulation |
| Wildcards | `LIKE` (prefix, suffix, contains) | Keyword search bar, email domain validation |
| Subqueries | Overlap Detection | Filtering out actively rented items during selected date ranges |

---

## Presentation & Demonstration Scenario

To demonstrate CampusLink effectively during your project evaluation:

1. **Launch GUI**: `python main.py`
2. **Demo Switcher**: Select **Albert Boateng** (Lender) from the top-right header switcher.
3. **Search & Request**: Switch to **Benedict Osei** (Borrower) -> go to **Search Marketplace** -> filter *Surveying Equipment* -> click **Request Rental** on Albert's *Leica Total Station TS07*.
4. **Approve**: Switch back to **Albert** -> go to **My Listings & Requests** -> click **Approve & Lock Transaction**. Note the calculated 10% commission (GH₵ 36.00) and net earnings (GH₵ 324.00).
5. **Return & Review**: Process return as Good -> submit mutual 5-star reviews.
6. **Reports**: Open **Campus Intelligence Reports** -> select **Report 01: Platform Revenue Summary** -> click **Export Report to CSV**.

---

## Academic Documentation

For complete technical specifications, problem statement, objectives, and future enhancement plans, refer to:
- [CampusLink_Report.md](file:///c:/Users/Albert/Desktop/CAMPUS_LINK/CampusLink_Report.md)

---

_CampusLink — Rent. Borrow. Lend. Earn._
_University of Mines and Technology (UMaT), Tarkwa, Ghana_
