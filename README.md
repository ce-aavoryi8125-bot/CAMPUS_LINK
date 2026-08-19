# CampusLink 2.0 — Enterprise P2P Student Equipment & Services Marketplace

[![Build Status](https://img.shields.io/badge/Unit%20Tests-127%2F127%20Passed-brightgreen.svg)](tests/)
[![E2E Suite](https://img.shields.io/badge/Master%20E2E-106%2F106%20Passed-brightgreen.svg)](tests/end_to_end_test.py)
[![Database](https://img.shields.io/badge/Database-MySQL%209.7%20%7C%20SQLite%203-blue.svg)](database/)
[![Security](https://img.shields.io/badge/Auth-PBKDF2--HMAC--SHA256-orange.svg)](core/security.py)
[![Financial Invariants](https://img.shields.io/badge/Ledger-Double--Entry%20Balanced-success.svg)](core/wallet_service.py)

**CampusLink 2.0** is an enterprise-grade, peer-to-peer equipment rental and student micro-services platform tailored specifically for collegiate academic and campus ecosystems (pioneered for the **University of Mines and Technology, UMaT, Tarkwa, Ghana**).

Designed with robust engineering discipline, CampusLink incorporates a dual-dialect database abstraction layer, a strict double-entry custodial financial ledger, distributed Redis sliding-window rate limiting, asynchronous Celery task pipelines, and hardened containerization.

---

## Architecture Overview

```
                                  ┌───────────────────────────────┐
                                  │      Nginx Reverse Proxy      │
                                  │  (Port 80 / Security Headers) │
                                  └───────────────┬───────────────┘
                                                  │
                                  ┌───────────────▼───────────────┐
                                  │    Gunicorn / Flask Web App   │
                                  │ (Non-root campuslink UID 10001│
                                  └───────┬───────────────┬───────┘
                                          │               │
                     ┌────────────────────┴──────┐ ┌──────┴────────────────────┐
                     │                           │ │                           │
             ┌───────▼───────┐           ┌───────▼───────┐             ┌───────▼───────┐
             │  Redis 8.1.0  │           │ Celery Worker │             │ MySQL 8+ / 9.7│
             │ (Lua Limiter  │◄──────────┤ & Celery Beat │◄────────────┤ (15 Tables    │
             │  & Broker)    │           │ (Async Tasks) │             │  InnoDB / FK) │
             └───────────────┘           └───────────────┘             └───────────────┘
```

---

## Key System Modules & Architectural Capabilities

### 1. Dual-Dialect Relational Database Engine (`db_engine.py`)
* **Physical MySQL 8.0+ / 9.7 Support**: Tested and verified on physical MySQL Server Ver 9.7.0 with InnoDB tables, `utf8mb4` character encoding, foreign keys (`ON DELETE RESTRICT`), and ANSI `ONLY_FULL_GROUP_BY` compliance.
* **Offline SQLite 3 Development Engine**: Zero-dependency local developer workflow that automatically translates queries (`?` $\leftrightarrow$ `%s`, `INSERT OR IGNORE` $\leftrightarrow$ `INSERT IGNORE`, keyword escaping).
* **Atomic Transaction Management**: Context-managed atomic execution (`with db_engine.transaction() as tx:`) guaranteeing ACID guarantees across both engines.

### 2. Dual-Sided Double-Entry Financial Ledger (`core/wallet_service.py`)
* **Strict Double-Entry Accounting**: Every monetary event (deposit, escrow hold, commission cut, earning release, refund, withdrawal) creates equal and opposite `DEBIT` and `CREDIT` records.
* **Zero-ID Invariant**: Transactions referencing `user_id = 0` or `wallet_id = 0` are strictly blocked ($\text{COUNT} \equiv 0$).
* **Segregated System Vaults**:
  - **Account `6`**: Platform Commission Vault (10% platform fee on completed rentals).
  - **Account `7`**: System Escrow Custody Account (holds security deposits and gross rental payments during active hires).
  - **Account `8`**: Mobile Money (MoMo) Gateway Clearinghouse (settles incoming student deposits and outgoing disbursements).

### 3. Distributed Sliding-Window Rate Limiter (`core/rate_limiter.py`)
* **Atomic Redis Lua Scripting**: Atomic sliding-window rate limiting executed inside Redis to prevent race conditions across multi-worker deployments.
* **Graceful Thread-Safe In-Memory Fallback**: When Redis is unreachable in local development, transparently falls back to an in-memory sliding-window limiter without crashing the application.
* **Granular Endpoint Tiers**: Strict per-IP/user limits applied to Authentication (`/login`, `/register`), Webhooks (`/api/v1/payments/momo/webhook`), and General API routes.

### 4. Asynchronous Background Tasks & Celery Scheduler (`tasks/`)
* **Asynchronous Mobile Money Webhooks**: Dedicated Celery tasks process and settle high-volume payment callbacks asynchronously.
* **Automated Scheduled Financial Reconciliation**: Daily background audit comparing gateway balances against the dual-entry ledger.
* **Overdue Rental Sweeper**: Nightly Celery Beat task identifying overdue equipment rentals and dispatching automated reminders.
* **Database-Level Idempotency**: All task execution is bounded by database-level unique constraints and idempotency keys to prevent duplicate transaction settlement on worker retry.

### 5. Production Configuration, Strict Secrets & Probes (`core/config.py`, `app.py`)
* **Fast-Fail Production Validation**: In production mode (`CAMPUSLINK_ENV=production`), startup fails immediately if default/insecure keys (`SECRET_KEY`, `JWT_SECRET`, `MYSQL_PASSWORD`, `MOMO_WEBHOOK_SECRET`) or SQLite/synchronous Celery are detected.
* **Liveness Probe (`/healthz`)**: Ultra-lightweight endpoint returning HTTP 200 without database dependencies.
* **Readiness Probe (`/readyz`)**: Deep health probe evaluating physical database connectivity and Redis availability, with sensitive credential masking.

### 6. Containerization & Multi-Service Deployment (`Dockerfile`, `docker-compose.yml`)
* **Hardened Multi-Stage Build**: Python builder stage compiled into a slim runtime container executed under an unprivileged user (`campuslink`, `UID 10001`).
* **Isolated Docker Networks**: Frontend reverse proxy network (`frontend_net`) segregated from the backend database/cache network (`backend_net`).
* **Nginx Reverse Proxy**: Production Nginx container configured with gzip compression, security headers (`X-Frame-Options`, `X-Content-Type-Options`, `Content-Security-Policy`), and reverse proxy routing to Gunicorn.

---

## 15-Table Relational Schema Design

```
 ┌──────────────────────┐         ┌──────────────────────┐         ┌──────────────────────┐
 │        users         │◄────────┤       listings       │◄────────┤   rental_requests    │
 ├──────────────────────┤         ├──────────────────────┤         ├──────────────────────┤
 │ user_id (PK)         │         │ listing_id (PK)      │         │ request_id (PK)      │
 │ name, email, phone   │         │ owner_id (FK -> users│         │ listing_id (FK)      │
 │ password_hash        │         │ category_id (FK)     │         │ borrower_id (FK)     │
 │ verification_level   │         │ rental_rate_per_day  │         │ rent_start/end_date  │
 │ department, hostel   │         │ deposit_amount       │         │ status, purpose      │
 └──────────┬───────────┘         └──────────┬───────────┘         └──────────┬───────────┘
            │                                │                                │
            │                                └────────────────┐               │
            ▼                                                 ▼               ▼
 ┌──────────────────────┐                         ┌───────────────────────────────────────┐
 │     user_wallets     │                         │          rental_transactions          │
 ├──────────────────────┤                         ├───────────────────────────────────────┤
 │ wallet_id (PK)       │                         │ transaction_id (PK)                   │
 │ user_id (FK -> users)│                         │ request_id (FK -> rental_requests)    │
 │ available_balance    │                         │ listing_id (FK -> listings)           │
 │ pending_balance      │                         │ borrower_id (FK -> users)             │
 │ locked_escrow        │                         │ gross_amount, commission, earnings    │
 └──────────┬───────────┘                         │ rental_status, payment_status         │
            │                                     └───────────────────┬───────────────────┘
            ▼                                                         │
 ┌──────────────────────────────────────┐                             ▼
 │         wallet_transactions          │                 ┌───────────────────────┐
 ├──────────────────────────────────────┤                 │        reviews        │
 │ transaction_id (PK)                  │                 ├───────────────────────┤
 │ wallet_id (FK -> user_wallets)       │                 │ review_id (PK)        │
 │ user_id (FK -> users)                │                 │ transaction_id (FK)   │
 │ entry_type (DEBIT / CREDIT)          │                 │ reviewer_id (FK)      │
 │ tx_type, amount, idempotency_key     │                 │ reviewee_id (FK)      │
 │ reference_type, reference_id, status │                 │ reviewee_type, rating │
 └──────────────────────────────────────┘                 └───────────────────────┘
```

### Complete Schema Table Directory:
1. `users` — Student, faculty, and administrative accounts with PBKDF2 authentication.
2. `categories` — 13 UMaT academic & campus equipment categories.
3. `listings` — Student equipment listings with daily rental rates and security deposits.
4. `rental_requests` — Borrower rental requests with date ranges and approval lifecycle.
5. `rental_transactions` — Executed rentals with financial breakdown (Gross, Commission, Net).
6. `maintenance` — Equipment maintenance, damage inspection tickets, and repair logs.
7. `reviews` — Dual-sided peer reviews (Lender-to-Borrower and Borrower-to-Lender).
8. `wishlist` — Equipment wishlist tracking for students.
9. `saved_listings` — Bookmarked listings for quick access.
10. `services` — Student micro-services (CAD, tutoring, laptop repair, data analysis).
11. `service_orders` — Service booking orders with custodial escrow holds.
12. `service_reviews` — Student service delivery reviews and star ratings.
13. `user_wallets` — User wallet balances (Available, Pending, Locked Escrow, Earned, Withdrawn).
14. `wallet_transactions` — Authoritative double-entry financial ledger journal entries.
15. `notifications` — Real-time student notification records.

---

## Real-Time Analytical SQL Intelligence Reports

CampusLink provides 15 real-time SQL analytical business intelligence reports (available in `controllers.py` and rendered in the administrative intelligence dashboard):

1. **Transaction Overview**: Total transactions, gross marketplace volume, platform fees, and net owner disbursements.
2. **Revenue by Lender**: Top-earning equipment lenders categorized by academic department and campus hostel.
3. **Borrower Activity & Spend**: Student rental frequency and total capital expenditure.
4. **Category Performance**: Asset inventory density, rental frequency, and gross volume per equipment category.
5. **Top Rented Assets**: Most frequently rented tools (Total Stations, Rock Hammers, Lab Equipment).
6. **Unrented Inventory**: Idle assets available for promotional discovery.
7. **Current Overdue Rentals**: Live tracking of items overdue past their agreed return date.
8. **Maintenance & Repair Cost Audit**: Cumulative repair expenditure across departments.
9. **Rental Purpose Distribution**: Breakdown of rentals by academic purpose (Final Year Project, Field Work, Lab Practical).
10. **Category Duration Analysis**: Average and maximum rental duration per equipment category.
11. **Lender Trust Ratings**: Star ratings and peer reviews received by equipment owners.
12. **Borrower Trust Ratings**: Star ratings and peer reviews received by student borrowers.
13. **Hostel Inventory Distribution**: Asset density and most listed categories across campus hostels.
14. **Monthly Volume & Commission Growth**: Time-series analysis of gross volume and platform revenue.
15. **Late Return Incident Tracker**: Historical audit of late returns by department and hostel.

---

## Test Suite & Verification Results

```
========================================================================
  CampusLink 2.0 Verification Summary
========================================================================
  Full Unit & Integration Suite:      127 / 127 PASSED (100%)
  Authoritative Master E2E Suite:     106 / 106 PASSED (100%)
  Stage 5.5 Live MySQL 9.7 Suite:       6 /   6 PASSED (100%)
  Double-Entry Ledger Parity:         DEBIT == CREDIT (Delta = GHS 0.00)
  Zero-ID Prohibition (user/wallet 0):0 occurrences
  Dedicated Accounting Vaults:        6 (Commission), 7 (Escrow), 8 (Clearing)
========================================================================
```

---

## Getting Started

### 1. Prerequisites
* **Python 3.10+** (Python 3.13 recommended)
* Optional for Production: **MySQL 8.0+ / 9.7**, **Redis 7.0+**, **Docker & Docker Compose**

### 2. Installation
Clone the repository and install dependencies:
```bash
git clone https://github.com/ce-aavoryi8125-bot/CAMPUS_LINK.git
cd CAMPUS_LINK
pip install -r requirements.txt
```

### 3. Local Offline Development (SQLite 3)
Run the application locally with zero external dependencies:
```bash
# Seed local SQLite database with 61 listings, 6 services, and 8 users
python database/db_seeder.py

# Start the Flask web application
python app.py
```
Visit `http://127.0.0.1:5000` in your browser.

### 4. Running the Verification Test Suites
```bash
# Execute the full 127-test discovery suite
python -m unittest discover -s tests -p "test_*.py"

# Execute the 106-check master end-to-end suite
python tests/end_to_end_test.py

# Execute physical MySQL 9.7 verification (when MySQL is running)
python scripts/verify_mysql_live.py
```

### 5. Multi-Service Containerized Deployment (Production)
```bash
# 1. Copy the production environment template
cp .env.example .env

# 2. Populate strong production secrets in .env
# (CAMPUSLINK_SECRET_KEY, CAMPUSLINK_JWT_SECRET, MOMO_WEBHOOK_SECRET, MYSQL_PASSWORD, REDIS_PASSWORD)

# 3. Launch the complete 6-service stack
docker-compose up -d --build
```

---

## Security & Engineering Safeguards

* **PBKDF2 Password Hashing**: Passwords stored using PBKDF2-HMAC-SHA256 with 100,000 iterations and cryptographically unique per-user salts.
* **Strict SQL Dialect Normalization**: Centralized parameterization in `db_engine.py` preventing SQL injection across both SQLite and MySQL.
* **Secret Protection**: Default passwords and development secrets are rejected at startup when in production mode (`ConfigurationError`).
* **Non-Root Execution**: Containerized applications run exclusively under unprivileged user `campuslink` (`UID 10001`).

---

## License & Attribution

Developed by **Albert Avoryi** (`ce-aavoryi8125@st.umat.edu.gh`)  
**University of Mines and Technology (UMaT)**, Tarkwa, Ghana.  
All Rights Reserved.
