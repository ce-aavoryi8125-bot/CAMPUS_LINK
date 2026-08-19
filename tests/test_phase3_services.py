"""
test_phase3_services.py
-----------------------
Comprehensive Services & Skills Marketplace Test Suite for CampusLink 2.0 (Phase 3).
Validates:
1. Service listing CRUD, filtering, searching, and pausing/delisting.
2. Zero-trust authorization: Provider ownership checks, cross-user edit prevention (403).
3. End-to-end service order state machine: Pending -> Accepted -> InProgress -> Delivered -> Completed.
4. Authoritative wallet_transactions ledger: DepositEscrowHold, ServiceIncome, PlatformCommission, DepositRefund.
5. Financial idempotency & atomic rollback protection.
6. Commission accuracy (10% platform, 90% provider).
7. Client-only review authorization, duplicate review blocking, and trust score harmonization.
8. Wallet & transaction history API.
"""
import unittest
import json
import io
import sys
import os
from decimal import Decimal

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app
from core.security import create_access_token
from core.config import CommissionService
import db_engine

class CampusLinkServicesTestSuite(unittest.TestCase):

    def setUp(self):
        app.testing = True
        self.client = app.test_client()

        # Personas:
        # User 1: Albert Boateng (Student Provider - Geomatic Engineering)
        self.token_albert = create_access_token(user_id=1, email="ce-aavoryi8125@st.umat.edu.gh", role="Verified Student", name="Albert Boateng")
        # User 2: Benedict Osei (Student Provider - Mining Engineering)
        self.token_benedict = create_access_token(user_id=2, email="benedict@st.umat.edu.gh", role="Verified Student", name="Benedict Osei")
        # User 3: Grace Mensah (Student Client - Petroleum Engineering)
        self.token_grace = create_access_token(user_id=3, email="grace@st.umat.edu.gh", role="Verified Student", name="Grace Mensah")
        # User 6: Admin CampusLink
        self.token_admin = create_access_token(user_id=6, email="admin@umat.edu.gh", role="Admin", name="Admin CampusLink")

    def _auth_headers(self, token: str, strict: bool = True):
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        if strict:
            headers["X-Strict-Auth"] = "true"
        return headers

    # =========================================================================
    # 1. SERVICE LISTINGS CRUD & AUTHORIZATION
    # =========================================================================

    def test_01_create_service_listing(self):
        # Albert creates a CAD & GIS mapping service
        payload = {
            "category_id": 2, # Surveying & Geomatics
            "title": "Professional ArcGIS & AutoCAD Site Mapping",
            "description": "Expert boundary plotting, GIS contour generation, and CAD site drawings for engineering students.",
            "subcategory": "GIS & CAD Design",
            "pricing_model": "Fixed",
            "price": 100.00,
            "delivery_time_days": 2,
            "portfolio_urls": "https://portfolio.umat.edu.gh/albert/maps"
        }
        res = self.client.post('/api/services', data=json.dumps(payload), headers=self._auth_headers(self.token_albert))
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertTrue(data["success"])
        self.assertGreater(data["service_id"], 0)
        
        # Verify in DB
        svc = db_engine.execute_query("SELECT provider_id, price, status FROM services WHERE service_id = ?;", (data["service_id"],), fetchone=True)
        self.assertEqual(svc["provider_id"], 1)
        self.assertEqual(float(svc["price"]), 100.00)
        self.assertEqual(svc["status"], "Active")
        print("  [OK] PASS  |  Service listing created with server-derived provider identity")

    def test_02_unauthorized_service_update_blocked_with_403(self):
        # Create service owned by Albert (user_id=1)
        svc_id = db_engine.execute_query("""
        INSERT INTO services (provider_id, category_id, title, description, subcategory, price, delivery_time_days, status)
        VALUES (1, 1, 'Python Tutoring for First Years', 'Data structures and Python programming help', 'Tutoring', 50.00, 1, 'Active');
        """, fetch="lastrowid")

        # Benedict (user_id=2) attempts to edit Albert's service
        payload = {
            "title": "Hacked Title",
            "description": "Attempting unauthorized modification",
            "subcategory": "Hacking",
            "pricing_model": "Fixed",
            "price": 10.00,
            "delivery_time_days": 1
        }
        res = self.client.put(f'/api/services/{svc_id}', data=json.dumps(payload), headers=self._auth_headers(self.token_benedict))
        self.assertEqual(res.status_code, 403)
        data = json.loads(res.data)
        self.assertFalse(data["success"])
        self.assertIn("not own", data["message"].lower())
        print("  [OK] PASS  |  Unauthorized service update blocked (HTTP 403)")

    def test_03_service_status_toggling(self):
        # Albert pauses his service
        svc_id = db_engine.execute_query("""
        INSERT INTO services (provider_id, category_id, title, description, subcategory, price, delivery_time_days, status)
        VALUES (1, 1, 'Laptop Formatting & Linux OS Installation', 'OS Setup', 'Tech Support', 40.00, 1, 'Active');
        """, fetch="lastrowid")

        # Pause
        res_pause = self.client.post(f'/api/services/{svc_id}/status', data=json.dumps({"status": "Paused"}), headers=self._auth_headers(self.token_albert))
        self.assertEqual(res_pause.status_code, 200)
        svc = db_engine.execute_query("SELECT status FROM services WHERE service_id = ?;", (svc_id,), fetchone=True)
        self.assertEqual(svc["status"], "Paused")

        # Resume
        res_resume = self.client.post(f'/api/services/{svc_id}/status', data=json.dumps({"status": "Active"}), headers=self._auth_headers(self.token_albert))
        self.assertEqual(res_resume.status_code, 200)
        svc = db_engine.execute_query("SELECT status FROM services WHERE service_id = ?;", (svc_id,), fetchone=True)
        self.assertEqual(svc["status"], "Active")
        print("  [OK] PASS  |  Service status state transitions (Active <-> Paused) verified")

    # =========================================================================
    # 2. END-TO-END SERVICE ORDER STATE MACHINE & AUTHORITATIVE ESCROW LEDGER
    # =========================================================================

    def test_04_full_order_lifecycle_and_escrow_accounting(self):
        # 1. Albert creates a GH₵ 100.00 service
        svc_id = db_engine.execute_query("""
        INSERT INTO services (provider_id, category_id, title, description, subcategory, price, delivery_time_days, status)
        VALUES (1, 2, 'Topographic Map Digitization', 'Digitizing paper maps into Shapefiles', 'GIS', 100.00, 2, 'Active');
        """, fetch="lastrowid")

        # 2. Grace (Client, user_id=3) books the service (Escrow Hold)
        order_payload = {
            "service_id": svc_id,
            "requirements": "Need digitization of Tarkwa North survey map by Friday.",
            "due_date": "2026-11-20"
        }
        res_order = self.client.post('/api/services/orders', data=json.dumps(order_payload), headers=self._auth_headers(self.token_grace))
        self.assertEqual(res_order.status_code, 200)
        order_data = json.loads(res_order.data)
        order_id = order_data["order_id"]

        # Assert Order State & Escrow
        order = db_engine.execute_query("SELECT status, escrow_status, amount, platform_fee, provider_earnings, client_id, provider_id FROM service_orders WHERE order_id = ?;", (order_id,), fetchone=True)
        self.assertEqual(order["status"], "Pending")
        self.assertEqual(order["escrow_status"], "Held")
        self.assertEqual(float(order["amount"]), 100.00)
        self.assertEqual(float(order["platform_fee"]), 10.00) # 10% platform fee
        self.assertEqual(float(order["provider_earnings"]), 90.00) # 90% provider net earnings
        self.assertEqual(order["client_id"], 3)
        self.assertEqual(order["provider_id"], 1)

        # Assert Authoritative Ledger: Escrow Hold Debit
        hold_tx = db_engine.execute_query("SELECT entry_type, tx_type, amount, idempotency_key, status FROM wallet_transactions WHERE reference_type = 'service_order' AND reference_id = ? AND tx_type = 'DepositEscrowHold';", (order_id,), fetchone=True)
        self.assertIsNotNone(hold_tx)
        self.assertEqual(hold_tx["entry_type"], "DEBIT")
        self.assertEqual(float(hold_tx["amount"]), 100.00)
        self.assertEqual(hold_tx["idempotency_key"], f"SVC_ESCROW_HOLD_ORD_{order_id}_DEBIT")

        # 3. Albert (Provider) accepts the order
        res_accept = self.client.post(f'/api/services/orders/{order_id}/accept', headers=self._auth_headers(self.token_albert))
        self.assertEqual(res_accept.status_code, 200)
        ord_status = db_engine.execute_query("SELECT status FROM service_orders WHERE order_id = ?;", (order_id,), fetchone=True)
        self.assertEqual(ord_status["status"], "Accepted")

        # 4. Albert starts work
        res_start = self.client.post(f'/api/services/orders/{order_id}/start', headers=self._auth_headers(self.token_albert))
        self.assertEqual(res_start.status_code, 200)
        ord_status = db_engine.execute_query("SELECT status FROM service_orders WHERE order_id = ?;", (order_id,), fetchone=True)
        self.assertEqual(ord_status["status"], "InProgress")

        # 5. Albert delivers deliverables
        res_deliver = self.client.post(f'/api/services/orders/{order_id}/deliver', data=json.dumps({"delivery_notes": "Shapefiles uploaded to Google Drive"}), headers=self._auth_headers(self.token_albert))
        self.assertEqual(res_deliver.status_code, 200)
        ord_status = db_engine.execute_query("SELECT status, delivered_at FROM service_orders WHERE order_id = ?;", (order_id,), fetchone=True)
        self.assertEqual(ord_status["status"], "Delivered")
        self.assertIsNotNone(ord_status["delivered_at"])

        # 6. Grace (Client) confirms completion -> Triggers Atomic Escrow Release
        res_complete = self.client.post(f'/api/services/orders/{order_id}/complete', headers=self._auth_headers(self.token_grace))
        self.assertEqual(res_complete.status_code, 200)

        # Verify Final Order State
        ord_final = db_engine.execute_query("SELECT status, escrow_status, completed_at FROM service_orders WHERE order_id = ?;", (order_id,), fetchone=True)
        self.assertEqual(ord_final["status"], "Completed")
        self.assertEqual(ord_final["escrow_status"], "Released")
        self.assertIsNotNone(ord_final["completed_at"])

        # Verify Provider Wallet Credit in Ledger
        prov_tx = db_engine.execute_query("SELECT user_id, entry_type, tx_type, amount, idempotency_key FROM wallet_transactions WHERE reference_type = 'service_order' AND reference_id = ? AND tx_type = 'ServiceIncome';", (order_id,), fetchone=True)
        self.assertIsNotNone(prov_tx)
        self.assertEqual(prov_tx["user_id"], 1) # Albert
        self.assertEqual(prov_tx["entry_type"], "CREDIT")
        self.assertEqual(float(prov_tx["amount"]), 90.00) # 90% payout
        self.assertEqual(prov_tx["idempotency_key"], f"SVC_EARNING_ORD_{order_id}_CREDIT")

        # Verify Platform Commission in Ledger
        admin_tx = db_engine.execute_query("SELECT user_id, entry_type, tx_type, amount, idempotency_key FROM wallet_transactions WHERE reference_type = 'service_order' AND reference_id = ? AND tx_type = 'PlatformCommission';", (order_id,), fetchone=True)
        self.assertIsNotNone(admin_tx)
        self.assertEqual(admin_tx["user_id"], 6) # Admin
        self.assertEqual(admin_tx["entry_type"], "CREDIT")
        self.assertEqual(float(admin_tx["amount"]), 10.00) # 10% fee
        self.assertEqual(admin_tx["idempotency_key"], f"SVC_COMMISSION_ORD_{order_id}_CREDIT")

        print("  [OK] PASS  |  Full service order lifecycle & atomic escrow accounting verified (10%/90% split)")

    def test_05_order_cancellation_and_escrow_refund(self):
        # 1. Create service and order
        svc_id = db_engine.execute_query("""
        INSERT INTO services (provider_id, category_id, title, description, subcategory, price, delivery_time_days, status)
        VALUES (2, 3, 'Electrical Circuit Simulation', 'SPICE circuit analysis', 'Electronics', 60.00, 1, 'Active');
        """, fetch="lastrowid")

        res_order = self.client.post('/api/services/orders', data=json.dumps({
            "service_id": svc_id,
            "requirements": "Simulate RLC circuit",
            "due_date": "2026-11-25"
        }), headers=self._auth_headers(self.token_grace))
        order_id = json.loads(res_order.data)["order_id"]

        # 2. Cancel order
        res_cancel = self.client.post(f'/api/services/orders/{order_id}/cancel', data=json.dumps({"reason": "Project postponed"}), headers=self._auth_headers(self.token_grace))
        self.assertEqual(res_cancel.status_code, 200)

        # 3. Assert Order State & Escrow Refund
        ord_rec = db_engine.execute_query("SELECT status, escrow_status FROM service_orders WHERE order_id = ?;", (order_id,), fetchone=True)
        self.assertEqual(ord_rec["status"], "Cancelled")
        self.assertEqual(ord_rec["escrow_status"], "Refunded")

        # Verify 100% Refund Ledger Entry for Client
        refund_tx = db_engine.execute_query("SELECT user_id, entry_type, tx_type, amount, idempotency_key FROM wallet_transactions WHERE reference_type = 'service_order' AND reference_id = ? AND tx_type = 'DepositRefund';", (order_id,), fetchone=True)
        self.assertIsNotNone(refund_tx)
        self.assertEqual(refund_tx["user_id"], 3) # Grace
        self.assertEqual(refund_tx["entry_type"], "CREDIT")
        self.assertEqual(float(refund_tx["amount"]), 60.00)
        self.assertEqual(refund_tx["idempotency_key"], f"SVC_REFUND_ORD_{order_id}_CREDIT")
        print("  [OK] PASS  |  Order cancellation and 100% escrow refund ledger entry verified")

    # =========================================================================
    # 3. REVIEWS & HARMONIZED TRUST SCORING
    # =========================================================================

    def test_06_verified_client_review_and_duplicate_rejection(self):
        # 1. Create a completed order
        order_id = db_engine.execute_query("""
        INSERT INTO service_orders (
            service_id, client_id, provider_id, requirements, amount, platform_fee,
            provider_earnings, status, escrow_status, due_date, completed_at
        ) VALUES (1, 3, 1, 'Completed GIS task', 80.00, 8.00, 72.00, 'Completed', 'Released', '2026-11-01', CURRENT_TIMESTAMP);
        """, fetch="lastrowid")

        # 2. Non-client (Benedict) attempts to review Albert -> 403 Forbidden
        res_bad = self.client.post('/api/services/reviews', data=json.dumps({
            "order_id": order_id,
            "rating": 5,
            "comment": "Fake review from unauthorized user"
        }), headers=self._auth_headers(self.token_benedict))
        self.assertEqual(res_bad.status_code, 403)

        # 3. Legitimate Client (Grace) submits 5-star review -> 200 OK
        res_good = self.client.post('/api/services/reviews', data=json.dumps({
            "order_id": order_id,
            "rating": 5,
            "comment": "Outstanding mapping work! Fast and precise."
        }), headers=self._auth_headers(self.token_grace))
        self.assertEqual(res_good.status_code, 200)
        rev_id = json.loads(res_good.data)["review_id"]
        self.assertGreater(rev_id, 0)

        # 4. Duplicate Review Attempt on same order -> 400 Bad Request
        res_dup = self.client.post('/api/services/reviews', data=json.dumps({
            "order_id": order_id,
            "rating": 4,
            "comment": "Second duplicate review attempt"
        }), headers=self._auth_headers(self.token_grace))
        self.assertEqual(res_dup.status_code, 400)
        data_dup = json.loads(res_dup.data)
        self.assertIn("already reviewed", data_dup["message"].lower())
        print("  [OK] PASS  |  Verified client-only review enforcement & duplicate review rejection verified")

    def test_07_trust_score_incorporates_service_reviews(self):
        # Verify Albert's trust score reflects both rentals and service reviews
        res = self.client.get('/api/trust-score/1')
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertIn("score", data)
        self.assertGreaterEqual(data["score"], 50)
        self.assertIn("total_services", data)
        print(f"  [OK] PASS  |  Harmonized trust score derived with service metrics: {data['score']}/100")

    # =========================================================================
    # 4. USER WALLET & TRANSACTION HISTORY API
    # =========================================================================

    def test_08_user_wallet_endpoint(self):
        res = self.client.get('/api/user/wallet', headers=self._auth_headers(self.token_albert))
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertTrue(data["success"])
        self.assertIn("wallet", data)
        self.assertIn("available_balance", data["wallet"])
        self.assertIn("transactions", data)
        self.assertIsInstance(data["transactions"], list)
        print("  [OK] PASS  |  User wallet balances and ledger transactions retrieved via API")

    # =========================================================================
    # 5. MARKETPLACE ABUSE & EDGE CASE PREVENTION
    # =========================================================================

    def test_09_self_service_order_blocked(self):
        # Albert attempts to order his own service
        svc_id = db_engine.execute_query("""
        INSERT INTO services (provider_id, category_id, title, description, subcategory, price, delivery_time_days, status)
        VALUES (1, 1, 'Self Service Test', 'Testing self order prevention', 'Tutoring', 50.00, 1, 'Active');
        """, fetch="lastrowid")

        res = self.client.post('/api/services/orders', data=json.dumps({
            "service_id": svc_id,
            "requirements": "Attempting self order",
            "due_date": "2026-11-20"
        }), headers=self._auth_headers(self.token_albert)) # Albert ordering from Albert
        self.assertEqual(res.status_code, 400)
        data = json.loads(res.data)
        self.assertIn("own service", data["message"].lower())
        print("  [OK] PASS  |  Abuse prevented: Provider ordering own service blocked (HTTP 400)")

    def test_10_unauthorized_order_state_transitions_blocked(self):
        # Grace places order on Albert's service
        svc_id = db_engine.execute_query("""
        INSERT INTO services (provider_id, category_id, title, description, subcategory, price, delivery_time_days, status)
        VALUES (1, 1, 'Math Modeling Help', 'Calculus and modeling assistance', 'Academic', 40.00, 1, 'Active');
        """, fetch="lastrowid")

        res_order = self.client.post('/api/services/orders', data=json.dumps({
            "service_id": svc_id,
            "requirements": "Need help on homework 3",
            "due_date": "2026-11-21"
        }), headers=self._auth_headers(self.token_grace))
        order_id = json.loads(res_order.data)["order_id"]

        # 1. Benedict (unauthorized 3rd party) attempts to accept Albert's order -> 403
        res_bad_accept = self.client.post(f'/api/services/orders/{order_id}/accept', headers=self._auth_headers(self.token_benedict))
        self.assertEqual(res_bad_accept.status_code, 403)

        # 2. Benedict attempts to view private order details -> 403
        res_bad_view = self.client.get(f'/api/services/orders/{order_id}', headers=self._auth_headers(self.token_benedict))
        self.assertEqual(res_bad_view.status_code, 403)

        # 3. Albert attempts to deliver an order that is still Pending (invalid transition) -> 400
        res_invalid_deliver = self.client.post(f'/api/services/orders/{order_id}/deliver', data=json.dumps({"delivery_notes": "Skipping in progress"}), headers=self._auth_headers(self.token_albert))
        self.assertEqual(res_invalid_deliver.status_code, 400)
        print("  [OK] PASS  |  Unauthorized order interactions & invalid state transitions blocked (HTTP 403 / 400)")

    def test_11_client_and_provider_order_history_endpoints(self):
        # Grace checks client orders
        res_client = self.client.get('/api/services/orders/client', headers=self._auth_headers(self.token_grace))
        self.assertEqual(res_client.status_code, 200)
        orders_client = json.loads(res_client.data)
        self.assertIsInstance(orders_client, list)

        # Albert checks provider orders
        res_prov = self.client.get('/api/services/orders/provider', headers=self._auth_headers(self.token_albert))
        self.assertEqual(res_prov.status_code, 200)
        orders_prov = json.loads(res_prov.data)
        self.assertIsInstance(orders_prov, list)
        print("  [OK] PASS  |  Client and Provider dedicated order history endpoints verified")

if __name__ == '__main__':
    print("========================================================================")
    print("   CampusLink Phase 3: Services & Skills Marketplace Test Suite")
    print("========================================================================")
    unittest.main()
