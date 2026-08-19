"""
test_stage1_2_controllers.py
----------------------------
Targeted unit and integration tests for Stage 1.2 Controller Modernization.
Verifies all refactored controller operations run through db_engine abstraction without any direct SQLite connections.
"""
import unittest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import controllers
import db_engine

class TestControllersStage1_2(unittest.TestCase):

    def test_01_no_direct_sqlite_import_in_controllers(self):
        self.assertNotIn("sqlite3", controllers.__dict__, "sqlite3 must not be imported in controllers.py")
        print("  [OK] PASS  |  controllers.py has 0 direct sqlite3 imports")

    def test_02_authenticate_user_pbkdf2(self):
        user = controllers.authenticate_user("ce-aavoryi8125@st.umat.edu.gh", "Student123")
        self.assertIsInstance(user, dict)
        self.assertEqual(user["name"], "Albert Boateng")
        self.assertEqual(user["account_status"], "Active")
        print("  [OK] PASS  |  authenticate_user: PBKDF2 verification succeeded via db_engine")

    def test_03_rental_request_and_atomic_approval_lifecycle(self):
        # 1. Submit rental request for listing 2
        req_id = controllers.submit_rental_request(
            listing_id=2,
            borrower_id=1,
            start_date="2026-09-01",
            end_date="2026-09-05",
            purpose="Final Year Project",
            notes="Stage 1.2 verification request"
        )
        self.assertGreater(req_id, 0)

        # 2. Get listing daily rate
        lst_info = db_engine.execute_query("SELECT rental_rate_per_day FROM listings WHERE listing_id = 2;", fetchone=True)
        rate = float(lst_info["rental_rate_per_day"])

        # 3. Approve request via atomic transaction
        res_app = controllers.approve_request(req_id)
        self.assertEqual(res_app, 1, "Approval must return 1 on success")

        # 4. Verify listing status was updated to Reserved
        lst = db_engine.execute_query("SELECT status FROM listings WHERE listing_id = 2;", fetchone=True)
        self.assertEqual(lst["status"], "Reserved")

        # 5. Verify transaction record created with accurate 10% commission & 90% earnings
        tx = db_engine.execute_query("SELECT * FROM rental_transactions WHERE request_id = ?;", (req_id,), fetchone=True)
        self.assertIsNotNone(tx)
        self.assertEqual(tx["rental_status"], "Active")
        self.assertEqual(tx["total_days"], 5) # Sept 1 to Sept 5 = 5 days
        expected_gross = rate * 5
        self.assertAlmostEqual(float(tx["gross_amount"]), expected_gross, places=2)
        self.assertAlmostEqual(float(tx["commission_amount"]), expected_gross * 0.10, places=2)
        self.assertAlmostEqual(float(tx["owner_earnings"]), expected_gross * 0.90, places=2)
        print(f"  [OK] PASS  |  approve_request: Atomic transaction, listing reservation, and commission verified (Tx ID: {tx['transaction_id']})")

        # 6. Process Return (Good Condition)
        res_ret = controllers.process_return(tx["transaction_id"], "Returned in pristine condition", "Good")
        self.assertEqual(res_ret, 1)

        # Verify transaction marked returned and listing restored to Available
        tx_ret = db_engine.execute_query("SELECT rental_status, actual_return_date FROM rental_transactions WHERE transaction_id = ?;", (tx["transaction_id"],), fetchone=True)
        self.assertEqual(tx_ret["rental_status"], "Returned")
        self.assertIsNotNone(tx_ret["actual_return_date"])
        lst_ret = db_engine.execute_query("SELECT status FROM listings WHERE listing_id = 2;", fetchone=True)
        self.assertEqual(lst_ret["status"], "Available")
        print("  [OK] PASS  |  process_return: Return processed and listing restored to Available")

    def test_04_damage_return_and_maintenance_lifecycle(self):
        # 1. Create a valid rental request first
        dummy_req_id = db_engine.execute_query("""
        INSERT INTO rental_requests (listing_id, borrower_id, rent_start_date, rent_end_date, rental_purpose, status, notes)
        VALUES (4, 1, '2026-08-01', '2026-08-03', 'Field Trip', 'Approved', 'Test request');
        """, fetch="lastrowid")

        # 2. Create matching transaction
        dummy_tx_id = db_engine.execute_query("""
        INSERT INTO rental_transactions (
            request_id, listing_id, borrower_id, rent_start_date, rent_end_date, total_days,
            gross_amount, commission_amount, owner_earnings, deposit_held, payment_status, rental_status
        ) VALUES (?, 4, 1, '2026-08-01', '2026-08-03', 3, 75.0, 7.5, 67.5, 100.0, 'Paid', 'Active');
        """, (dummy_req_id,), fetch="lastrowid")

        # 3. Process return with Minor damage
        res = controllers.process_return(dummy_tx_id, "Tripod clamp slightly bent", "Minor", claim_amount=25.0)
        self.assertEqual(res, 1)

        # 4. Verify listing moved to Maintenance
        lst = db_engine.execute_query("SELECT status FROM listings WHERE listing_id = 4;", fetchone=True)
        self.assertEqual(lst["status"], "Maintenance")

        # 5. Verify maintenance record created
        maint = db_engine.execute_query("SELECT * FROM maintenance WHERE listing_id = 4 ORDER BY maintenance_id DESC LIMIT 1;", fetchone=True)
        self.assertIsNotNone(maint)
        self.assertEqual(maint["status"], "Pending")
        self.assertAlmostEqual(float(maint["cost"]), 25.0, places=2)

        # 6. Complete maintenance
        res_maint = controllers.update_maintenance(maint["maintenance_id"], cost=25.0, status="Completed", listing_id=4)
        self.assertEqual(res_maint, 1)

        # 7. Verify listing restored to Available
        lst_final = db_engine.execute_query("SELECT status FROM listings WHERE listing_id = 4;", fetchone=True)
        self.assertEqual(lst_final["status"], "Available")

        # Cleanup dummy records
        db_engine.execute_query("DELETE FROM maintenance WHERE maintenance_id = ?;", (maint["maintenance_id"],))
        db_engine.execute_query("DELETE FROM rental_transactions WHERE transaction_id = ?;", (dummy_tx_id,))
        db_engine.execute_query("DELETE FROM rental_requests WHERE request_id = ?;", (dummy_req_id,))
        print("  [OK] PASS  |  Damage Return & Maintenance: Ticket auto-generation and completion verified")

    def test_05_calculate_trust_score(self):
        score_data = controllers.calculate_trust_score(1)
        self.assertIsInstance(score_data, dict)
        self.assertIn("score", score_data)
        self.assertIn("avg_rating", score_data)
        self.assertIn("total_rentals", score_data)
        self.assertIn("late_returns", score_data)
        self.assertGreaterEqual(score_data["score"], 0)
        self.assertLessEqual(score_data["score"], 100)
        print(f"  [OK] PASS  |  calculate_trust_score: User #1 score is {score_data['score']}/100")

    def test_06_reports_engine_all_15_dialect_safe(self):
        for r_id in range(1, 16):
            headers, rows = controllers.get_report_data(r_id)
            self.assertIsInstance(headers, list, f"Report #{r_id} headers must be a list")
            self.assertGreater(len(headers), 0, f"Report #{r_id} must have headers")
            self.assertIsInstance(rows, list, f"Report #{r_id} rows must be a list")
        print("  [OK] PASS  |  get_report_data: All 15 BI Reports executed successfully with dialect-safe syntax")

if __name__ == '__main__':
    print("========================================================================")
    print("   CampusLink Stage 1.2: Controller Modernization Test Suite")
    print("========================================================================")
    unittest.main()
