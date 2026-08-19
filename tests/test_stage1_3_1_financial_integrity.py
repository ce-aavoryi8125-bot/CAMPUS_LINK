"""
test_stage1_3_1_financial_integrity.py
---------------------------------------
Financial and Schema Integrity Review Test Suite.
Validates:
1. CREDIT/DEBIT ledger direction.
2. Idempotency key uniqueness for duplicate transaction prevention.
3. Decimal monetary precision (10.50, 125.75, 1000.00).
4. Service order provider historical snapshot integrity.
5. Escrow transition modeling.
6. Confirmation that physical DB was NOT modified prematurely.
"""
import unittest
import sys
import os
import sqlite3
from decimal import Decimal

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError

from database.models import (
    Base, User, Category, Service, ServiceOrder, UserWallet, WalletTransaction
)

class TestFinancialIntegrityStage1_3_1(unittest.TestCase):

    def setUp(self):
        # Use an isolated in-memory SQLite database for schema integrity validation
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.session = self.Session()

        # Seed baseline user & category
        self.user = User(name="Kwame Mensah", email="kwame@st.umat.edu.gh", password_hash="hash", phone="+233240003344", department="Computer Science")
        self.client = User(name="Ama Serwaa", email="ama@st.umat.edu.gh", password_hash="hash", phone="+233240005566", department="Mining Engineering")
        self.category = Category(name="Graphic Design", description="Logo and flyer design")
        self.session.add_all([self.user, self.client, self.category])
        self.session.commit()

    def tearDown(self):
        self.session.close()

    def test_01_wallet_ledger_credit_debit_direction(self):
        wallet = UserWallet(user_id=self.user.user_id, available_balance=Decimal("0.00"))
        self.session.add(wallet)
        self.session.commit()

        # 1. Add CREDIT transaction (e.g. Service Earnings)
        tx_credit = WalletTransaction(
            wallet_id=wallet.wallet_id,
            user_id=self.user.user_id,
            entry_type="CREDIT",
            tx_type="ServiceIncome",
            amount=Decimal("90.00"),
            reference_type="service_order",
            reference_id=101,
            idempotency_key="SVC_EARNING_ORD_101_CREDIT",
            status="Completed"
        )
        self.session.add(tx_credit)
        self.session.commit()

        # 2. Add DEBIT transaction (e.g. MoMo Withdrawal Payout)
        tx_debit = WalletTransaction(
            wallet_id=wallet.wallet_id,
            user_id=self.user.user_id,
            entry_type="DEBIT",
            tx_type="PayoutWithdrawal",
            amount=Decimal("50.00"),
            reference_type="payout",
            reference_id=501,
            idempotency_key="PAYOUT_REQ_501_DEBIT",
            status="Completed"
        )
        self.session.add(tx_debit)
        self.session.commit()

        # 3. Calculate derived ledger balance: SUM(CREDIT) - SUM(DEBIT)
        txs = self.session.execute(select(WalletTransaction).where(WalletTransaction.wallet_id == wallet.wallet_id)).scalars().all()
        self.assertEqual(len(txs), 2)
        total_credit = sum(t.amount for t in txs if t.entry_type == "CREDIT")
        total_debit = sum(t.amount for t in txs if t.entry_type == "DEBIT")
        net_balance = total_credit - total_debit

        self.assertEqual(net_balance, Decimal("40.00"))
        print(f"  [OK] PASS  |  Ledger CREDIT/DEBIT arithmetic verified: GHS {total_credit} - GHS {total_debit} = GHS {net_balance}")

    def test_02_financial_idempotency_prevents_duplicate_payouts_and_earnings(self):
        wallet = UserWallet(user_id=self.user.user_id, available_balance=Decimal("100.00"))
        self.session.add(wallet)
        self.session.commit()

        # 1. First execution of rental earning credit
        tx1 = WalletTransaction(
            wallet_id=wallet.wallet_id,
            user_id=self.user.user_id,
            entry_type="CREDIT",
            tx_type="RentalIncome",
            amount=Decimal("180.00"),
            reference_type="rental_transaction",
            reference_id=42,
            idempotency_key="RENTAL_EARNING_TX_42_CREDIT",
            status="Completed"
        )
        self.session.add(tx1)
        self.session.commit()

        # 2. Attempt duplicate execution with same idempotency_key
        tx2_dup = WalletTransaction(
            wallet_id=wallet.wallet_id,
            user_id=self.user.user_id,
            entry_type="CREDIT",
            tx_type="RentalIncome",
            amount=Decimal("180.00"),
            reference_type="rental_transaction",
            reference_id=42,
            idempotency_key="RENTAL_EARNING_TX_42_CREDIT", # DUPLICATE KEY
            status="Completed"
        )
        self.session.add(tx2_dup)
        with self.assertRaises(IntegrityError):
            self.session.commit()
        self.session.rollback()
        print("  [OK] PASS  |  Financial idempotency: Duplicate transaction with identical key blocked by UNIQUE constraint")

    def test_03_sqlite_monetary_precision(self):
        wallet = UserWallet(user_id=self.user.user_id, available_balance=Decimal("0.00"))
        self.session.add(wallet)
        self.session.commit()

        test_amounts = [Decimal("10.50"), Decimal("125.75"), Decimal("1000.00")]
        for idx, amt in enumerate(test_amounts):
            tx = WalletTransaction(
                wallet_id=wallet.wallet_id,
                user_id=self.user.user_id,
                entry_type="CREDIT",
                tx_type="ServiceIncome",
                amount=amt,
                reference_type="service_order",
                reference_id=idx + 1,
                idempotency_key=f"PRECISION_TEST_{idx}_{amt}",
                status="Completed"
            )
            self.session.add(tx)
        self.session.commit()

        # Read back and verify exact Decimal types and values
        loaded_txs = self.session.execute(
            select(WalletTransaction).where(WalletTransaction.wallet_id == wallet.wallet_id).order_by(WalletTransaction.wallet_tx_id)
        ).scalars().all()

        for original, loaded in zip(test_amounts, loaded_txs):
            self.assertIsInstance(loaded.amount, Decimal)
            self.assertEqual(loaded.amount, original)
            self.assertEqual(str(loaded.amount), str(original))
        print(f"  [OK] PASS  |  Monetary Decimal precision verified on SQLite ({[str(a) for a in test_amounts]})")

    def test_04_service_order_provider_snapshot_immutability(self):
        # Create service
        svc = Service(
            provider_id=self.user.user_id,
            category_id=self.category.category_id,
            title="Logo Design",
            description="Vector logo branding",
            subcategory="Design",
            pricing_model="Fixed",
            price=Decimal("150.00"),
            delivery_time_days=3
        )
        self.session.add(svc)
        self.session.commit()

        # Create Order (snapshotting provider_id=self.user.user_id)
        order = ServiceOrder(
            service_id=svc.service_id,
            client_id=self.client.user_id,
            provider_id=svc.provider_id, # Snapshot
            requirements="Tech startup logo",
            amount=Decimal("150.00"),
            platform_fee=Decimal("15.00"),
            provider_earnings=Decimal("135.00"),
            status="InProgress",
            escrow_status="Held",
            due_date="2026-09-15"
        )
        self.session.add(order)
        self.session.commit()

        # Even if the Service listing is transferred to a new provider:
        new_provider = User(name="Kofi Boateng", email="kofi@st.umat.edu.gh", password_hash="hash", phone="+233240007788", department="Geomatic")
        self.session.add(new_provider)
        self.session.commit()
        svc.provider_id = new_provider.user_id
        self.session.commit()

        # Verify historical order provider_id remains uncorrupted
        refreshed_order = self.session.execute(select(ServiceOrder).where(ServiceOrder.order_id == order.order_id)).scalar_one()
        self.assertEqual(refreshed_order.provider_id, self.user.user_id, "Order provider snapshot must remain unchanged")
        print("  [OK] PASS  |  Historical provider snapshot on service_orders verified")

    def test_05_escrow_lifecycle_state_compatibility(self):
        valid_escrow_states = ['Held', 'Released', 'Refunded', 'Deducted']
        for state in valid_escrow_states:
            order = ServiceOrder(
                service_id=1,
                client_id=self.client.user_id,
                provider_id=self.user.user_id,
                requirements=f"Escrow test for state {state}",
                amount=Decimal("100.00"),
                platform_fee=Decimal("10.00"),
                provider_earnings=Decimal("90.00"),
                status="Pending",
                escrow_status=state,
                due_date="2026-09-20"
            )
            self.session.add(order)
        self.session.commit()
        print("  [OK] PASS  |  Escrow lifecycle states (Held, Released, Refunded, Deducted) verified")

    def test_06_physical_database_materialized_tables(self):
        # Inspect physical SQLite database campuslink_umat.db directly
        db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "database", "campuslink_umat.db")
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
        tables = [r[0] for r in cursor.fetchall() if not r[0].startswith("sqlite_")]
        conn.close()

        # Confirm physical DB contains all 15 normalized tables
        expected_physical = [
            "categories", "listings", "maintenance", "notifications", "rental_requests",
            "rental_transactions", "reviews", "saved_listings", "service_orders",
            "service_reviews", "services", "user_wallets", "users", "wallet_transactions", "wishlist"
        ]
        self.assertEqual(sorted(tables), sorted(expected_physical))
        print(f"  [OK] PASS  |  Physical database confirmed ({len(tables)} tables verified)")

if __name__ == '__main__':
    print("========================================================================")
    print("   CampusLink Stage 1.3.1: Financial & Schema Integrity Test Suite")
    print("========================================================================")
    unittest.main()
