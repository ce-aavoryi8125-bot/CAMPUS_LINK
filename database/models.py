"""
database/models.py
------------------
SQLAlchemy 2.0 Typed Declarative Models for CampusLink 2.0.
Maps the 10 existing core tables plus the 5 new tables for Services, Orders, and Wallets.
Preserves exact column naming, constraints, monetary decimal precision, and relationships.
Includes Stage 1.3.1 Financial & Schema Integrity enhancements (CREDIT/DEBIT direction,
idempotency keys for duplicate prevention, and immutable historical provider snapshots).
"""
from typing import Optional, List
from datetime import datetime, timezone
from decimal import Decimal
import os

from sqlalchemy import (
    create_engine, Integer, String, Text, Numeric, DateTime, ForeignKey,
    UniqueConstraint, CheckConstraint, Index, func, event
)
from sqlalchemy.orm import (
    DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker, Session
)

def utcnow_naive():
    """Returns current UTC timestamp as a naive datetime object for cross-DB compatibility."""
    return datetime.now(timezone.utc).replace(tzinfo=None)

# Base Declarative Class
class Base(DeclarativeBase):
    pass

# ==============================================================================
# 1. CORE IDENTITY & AUTHENTICATION MODELS
# ==============================================================================

class User(Base):
    __tablename__ = "users"

    user_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    student_id: Mapped[Optional[str]] = mapped_column(String(100), unique=True, nullable=True)
    phone: Mapped[str] = mapped_column(String(50), nullable=False)
    verification_level: Mapped[str] = mapped_column(String(50), nullable=False, default="Unverified")
    account_status: Mapped[str] = mapped_column(String(50), nullable=False, default="Active")
    department: Mapped[str] = mapped_column(String(150), nullable=False)
    hostel: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    last_login: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime, default=utcnow_naive, server_default=func.current_timestamp())

    # Relationships to existing marketplace & rental entities
    listings: Mapped[List["Listing"]] = relationship("Listing", back_populates="owner", foreign_keys="Listing.owner_id")
    rental_requests: Mapped[List["RentalRequest"]] = relationship("RentalRequest", back_populates="borrower", foreign_keys="RentalRequest.borrower_id")
    rental_transactions: Mapped[List["RentalTransaction"]] = relationship("RentalTransaction", back_populates="borrower", foreign_keys="RentalTransaction.borrower_id")
    maintenance_reports: Mapped[List["Maintenance"]] = relationship("Maintenance", back_populates="reporter", foreign_keys="Maintenance.reported_by")
    reviews_written: Mapped[List["Review"]] = relationship("Review", back_populates="reviewer", foreign_keys="Review.reviewer_id")
    reviews_received: Mapped[List["Review"]] = relationship("Review", back_populates="reviewee", foreign_keys="Review.reviewee_id")
    wishlist_items: Mapped[List["Wishlist"]] = relationship("Wishlist", back_populates="user", cascade="all, delete-orphan")
    saved_listings: Mapped[List["SavedListing"]] = relationship("SavedListing", back_populates="user", cascade="all, delete-orphan")
    notifications: Mapped[List["Notification"]] = relationship("Notification", back_populates="user", cascade="all, delete-orphan")

    # Relationships to new services and wallet entities
    services: Mapped[List["Service"]] = relationship("Service", back_populates="provider", foreign_keys="Service.provider_id")
    service_orders_bought: Mapped[List["ServiceOrder"]] = relationship("ServiceOrder", back_populates="client", foreign_keys="ServiceOrder.client_id")
    service_orders_provided: Mapped[List["ServiceOrder"]] = relationship("ServiceOrder", back_populates="provider", foreign_keys="ServiceOrder.provider_id")
    wallet: Mapped[Optional["UserWallet"]] = relationship("UserWallet", back_populates="user", uselist=False)

    __table_args__ = (
        CheckConstraint(
            "email LIKE '%@umat.edu.gh' OR email LIKE '%@student.umat.edu.gh' OR email LIKE '%@st.umat.edu.gh' OR email LIKE '%@%'",
            name="chk_email_domain"
        ),
        CheckConstraint("verification_level IN ('Unverified', 'Verified Student', 'Verified Staff', 'Admin')", name="chk_user_verification"),
        CheckConstraint("account_status IN ('Active', 'Suspended', 'Pending Verification')", name="chk_user_status"),
    )


class Category(Base):
    __tablename__ = "categories"

    category_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(150), unique=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    listings: Mapped[List["Listing"]] = relationship("Listing", back_populates="category")
    services: Mapped[List["Service"]] = relationship("Service", back_populates="category")
    wishlist_items: Mapped[List["Wishlist"]] = relationship("Wishlist", back_populates="category")

# ==============================================================================
# 2. EQUIPMENT MARKETPLACE & RENTAL LIFECYCLE MODELS
# ==============================================================================

class Listing(Base):
    __tablename__ = "listings"

    listing_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    owner_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.user_id"), nullable=False)
    category_id: Mapped[int] = mapped_column(Integer, ForeignKey("categories.category_id"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    subcategory: Mapped[str] = mapped_column(String(150), nullable=False)
    brand: Mapped[str] = mapped_column(String(100), nullable=False)
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    purchase_year: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    rental_rate_per_day: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    deposit_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    condition: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="Available")
    pickup_location: Mapped[str] = mapped_column(String(255), nullable=False)
    thumbnail_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    available_from: Mapped[str] = mapped_column(String(50), nullable=False)
    available_until: Mapped[str] = mapped_column(String(50), nullable=False)
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime, default=utcnow_naive, server_default=func.current_timestamp())

    owner: Mapped["User"] = relationship("User", back_populates="listings")
    category: Mapped["Category"] = relationship("Category", back_populates="listings")
    rental_requests: Mapped[List["RentalRequest"]] = relationship("RentalRequest", back_populates="listing")
    rental_transactions: Mapped[List["RentalTransaction"]] = relationship("RentalTransaction", back_populates="listing")
    maintenance_records: Mapped[List["Maintenance"]] = relationship("Maintenance", back_populates="listing")
    saved_by_users: Mapped[List["SavedListing"]] = relationship("SavedListing", back_populates="listing")

    __table_args__ = (
        CheckConstraint("rental_rate_per_day >= 0", name="chk_rate_positive"),
        CheckConstraint("deposit_amount >= 0", name="chk_deposit_positive"),
        CheckConstraint("condition IN ('New', 'Good', 'Fair', 'Poor')", name="chk_listing_condition"),
        CheckConstraint("status IN ('Available', 'Reserved', 'Rented', 'Maintenance', 'Delisted')", name="chk_listing_status"),
        CheckConstraint("available_until >= available_from", name="chk_dates_valid"),
        Index("idx_listings_owner", "owner_id"),
        Index("idx_listings_category", "category_id"),
    )


class RentalRequest(Base):
    __tablename__ = "rental_requests"

    request_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    listing_id: Mapped[int] = mapped_column(Integer, ForeignKey("listings.listing_id"), nullable=False)
    borrower_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.user_id"), nullable=False)
    rent_start_date: Mapped[str] = mapped_column(String(50), nullable=False)
    rent_end_date: Mapped[str] = mapped_column(String(50), nullable=False)
    rental_purpose: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="Pending")
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime, default=utcnow_naive, server_default=func.current_timestamp())

    listing: Mapped["Listing"] = relationship("Listing", back_populates="rental_requests")
    borrower: Mapped["User"] = relationship("User", back_populates="rental_requests")
    transaction: Mapped[Optional["RentalTransaction"]] = relationship("RentalTransaction", back_populates="request", uselist=False)

    __table_args__ = (
        CheckConstraint("rental_purpose IN ('Field Trip', 'Final Year Project', 'Laboratory Session', 'Research', 'Presentation', 'Personal Use')", name="chk_rental_purpose"),
        CheckConstraint("status IN ('Pending', 'Approved', 'Rejected', 'Cancelled')", name="chk_request_status"),
        CheckConstraint("rent_end_date >= rent_start_date", name="chk_rent_dates"),
        Index("idx_requests_listing", "listing_id"),
        Index("idx_requests_borrower", "borrower_id"),
    )


class RentalTransaction(Base):
    __tablename__ = "rental_transactions"

    transaction_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    request_id: Mapped[int] = mapped_column(Integer, ForeignKey("rental_requests.request_id"), unique=True, nullable=False)
    listing_id: Mapped[int] = mapped_column(Integer, ForeignKey("listings.listing_id"), nullable=False)
    borrower_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.user_id"), nullable=False)
    rent_start_date: Mapped[str] = mapped_column(String(50), nullable=False)
    rent_end_date: Mapped[str] = mapped_column(String(50), nullable=False)
    actual_return_date: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    total_days: Mapped[int] = mapped_column(Integer, nullable=False)
    gross_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    commission_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    owner_earnings: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    deposit_held: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    payment_status: Mapped[str] = mapped_column(String(50), nullable=False, default="Pending")
    rental_status: Mapped[str] = mapped_column(String(50), nullable=False, default="Active")
    return_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime, default=utcnow_naive, server_default=func.current_timestamp())

    request: Mapped["RentalRequest"] = relationship("RentalRequest", back_populates="transaction")
    listing: Mapped["Listing"] = relationship("Listing", back_populates="rental_transactions")
    borrower: Mapped["User"] = relationship("User", back_populates="rental_transactions")
    reviews: Mapped[List["Review"]] = relationship("Review", back_populates="transaction")

    __table_args__ = (
        CheckConstraint("total_days > 0", name="chk_total_days"),
        CheckConstraint("gross_amount >= 0", name="chk_gross_positive"),
        CheckConstraint("commission_amount >= 0", name="chk_commission_positive"),
        CheckConstraint("owner_earnings >= 0", name="chk_earnings_positive"),
        CheckConstraint("deposit_held >= 0", name="chk_deposit_held_positive"),
        CheckConstraint("payment_status IN ('Pending', 'Paid', 'Refunded')", name="chk_payment_status"),
        CheckConstraint("rental_status IN ('Active', 'Returned', 'Overdue', 'Cancelled')", name="chk_rental_status"),
        Index("idx_transactions_request", "request_id"),
    )


class Maintenance(Base):
    __tablename__ = "maintenance"

    maintenance_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    listing_id: Mapped[int] = mapped_column(Integer, ForeignKey("listings.listing_id"), nullable=False)
    reported_by: Mapped[int] = mapped_column(Integer, ForeignKey("users.user_id"), nullable=False)
    issue_description: Mapped[str] = mapped_column(Text, nullable=False)
    cost: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=Decimal("0.00"))
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="Pending")
    start_date: Mapped[str] = mapped_column(String(50), nullable=False)
    end_date: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    listing: Mapped["Listing"] = relationship("Listing", back_populates="maintenance_records")
    reporter: Mapped["User"] = relationship("User", back_populates="maintenance_reports")

    __table_args__ = (
        CheckConstraint("cost >= 0", name="chk_cost_positive"),
        CheckConstraint("status IN ('Pending', 'In Progress', 'Completed')", name="chk_maint_status"),
    )


class Review(Base):
    __tablename__ = "reviews"

    review_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    transaction_id: Mapped[int] = mapped_column(Integer, ForeignKey("rental_transactions.transaction_id"), nullable=False)
    reviewer_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.user_id"), nullable=False)
    reviewee_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.user_id"), nullable=False)
    reviewee_type: Mapped[str] = mapped_column(String(50), nullable=False)
    rating: Mapped[int] = mapped_column(Integer, nullable=False)
    comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime, default=utcnow_naive, server_default=func.current_timestamp())

    transaction: Mapped["RentalTransaction"] = relationship("RentalTransaction", back_populates="reviews")
    reviewer: Mapped["User"] = relationship("User", back_populates="reviews_written", foreign_keys=[reviewer_id])
    reviewee: Mapped["User"] = relationship("User", back_populates="reviews_received", foreign_keys=[reviewee_id])

    __table_args__ = (
        CheckConstraint("reviewee_type IN ('Lender', 'Borrower')", name="chk_reviewee_type"),
        CheckConstraint("rating >= 1 AND rating <= 5", name="chk_rating_range"),
        Index("idx_reviews_transaction", "transaction_id"),
    )


class Wishlist(Base):
    __tablename__ = "wishlist"

    wishlist_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.user_id"), nullable=False)
    category_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("categories.category_id"), nullable=True)
    keyword: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime, default=utcnow_naive, server_default=func.current_timestamp())

    user: Mapped["User"] = relationship("User", back_populates="wishlist_items")
    category: Mapped[Optional["Category"]] = relationship("Category", back_populates="wishlist_items")

    __table_args__ = (
        UniqueConstraint("user_id", "category_id", "keyword", name="uq_wishlist"),
    )


class SavedListing(Base):
    __tablename__ = "saved_listings"

    saved_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.user_id"), nullable=False)
    listing_id: Mapped[int] = mapped_column(Integer, ForeignKey("listings.listing_id"), nullable=False)
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime, default=utcnow_naive, server_default=func.current_timestamp())

    user: Mapped["User"] = relationship("User", back_populates="saved_listings")
    listing: Mapped["Listing"] = relationship("Listing", back_populates="saved_by_users")

    __table_args__ = (
        UniqueConstraint("user_id", "listing_id", name="uq_saved"),
    )


class Notification(Base):
    __tablename__ = "notifications"

    notification_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.user_id"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    type: Mapped[str] = mapped_column(String(50), nullable=False, default="info")
    is_read: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime, default=utcnow_naive, server_default=func.current_timestamp())

    user: Mapped["User"] = relationship("User", back_populates="notifications")

    __table_args__ = (
        CheckConstraint("type IN ('info', 'success', 'warning', 'danger')", name="chk_notif_type"),
        Index("idx_notifications_user", "user_id"),
    )

# ==============================================================================
# 3. SERVICES & SKILLS MARKETPLACE MODELS (PHASE 1 EXPANSION)
# ==============================================================================

class Service(Base):
    __tablename__ = "services"

    service_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    provider_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.user_id"), nullable=False)
    category_id: Mapped[int] = mapped_column(Integer, ForeignKey("categories.category_id"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    subcategory: Mapped[str] = mapped_column(String(150), nullable=False)
    pricing_model: Mapped[str] = mapped_column(String(50), nullable=False, default="Fixed")
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    delivery_time_days: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    portfolio_urls: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="Active")
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime, default=utcnow_naive, server_default=func.current_timestamp())
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, default=utcnow_naive, onupdate=utcnow_naive)

    provider: Mapped["User"] = relationship("User", back_populates="services")
    category: Mapped["Category"] = relationship("Category", back_populates="services")
    orders: Mapped[List["ServiceOrder"]] = relationship("ServiceOrder", back_populates="service")

    __table_args__ = (
        CheckConstraint("price >= 0", name="chk_service_price_positive"),
        CheckConstraint("delivery_time_days >= 1", name="chk_delivery_days"),
        CheckConstraint("pricing_model IN ('Fixed', 'Hourly', 'StartingAt')", name="chk_pricing_model"),
        CheckConstraint("status IN ('Active', 'Paused', 'Delisted')", name="chk_service_status"),
        Index("idx_services_provider", "provider_id"),
        Index("idx_services_category", "category_id"),
    )


class ServiceOrder(Base):
    """
    Client Service Order.
    NOTE: provider_id is explicitly stored on the order as an immutable financial snapshot.
    This guarantees that the exact provider entitled to earnings at order placement remains
    preserved even if the parent Service listing is later edited, transferred, or delisted.
    """
    __tablename__ = "service_orders"

    order_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    service_id: Mapped[int] = mapped_column(Integer, ForeignKey("services.service_id"), nullable=False)
    client_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.user_id"), nullable=False)
    provider_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.user_id"), nullable=False) # Historical snapshot
    requirements: Mapped[str] = mapped_column(Text, nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    platform_fee: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    provider_earnings: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="Pending")
    escrow_status: Mapped[str] = mapped_column(String(50), nullable=False, default="Held")
    due_date: Mapped[str] = mapped_column(String(50), nullable=False)
    delivered_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime, default=utcnow_naive, server_default=func.current_timestamp())

    service: Mapped["Service"] = relationship("Service", back_populates="orders")
    client: Mapped["User"] = relationship("User", back_populates="service_orders_bought", foreign_keys=[client_id])
    provider: Mapped["User"] = relationship("User", back_populates="service_orders_provided", foreign_keys=[provider_id])
    review: Mapped[Optional["ServiceReview"]] = relationship("ServiceReview", back_populates="order", uselist=False)

    __table_args__ = (
        CheckConstraint("amount >= 0", name="chk_order_amount_positive"),
        CheckConstraint("platform_fee >= 0", name="chk_order_fee_positive"),
        CheckConstraint("provider_earnings >= 0", name="chk_order_earnings_positive"),
        CheckConstraint("status IN ('Pending', 'Accepted', 'InProgress', 'Delivered', 'Completed', 'Cancelled', 'Disputed')", name="chk_order_status"),
        CheckConstraint("escrow_status IN ('Held', 'Released', 'Refunded', 'Deducted')", name="chk_escrow_status"),
        Index("idx_orders_service", "service_id"),
        Index("idx_orders_client", "client_id"),
        Index("idx_orders_provider", "provider_id"),
    )


class ServiceReview(Base):
    __tablename__ = "service_reviews"

    review_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(Integer, ForeignKey("service_orders.order_id"), unique=True, nullable=False)
    client_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.user_id"), nullable=False)
    provider_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.user_id"), nullable=False)
    rating: Mapped[int] = mapped_column(Integer, nullable=False)
    comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime, default=utcnow_naive, server_default=func.current_timestamp())

    order: Mapped["ServiceOrder"] = relationship("ServiceOrder", back_populates="review")

    __table_args__ = (
        CheckConstraint("rating >= 1 AND rating <= 5", name="chk_service_rating_range"),
    )

# ==============================================================================
# 4. WALLET, ESCROW & FINANCIAL LEDGER MODELS (AUTHORITATIVE LEDGER)
# ==============================================================================

class UserWallet(Base):
    """
    Cached balance representation for high-frequency dashboard queries.
    NOTE: wallet_transactions is the authoritative financial ledger.
    """
    __tablename__ = "user_wallets"

    wallet_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.user_id"), unique=True, nullable=False)
    available_balance: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=Decimal("0.00"))
    pending_balance: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=Decimal("0.00"))
    locked_escrow: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=Decimal("0.00"))
    total_earned: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=Decimal("0.00"))
    total_withdrawn: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False, default=Decimal("0.00"))
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, default=utcnow_naive, onupdate=utcnow_naive)

    user: Mapped["User"] = relationship("User", back_populates="wallet")
    transactions: Mapped[List["WalletTransaction"]] = relationship("WalletTransaction", back_populates="wallet")

    __table_args__ = (
        CheckConstraint("available_balance >= 0", name="chk_wallet_avail_positive"),
        CheckConstraint("pending_balance >= 0", name="chk_wallet_pending_positive"),
        CheckConstraint("locked_escrow >= 0", name="chk_wallet_escrow_positive"),
        CheckConstraint("total_earned >= 0", name="chk_wallet_earned_positive"),
        CheckConstraint("total_withdrawn >= 0", name="chk_wallet_withdrawn_positive"),
        Index("idx_wallets_user", "user_id"),
    )


class WalletTransaction(Base):
    """
    Authoritative Financial Ledger. Every balance-changing operation MUST have an immutable row here.
    - entry_type ('CREDIT' vs 'DEBIT') unambiguously establishes money entering vs leaving the wallet.
    - idempotency_key prevents duplicate execution of earnings, payouts, escrow releases, or refunds.
    Supports HOLD, RELEASE, DEDUCTION, REFUND, PAYOUT, RENTAL_EARNING, and SERVICE_EARNING.
    """
    __tablename__ = "wallet_transactions"

    wallet_tx_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    wallet_id: Mapped[int] = mapped_column(Integer, ForeignKey("user_wallets.wallet_id"), nullable=False)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.user_id"), nullable=False)
    entry_type: Mapped[str] = mapped_column(String(10), nullable=False) # 'CREDIT' or 'DEBIT'
    tx_type: Mapped[str] = mapped_column(String(50), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    reference_type: Mapped[str] = mapped_column(String(50), nullable=False) # 'rental_transaction', 'service_order', 'payout', 'escrow_hold', 'escrow_release', 'escrow_refund'
    reference_id: Mapped[int] = mapped_column(Integer, nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(120), unique=True, nullable=False) # e.g. "RENTAL_EARNING_TX_42_CREDIT"
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="Completed")
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime, default=utcnow_naive, server_default=func.current_timestamp())

    wallet: Mapped["UserWallet"] = relationship("UserWallet", back_populates="transactions")

    __table_args__ = (
        CheckConstraint("entry_type IN ('CREDIT', 'DEBIT')", name="chk_ledger_entry_type"),
        CheckConstraint("amount >= 0", name="chk_ledger_amount_positive"),
        CheckConstraint(
            "tx_type IN ('RentalIncome', 'ServiceIncome', 'DepositEscrowHold', 'DepositRefund', 'DamageDeduction', 'PlatformCommission', 'PayoutWithdrawal')",
            name="chk_ledger_tx_type"
        ),
        CheckConstraint("status IN ('Pending', 'Completed', 'Failed')", name="chk_ledger_status"),
        Index("idx_wallet_tx_wallet", "wallet_id"),
        Index("idx_wallet_tx_user", "user_id"),
        Index("idx_wallet_tx_idempotency", "idempotency_key"),
    )

# ==============================================================================
# 5. ENGINE & SESSION FACTORY INFRASTRUCTURE
# ==============================================================================

def get_db_url():
    """
    Returns the appropriate SQLAlchemy database URL based on active configuration.
    """
    use_mysql = os.environ.get("USE_MYSQL", "true").lower() in ("true", "1", "yes")
    mysql_host = os.environ.get("MYSQL_HOST", "localhost")
    mysql_port = os.environ.get("MYSQL_PORT", "3306")
    mysql_user = os.environ.get("MYSQL_USER", "root")
    mysql_password = os.environ.get("MYSQL_PASSWORD", "")
    mysql_db = os.environ.get("MYSQL_DB", "campuslink_umat")
    
    sqlite_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "campuslink_umat.db")

    if use_mysql:
        try:
            import pymysql
            conn = pymysql.connect(
                host=mysql_host,
                port=int(mysql_port),
                user=mysql_user,
                password=mysql_password,
                database=mysql_db,
                connect_timeout=2
            )
            conn.close()
            return f"mysql+pymysql://{mysql_user}:{mysql_password}@{mysql_host}:{mysql_port}/{mysql_db}?charset=utf8mb4"
        except Exception:
            pass

    return f"sqlite:///{sqlite_path}"

_engine = None
_SessionLocal = None

def get_sqlalchemy_engine():
    global _engine
    if _engine is None:
        db_url = get_db_url()
        if db_url.startswith("sqlite"):
            _engine = create_engine(
                db_url,
                connect_args={"check_same_thread": False},
                echo=False
            )
            @event.listens_for(_engine, "connect")
            def set_sqlite_pragma(dbapi_connection, connection_record):
                cursor = dbapi_connection.cursor()
                cursor.execute("PRAGMA foreign_keys=ON")
                cursor.close()
        else:
            _engine = create_engine(
                db_url,
                pool_pre_ping=True,
                pool_recycle=3600,
                echo=False
            )
    return _engine

def get_db_session() -> Session:
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=get_sqlalchemy_engine())
    return _SessionLocal()
