"""
test_stage1_3_models.py
-----------------------
Targeted unit and integration tests for Stage 1.3 SQLAlchemy 2.0 Declarative Models.
Verifies all 15 model definitions, columns, relationships, monetary precision,
session lifecycle, and compatibility with the existing active database.
"""
import unittest
import sys
import os
from decimal import Decimal

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from database.models import (
    Base, User, Category, Listing, RentalRequest, RentalTransaction,
    Maintenance, Review, Wishlist, SavedListing, Notification,
    Service, ServiceOrder, ServiceReview, UserWallet, WalletTransaction,
    get_sqlalchemy_engine, get_db_session
)

class TestSQLAlchemyModelsStage1_3(unittest.TestCase):

    def test_01_all_15_models_registered(self):
        tables = Base.metadata.tables.keys()
        expected = [
            "users", "categories", "listings", "rental_requests", "rental_transactions",
            "maintenance", "reviews", "wishlist", "saved_listings", "notifications",
            "services", "service_orders", "service_reviews", "user_wallets", "wallet_transactions"
        ]
        for tbl in expected:
            self.assertIn(tbl, tables, f"Table '{tbl}' must be registered in Base.metadata")
        print(f"  [OK] PASS  |  All 15 SQLAlchemy 2.0 models verified in Base.metadata ({len(tables)} tables)")

    def test_02_monetary_precision_numeric_type(self):
        # Verify monetary columns use Numeric(10, 2)
        listing_rate_col = Listing.__table__.columns["rental_rate_per_day"]
        self.assertEqual(listing_rate_col.type.precision, 10)
        self.assertEqual(listing_rate_col.type.scale, 2)

        tx_gross_col = RentalTransaction.__table__.columns["gross_amount"]
        self.assertEqual(tx_gross_col.type.precision, 10)
        self.assertEqual(tx_gross_col.type.scale, 2)

        wallet_bal_col = UserWallet.__table__.columns["available_balance"]
        self.assertEqual(wallet_bal_col.type.precision, 10)
        self.assertEqual(wallet_bal_col.type.scale, 2)
        print("  [OK] PASS  |  Monetary fields use precise Numeric(10, 2) across listings, transactions, and wallets")

    def test_03_query_existing_database_via_orm(self):
        # Query existing users from the live database using SQLAlchemy ORM
        session = get_db_session()
        try:
            user = session.execute(select(User).where(User.user_id == 1)).scalar_one_or_none()
            self.assertIsNotNone(user)
            self.assertEqual(user.name, "Albert Boateng")
            self.assertTrue(user.email.endswith("umat.edu.gh") or "@st.umat.edu.gh" in user.email)
            print(f"  [OK] PASS  |  SQLAlchemy ORM session successfully retrieved User #{user.user_id} ({user.name})")

            # Verify relationship loading (User -> Listings)
            listings = user.listings
            self.assertIsInstance(listings, list)
            self.assertGreater(len(listings), 0)
            print(f"  [OK] PASS  |  Relationship User -> Listings verified ({len(listings)} listings for Albert)")

            # Verify relationship loading (Listing -> Category & Owner)
            first_listing = listings[0]
            self.assertIsNotNone(first_listing.category)
            self.assertEqual(first_listing.owner.name, "Albert Boateng")
            print(f"  [OK] PASS  |  Relationship Listing -> Category & Owner verified ('{first_listing.title}')")
        finally:
            session.close()

    def test_04_query_rental_transactions_and_requests_orm(self):
        session = get_db_session()
        try:
            tx = session.execute(select(RentalTransaction).limit(1)).scalar_one_or_none()
            if tx:
                self.assertIsNotNone(tx.request)
                self.assertIsNotNone(tx.listing)
                self.assertIsNotNone(tx.borrower)
                self.assertIsInstance(tx.gross_amount, (Decimal, float))
                print(f"  [OK] PASS  |  ORM RentalTransaction #{tx.transaction_id} relationships verified (Borrower: {tx.borrower.name})")
        finally:
            session.close()

    def test_05_in_memory_metadata_creation_and_new_models(self):
        # Create an isolated in-memory SQLite database to test all 15 models including new Services & Wallet tables
        mem_engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(mem_engine)

        MemSession = sessionmaker(bind=mem_engine)
        session = MemSession()

        try:
            # 1. Create User & Category
            u = User(name="Test Provider", email="provider@st.umat.edu.gh", password_hash="hash", phone="+233240001122", department="Computer Science")
            c = Category(name="Academic Tutoring", description="Peer tutoring services")
            session.add_all([u, c])
            session.commit()

            # 2. Create Service
            svc = Service(
                provider_id=u.user_id,
                category_id=c.category_id,
                title="Python Programming Tutoring",
                description="One-on-one Python programming lessons",
                subcategory="Software Tutoring",
                pricing_model="Hourly",
                price=Decimal("40.00"),
                delivery_time_days=2
            )
            session.add(svc)
            session.commit()
            self.assertGreater(svc.service_id, 0)

            # 3. Create ServiceOrder
            order = ServiceOrder(
                service_id=svc.service_id,
                client_id=u.user_id,
                provider_id=u.user_id,
                requirements="Need help with Python OOP",
                amount=Decimal("80.00"),
                platform_fee=Decimal("8.00"),
                provider_earnings=Decimal("72.00"),
                status="Pending",
                escrow_status="Held",
                due_date="2026-09-10"
            )
            session.add(order)
            session.commit()
            self.assertGreater(order.order_id, 0)

            # 4. Create UserWallet and WalletTransaction
            wallet = UserWallet(
                user_id=u.user_id,
                available_balance=Decimal("150.00"),
                pending_balance=Decimal("72.00"),
                locked_escrow=Decimal("0.00"),
                total_earned=Decimal("250.00"),
                total_withdrawn=Decimal("100.00")
            )
            session.add(wallet)
            session.commit()
            self.assertGreater(wallet.wallet_id, 0)

            wallet_tx = WalletTransaction(
                wallet_id=wallet.wallet_id,
                user_id=u.user_id,
                entry_type="CREDIT",
                tx_type="ServiceIncome",
                amount=Decimal("72.00"),
                reference_type="service_order",
                reference_id=order.order_id,
                idempotency_key="TEST_STAGE1_3_WALLET_TX_1",
                status="Completed",
                notes="Tutoring session completed"
            )
            session.add(wallet_tx)
            session.commit()
            self.assertGreater(wallet_tx.wallet_tx_id, 0)

            # 5. Verify relationships on new models
            loaded_wallet = session.execute(select(UserWallet).where(UserWallet.wallet_id == wallet.wallet_id)).scalar_one()
            self.assertEqual(len(loaded_wallet.transactions), 1)
            self.assertEqual(loaded_wallet.transactions[0].tx_type, "ServiceIncome")
            print("  [OK] PASS  |  New Services, Orders, and Wallet models verified in isolated in-memory DB")
        finally:
            session.close()

if __name__ == '__main__':
    print("========================================================================")
    print("   CampusLink Stage 1.3: SQLAlchemy 2.0 Declarative Models Test Suite")
    print("========================================================================")
    unittest.main()
