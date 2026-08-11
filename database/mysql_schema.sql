-- CampusLink MySQL Database Schema DDL
-- Target: MySQL 5.7+ / MySQL 8.0+ / MariaDB
-- Platform: Peer-to-Peer Student Resource Marketplace (UMaT, Ghana)

CREATE DATABASE IF NOT EXISTS campuslink_umat
  DEFAULT CHARACTER SET utf8mb4
  DEFAULT COLLATE utf8mb4_unicode_ci;

USE campuslink_umat;

-- 1. USERS Table
CREATE TABLE IF NOT EXISTS users (
    user_id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    student_id VARCHAR(100) UNIQUE NULL,
    phone VARCHAR(50) NOT NULL,
    verification_level ENUM('Unverified', 'Verified Student', 'Verified Staff', 'Admin') NOT NULL DEFAULT 'Unverified',
    account_status ENUM('Active', 'Suspended', 'Pending Verification') NOT NULL DEFAULT 'Active',
    department VARCHAR(150) NOT NULL,
    hostel VARCHAR(150) NULL,
    last_login DATETIME NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_email_umat CHECK (email LIKE '%@%')
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 2. CATEGORIES Table
CREATE TABLE IF NOT EXISTS categories (
    category_id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(150) UNIQUE NOT NULL,
    description TEXT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 3. LISTINGS Table
CREATE TABLE IF NOT EXISTS listings (
    listing_id INT AUTO_INCREMENT PRIMARY KEY,
    owner_id INT NOT NULL,
    category_id INT NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT NULL,
    subcategory VARCHAR(150) NOT NULL,
    brand VARCHAR(100) NOT NULL,
    model VARCHAR(100) NOT NULL,
    purchase_year INT NULL,
    rental_rate_per_day DECIMAL(10,2) NOT NULL,
    deposit_amount DECIMAL(10,2) NOT NULL,
    `condition` ENUM('New', 'Good', 'Fair', 'Poor') NOT NULL,
    status ENUM('Available', 'Reserved', 'Rented', 'Maintenance', 'Delisted') NOT NULL DEFAULT 'Available',
    pickup_location VARCHAR(255) NOT NULL,
    thumbnail_path VARCHAR(500) NULL,
    available_from DATE NOT NULL,
    available_until DATE NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (owner_id) REFERENCES users (user_id) ON DELETE CASCADE,
    FOREIGN KEY (category_id) REFERENCES categories (category_id) ON DELETE CASCADE,
    CONSTRAINT chk_rate_positive CHECK (rental_rate_per_day >= 0),
    CONSTRAINT chk_deposit_positive CHECK (deposit_amount >= 0),
    CONSTRAINT chk_dates_valid CHECK (available_until >= available_from)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 4. RENTAL REQUESTS Table
CREATE TABLE IF NOT EXISTS rental_requests (
    request_id INT AUTO_INCREMENT PRIMARY KEY,
    listing_id INT NOT NULL,
    borrower_id INT NOT NULL,
    rent_start_date DATE NOT NULL,
    rent_end_date DATE NOT NULL,
    rental_purpose ENUM('Field Trip', 'Final Year Project', 'Laboratory Session', 'Research', 'Presentation', 'Personal Use') NOT NULL,
    status ENUM('Pending', 'Approved', 'Rejected', 'Cancelled') NOT NULL DEFAULT 'Pending',
    notes TEXT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (listing_id) REFERENCES listings (listing_id) ON DELETE CASCADE,
    FOREIGN KEY (borrower_id) REFERENCES users (user_id) ON DELETE CASCADE,
    CONSTRAINT chk_rent_dates CHECK (rent_end_date >= rent_start_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 5. RENTAL TRANSACTIONS Table
CREATE TABLE IF NOT EXISTS rental_transactions (
    transaction_id INT AUTO_INCREMENT PRIMARY KEY,
    request_id INT UNIQUE NOT NULL,
    listing_id INT NOT NULL,
    borrower_id INT NOT NULL,
    rent_start_date DATE NOT NULL,
    rent_end_date DATE NOT NULL,
    actual_return_date DATE NULL,
    total_days INT NOT NULL,
    gross_amount DECIMAL(10,2) NOT NULL,
    commission_amount DECIMAL(10,2) NOT NULL,
    owner_earnings DECIMAL(10,2) NOT NULL,
    deposit_held DECIMAL(10,2) NOT NULL,
    payment_status ENUM('Pending', 'Paid', 'Refunded') NOT NULL DEFAULT 'Pending',
    rental_status ENUM('Active', 'Returned', 'Overdue', 'Cancelled') NOT NULL DEFAULT 'Active',
    return_notes TEXT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (request_id) REFERENCES rental_requests (request_id) ON DELETE CASCADE,
    FOREIGN KEY (listing_id) REFERENCES listings (listing_id) ON DELETE CASCADE,
    FOREIGN KEY (borrower_id) REFERENCES users (user_id) ON DELETE CASCADE,
    CONSTRAINT chk_total_days CHECK (total_days > 0),
    CONSTRAINT chk_gross_positive CHECK (gross_amount >= 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 6. MAINTENANCE Table
CREATE TABLE IF NOT EXISTS maintenance (
    maintenance_id INT AUTO_INCREMENT PRIMARY KEY,
    listing_id INT NOT NULL,
    reported_by INT NOT NULL,
    issue_description TEXT NOT NULL,
    cost DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    status ENUM('Pending', 'In Progress', 'Completed') NOT NULL DEFAULT 'Pending',
    start_date DATE NOT NULL,
    end_date DATE NULL,
    FOREIGN KEY (listing_id) REFERENCES listings (listing_id) ON DELETE CASCADE,
    FOREIGN KEY (reported_by) REFERENCES users (user_id) ON DELETE CASCADE,
    CONSTRAINT chk_cost_positive CHECK (cost >= 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 7. REVIEWS Table
CREATE TABLE IF NOT EXISTS reviews (
    review_id INT AUTO_INCREMENT PRIMARY KEY,
    transaction_id INT NOT NULL,
    reviewer_id INT NOT NULL,
    reviewee_id INT NOT NULL,
    reviewee_type ENUM('Lender', 'Borrower') NOT NULL,
    rating INT NOT NULL,
    comment TEXT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (transaction_id) REFERENCES rental_transactions (transaction_id) ON DELETE CASCADE,
    FOREIGN KEY (reviewer_id) REFERENCES users (user_id) ON DELETE CASCADE,
    FOREIGN KEY (reviewee_id) REFERENCES users (user_id) ON DELETE CASCADE,
    CONSTRAINT chk_rating_range CHECK (rating >= 1 AND rating <= 5)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 8. WISHLIST Table
CREATE TABLE IF NOT EXISTS wishlist (
    wishlist_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    category_id INT NULL,
    keyword VARCHAR(150) NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE,
    FOREIGN KEY (category_id) REFERENCES categories (category_id) ON DELETE SET NULL,
    UNIQUE KEY uq_wishlist (user_id, category_id, keyword)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 9. SAVED LISTINGS Table
CREATE TABLE IF NOT EXISTS saved_listings (
    saved_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    listing_id INT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE,
    FOREIGN KEY (listing_id) REFERENCES listings (listing_id) ON DELETE CASCADE,
    UNIQUE KEY uq_saved (user_id, listing_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Performance & Query Optimization Indexes
CREATE INDEX idx_listings_owner ON listings(owner_id);
CREATE INDEX idx_listings_category ON listings(category_id);
CREATE INDEX idx_requests_listing ON rental_requests(listing_id);
CREATE INDEX idx_requests_borrower ON rental_requests(borrower_id);
CREATE INDEX idx_transactions_request ON rental_transactions(request_id);
CREATE INDEX idx_reviews_transaction ON reviews(transaction_id);
