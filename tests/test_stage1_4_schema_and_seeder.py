"""
test_stage1_4_schema_and_seeder.py
----------------------------------
Targeted unit and integration tests for Stage 1.4 Schema DDL, Cascade Protection & Seeder Evolution.
Verifies all 15 physical tables, constraints, foreign keys, cascade protection,
one-wallet-per-user enforcement, financial idempotency, and seeder idempotency.
"""
import unittest
import sys
import os
import sqlite3
from decimal import Decimal

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import db_engine
from database import db_seeder, database_schema

class TestSchemaAndSeederStage1_4(unittest.TestCase):

    def setUp(self):
        self.db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "database", "campuslink_umat.db")

    def test_01_all_15_physical_tables_exist(self):
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
        tables = [r[0] for r in cur.fetchall() if not r[0].startswith("sqlite_")]
        conn.close()

        expected_tables = [
            "categories", "listings", "maintenance", "notifications", "rental_requests",
            "rental_transactions", "reviews", "saved_listings", "service_orders",
            "service_reviews", "services", "user_wallets", "users", "wallet_transactions", "wishlist"
        ]
        for tbl in expected_tables:
            self.assertIn(tbl, tables, f"Physical table '{tbl}' must exist in database")
        self.assertEqual(len(tables), 15)
        print(f"  [OK] PASS  |  All 15 physical tables materialized in SQLite database ({len(tables)} tables)")

    def test_02_services_table_structure_and_constraints(self):
        services = db_engine.execute_query("SELECT * FROM services ORDER BY service_id ASC;", fetch="all")
        self.assertGreaterEqual(len(services), 6)
        first_svc = services[0]
        self.assertIn("provider_id", first_svc)
        self.assertIn("category_id", first_svc)
        self.assertIn("pricing_model", first_svc)
        self.assertIn("price", first_svc)
        self.assertIn("delivery_time_days", first_svc)
        self.assertIn("status", first_svc)

        # Verify CHECK constraint on pricing_model
        with self.assertRaises(Exception):
            db_engine.execute_query("""
            INSERT INTO services (provider_id, category_id, title, description, subcategory, pricing_model, price, delivery_time_days, status)
            VALUES (1, 1, 'Bad Model Service', 'Desc', 'Sub', 'InvalidPricingModel', 50.0, 2, 'Active');
            """)
        print("  [OK] PASS  |  services: Columns and pricing_model CHECK constraints verified")

    def test_03_one_wallet_per_user_unique_constraint(self):
        wallets = db_engine.execute_query("SELECT * FROM user_wallets ORDER BY user_id ASC;", fetch="all")
        self.assertGreaterEqual(len(wallets), 6)

        # Attempt to insert a second wallet for user_id = 1 (must fail)
        with self.assertRaises(Exception):
            db_engine.execute_query("""
            INSERT INTO user_wallets (user_id, available_balance, pending_balance, locked_escrow, total_earned, total_withdrawn)
            VALUES (1, 100.0, 0.0, 0.0, 100.0, 0.0);
            """)
        print("  [OK] PASS  |  user_wallets: One-wallet-per-user UNIQUE constraint verified")

    def test_04_wallet_transactions_idempotency_and_entry_type(self):
        txs = db_engine.execute_query("SELECT * FROM wallet_transactions;", fetch="all")
        self.assertGreaterEqual(len(txs), 3)

        # Verify entry_type constraint (CREDIT or DEBIT)
        with self.assertRaises(Exception):
            db_engine.execute_query("""
            INSERT INTO wallet_transactions (wallet_id, user_id, entry_type, tx_type, amount, reference_type, reference_id, idempotency_key, status)
            VALUES (1, 1, 'INVALID_ENTRY', 'RentalIncome', 50.0, 'rental_transaction', 99, 'BAD_ENTRY_KEY', 'Completed');
            """)

        # Verify unique idempotency_key rejection
        with self.assertRaises(Exception):
            db_engine.execute_query("""
            INSERT INTO wallet_transactions (wallet_id, user_id, entry_type, tx_type, amount, reference_type, reference_id, idempotency_key, status)
            VALUES (1, 1, 'CREDIT', 'RentalIncome', 50.0, 'rental_transaction', 1, 'DEMO_RENTAL_EARNING_TX_1_CREDIT', 'Completed');
            """)
        print("  [OK] PASS  |  wallet_transactions: entry_type (CREDIT/DEBIT) and idempotency_key uniqueness verified")

    def test_05_cascade_protection_on_financial_history(self):
        # Attempting to delete a user who has active transactions or a wallet must fail with FOREIGN KEY constraint error
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA foreign_keys = ON;")
        cur = conn.cursor()
        with self.assertRaises(sqlite3.IntegrityError):
            cur.execute("DELETE FROM users WHERE user_id = 1;")
        conn.close()
        print("  [OK] PASS  |  Cascade protection: Deleting user with financial history blocked by ON DELETE RESTRICT")

    def test_06_seeder_idempotency(self):
        # Running the seeder a second time must execute cleanly without error
        try:
            db_seeder.seed_database()
            seeder_passed = True
        except Exception as e:
            seeder_passed = False
            print(f"Seeder idempotency failure: {e}")

        self.assertTrue(seeder_passed)
        # Verify row counts remain consistent
        counts = db_engine.execute_query("SELECT (SELECT COUNT(*) FROM users) as u, (SELECT COUNT(*) FROM listings) as l, (SELECT COUNT(*) FROM services) as s;", fetchone=True)
        self.assertEqual(counts["u"], 8)
        self.assertEqual(counts["l"], 61)
        self.assertEqual(counts["s"], 6)
        print("  [OK] PASS  |  db_seeder.seed_database() idempotency verified (clean repeat execution with 8 users)")

if __name__ == '__main__':
    print("========================================================================")
    print("   CampusLink Stage 1.4: Schema DDL & Seeder Test Suite")
    print("========================================================================")
    unittest.main()
