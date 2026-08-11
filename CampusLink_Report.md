# CampusLink — Academic Project & System Documentation
**A Peer-to-Peer Student Resource Sharing Platform**
*University of Mines and Technology (UMaT), Tarkwa, Ghana*

---

## 1. Executive Summary

CampusLink is an autonomous, peer-to-peer resource sharing platform developed for the University of Mines and Technology (UMaT), Tarkwa. The platform enables university students and staff to list, rent, borrow, and monetize underutilized educational resources, surveying instruments, laboratory equipment, hostel appliances, and mining gear. By acting strictly as a marketplace facilitator rather than an inventory owner, CampusLink charges a 10% platform commission on completed exchanges while fostering a collaborative campus economy. The project demonstrates the practical application of relational database design, third normal form (3NF) schema optimization, complex SQL operations, business intelligence reporting, and modern GUI development using Python, SQLite, and Tkinter.

---

## 2. Problem Statement

At higher learning institutions such as UMaT, students across various engineering disciplines (Geomatic, Mining, Petroleum, Electrical, Geological) are frequently required to purchase high-cost specialized tools—such as Leica Total Stations, rock hammers, oscilloscopes, and handheld GPS units—that are only utilized during specific weeks of a semester. Concurrently, many students lack the financial resources to purchase these mandatory tools, creating academic disparities and financial strain. Existing assets remain idle in student hostels for long periods, while other students struggle to access them. CampusLink solves this problem by creating a trusted, transparent peer-to-peer marketplace where students can monetize idle resources safely, borrow essential equipment at affordable daily rates, and maintain accountability through automated trust scoring and deposit handling.

---

## 3. Project Objectives

### General Objective
Design and implement a robust, database-driven peer-to-peer resource sharing marketplace for UMaT students and staff.

### Specific Objectives
1. **User & Identity Management**: Enforce institutional email validation (`@umat.edu.gh` and `@student.umat.edu.gh`) with tiered verification levels (Unverified, Verified Student, Verified Staff, Admin).
2. **Resource Cataloging**: Enable students to list items with flexible daily rental rates, security deposit bounds, availability windows, and condition classifications.
3. **Transaction Lifecycle Management**: Automate the multi-stage rental workflow (*List → Request → Approve → Active Transaction → Return → Two-Way Rating*).
4. **Financial Calculations**: Automatically calculate rental durations, gross costs, 10% platform commissions, and 90% owner earnings upon request approval.
5. **Damage & Maintenance Tracking**: Track equipment repairs, log cost allocations against held security deposits, and isolate damaged items from active search results.
6. **Business Intelligence Reporting**: Implement 15 specialized SQL analytical queries providing actionable campus insights and exportable CSV reports.

---

## 4. System Architecture

CampusLink is designed following the Model-View-Controller (MVC) architectural pattern:

```
                  ┌─────────────────────────────────────────┐
                  │               USER (GUI)                │
                  └────────────────────┬────────────────────┘
                                       │
                                       ▼
                  ┌─────────────────────────────────────────┐
                  │          VIEW LAYER (main.py)           │
                  │   Tkinter Desktop GUI, Toast Banner,    │
                  │   Demo Switcher, Interactive Tables     │
                  └────────────────────┬────────────────────┘
                                       │
                                       ▼
                  ┌─────────────────────────────────────────┐
                  │    CONTROLLER LAYER (controllers.py)    │
                  │    P2P Business Logic, Trust Score,     │
                  │    15 BI Reports, Financial Calculations│
                  └────────────────────┬────────────────────┘
                                       │
                                       ▼
                  ┌─────────────────────────────────────────┐
                  │      MODEL LAYER (database_schema.py)   │
                  │     9-Table 3NF DDL, Check Constraints, │
                  │     SQLite DROP COLUMN Compatibility     │
                  └────────────────────┬────────────────────┘
                                       │
                                       ▼
                  ┌─────────────────────────────────────────┐
                  │           DATABASE (SQLite 3)           │
                  │           database/campuslink_umat.db   │
                  └─────────────────────────────────────────┘
```

---

## 5. Relational Database Design (9 Tables)

The database structure adheres to Third Normal Form (3NF) to minimize redundancy and guarantee data integrity.

### 5 Core Business Tables
1. **`users`**: Stores user credentials, contact details, verification levels, department, and hostel assignment.
2. **`listings`**: Stores resources available for rent, daily rates, security deposits, pickup location, and availability dates.
3. **`rental_requests`**: Stores rental booking requests submitted by borrowers, including purpose and date range.
4. **`rental_transactions`**: Stores active and historical rental exchanges, gross revenue, 10% commission, owner earnings, and return statuses.
5. **`maintenance`**: Logs equipment damage reports, repair cost allocations, and maintenance lifecycle statuses.

### 4 Normalized Supporting Tables
6. **`categories`**: Equipment taxonomy (Computing, Surveying, Mining PPE, Geology, Lab Tools, etc.).
7. **`reviews`**: Two-way peer feedback (ratings 1–5 and comments) between lenders and borrowers.
8. **`wishlist`**: Automated keyword and category alerts for items students want to rent.
9. **`saved_listings`**: Individual student bookmarks for quick access.

---

## 6. SQL Operations & Technical Demonstration

| SQL Operation | Implementation Site | Purpose |
|---|---|---|
| **DDL (`CREATE TABLE`)** | `database/database_schema.py` | Defines 9 tables with `CHECK`, `FOREIGN KEY`, `NOT NULL`, and `DEFAULT` constraints. |
| **Integrity Constraints** | `users.email`, `listings.rental_rate_per_day` | Rejects non-UMaT emails (`CHECK(email LIKE '%@%.umat.edu.gh')`) and negative rates. |
| **ALTER TABLE (ADD/DROP)** | `database/database_schema.py` | Demonstrates schema evolution; includes native SQLite 3.35+ drop and table-recreation fallback for older engines. |
| **DML (`INSERT`, `UPDATE`, `DELETE`)** | `controllers.py` | Handles new user registrations, listing delistings, request approvals, and status transitions. |
| **Aggregates (`SUM`, `AVG`, `COUNT`, `MIN`, `MAX`)** | `controllers.get_report_data()` | Powers BI reports calculating total revenue, average daily rates, and total active listings. |
| **INNER JOIN** | Report 01, 02, 03, 04, 07 | Combines `rental_transactions`, `users`, `listings`, and `categories` for unified data views. |
| **LEFT JOIN** | Report 06 (Un-rented items) | Identifies listings with no matching rental transaction (`WHERE t.transaction_id IS NULL`). |
| **RIGHT JOIN Emulation** | `tests/verify_db.py` | Emulates `RIGHT JOIN` by swapping table positions in a `LEFT JOIN` query. |
| **Wildcard Searches (`LIKE`)** | `controllers.get_filtered_listings()` | Case-insensitive keyword searching across title, description, brand, and model. |
| **Subqueries** | `controllers.get_filtered_listings()` | Filters out items actively rented during requested booking date overlaps. |

---

## 7. End-to-End Demonstration Storyboard

### Storyboard: The Field Practical Equipment Exchange
> **Characters**: 
> - **Benedict Osei** (Final Year Mining Engineering student residing at Gold Refinery Hostel)
> - **Albert Boateng** (Geomatic Engineering student residing at Chamber of Mines Hostel)

1. **The Need**: Benedict is preparing for a mandatory 3-day field exercise in Tarkwa but does not own a total station. Buying a new unit costs over GH₵ 15,000.
2. **Search & Request**: Benedict opens CampusLink, selects *Surveying Equipment*, sets date filters (Aug 25 to Aug 27), and finds Albert's **Leica Total Station TS07** listed at GH₵ 120.00 / day. Benedict clicks **Request Rental**.
3. **Approval & Financial Lock**: Albert receives an instant notification under *My Listings & Requests*. He clicks **Approve**. CampusLink automatically:
   - Locks the listing status to `Reserved`.
   - Generates Transaction ID #5.
   - Calculates **Gross Amount**: GH₵ 360.00 (3 days × GH₵ 120.00).
   - Calculates **CampusLink Commission (10%)**: GH₵ 36.00.
   - Calculates **Albert's Net Earnings (90%)**: GH₵ 324.00.
   - Holds a **Security Deposit**: GH₵ 500.00.
4. **Physical Exchange & Return**: Benedict collects the equipment, completes his field practical, and returns the Leica TS07 on time. Albert inspects the unit, finds it in perfect condition, and processes the return.
5. **Rating & Reputation**: Benedict rates Albert 5 stars ("*Pristine equipment, highly recommended!*"). Albert rates Benedict 5 stars ("*Handled with extreme care.*"). Albert's Trust Score increases to **92/100**.
6. **Platform Intelligence**: CampusLink Report 01 immediately reflects the GH₵ 36.00 platform revenue increment.

---

## 8. Business Intelligence Reports (15 Analytical Views)

1. **Platform Revenue Summary**: Total transactions, gross volume, commission earned, net owner payout.
2. **Top Earning Lenders**: Lenders ranked by total net earnings (`GROUP BY owner_id ORDER BY SUM`).
3. **Most Active Borrowers**: Students ranked by completed transactions (`GROUP BY borrower_id`).
4. **Revenue by Category**: Category performance Breakdown (`INNER JOIN categories`).
5. **Listings With Zero Rentals**: Unmonetized assets requiring price optimization (`LEFT JOIN WHERE NULL`).
6. **Current Availability Status**: Breakdown of items (*Available*, *Reserved*, *Rented*, *Maintenance*).
7. **Late Returns Analysis**: Overdue tracking comparing `actual_return_date` to `rent_end_date`.
8. **Damage & Maintenance Log**: Repair ticket summary and total maintenance expenditures.
9. **Rentals by Purpose**: Utilization distribution (*Field Trip*, *Lab Session*, *Final Year Project*).
10. **Category Utilization Rate**: Percentage of listed equipment currently rented out per category.
11. **Lender Trust Leaderboard**: Top-rated lenders based on average peer reviews.
12. **Borrower Reliability Ranking**: Top-rated borrowers based on return punctuality.
13. **Hostel Activity Map**: Item distribution across UMaT hostels (*Chamber of Mines*, *Gold Refinery*, *K.T. Hall*).
14. **Monthly Revenue Trend**: Revenue growth grouped by month (`strftime('%Y-%m', created_at)`).
15. **Overdue Returns**: Active rentals exceeding end dates requiring administrative follow-up.

---

## 9. Future Enhancements

Looking beyond the current assignment scope, CampusLink can evolve into a full-scale commercial university enterprise through the following technical additions:

1. **Mobile Application (Flutter / React Native)**: Cross-platform iOS and Android app with instant push notifications for rental request approvals.
2. **Mobile Money API Integration (MTN MoMo / Telecel Cash)**: Automated escrow payment processing in Ghana Cedis (GHS) via Paystack/Hubtel APIs.
3. **QR Code Handover Verification**: Physical check-in/check-out scanning where lender and borrower scan a dynamic QR code on handover to prevent disputed return times.
4. **SMS & WhatsApp Reminders (Twilio / Arkesel)**: Automated SMS notifications 24 hours prior to rental due dates to prevent late returns.
5. **AI-Powered Dynamic Pricing & Recommendations**: Machine learning model analyzing seasonal campus demand (e.g., examination weeks, field trips) to suggest optimal daily rates to lenders.
6. **Asset RFID / Barcode Tagging**: Physical barcode sticker integration for rapid laboratory inventory audits and instant asset lookup.

---

## 10. Project Directory Structure

```
CAMPUS_LINK/
│
├── database/
│   ├── database_schema.py   # 9-Table 3NF DDL, Constraints, Indexes, Drop Column
│   ├── db_seeder.py         # Realistic UMaT Demo Data Population Script
│   └── campuslink_umat.db   # Active SQLite Database File
│
├── tests/
│   ├── verify_db.py         # SQL Operations Compliance Verifier
│   └── end_to_end_test.py   # 100-Test Automated Validation Suite
│
├── assets/
│   └── logo.jpg             # Circular CampusLink Brand Logo Badge
│
├── controllers.py           # Controller Layer: Logic, Trust Score, 15 Reports
├── main.py                  # View Layer: Tkinter GUI, Toast System, Live Clock
├── db_schema.py             # Root Compatibility Forwarder
├── db_seeder.py             # Root Compatibility Forwarder
├── verify_db.py             # Root Compatibility Forwarder
├── end_to_end_test.py       # Root Compatibility Forwarder
├── README.md                # Submission & Quick-Start Guide
└── CampusLink_Report.md     # Full Academic System Documentation
```

---

## 11. Conclusion

CampusLink successfully addresses the challenge of resource accessibility at the University of Mines and Technology by replacing expensive personal ownership with an efficient, peer-to-peer sharing economy. The platform demonstrates that a well-designed relational database model—enforced by robust constraints, normalized tables, comprehensive SQL logic, and an intuitive user interface—can solve real-world student challenges while providing administrators with rich business intelligence insights.
