"""
tests/test_stage5_2_background_tasks.py
---------------------------------------
Focused Unit & Integration Test Suite for Phase 5 - Stage 5.2:
Asynchronous Background Task Architecture (Celery, Redis Queue & Beat Schedules).

Validates:
1. Celery app configuration, JSON serialization, UTC timezone, and Beat crontab schedules.
2. Asynchronous MoMo deposit webhook task execution & double-entry ledger settlement.
3. Database-level idempotency protection preventing duplicate crediting on Celery retries.
4. Asynchronous MoMo payout confirmation & compensating reversal tasks.
5. Periodic financial reconciliation background task execution.
6. Daily 00:00 UTC overdue rental sweeping and notification generation.
7. Asynchronous notification dispatch task.
8. End-to-end Flask webhook HTTP endpoint integration via task pipeline.
"""
import unittest
import time
import json
import os
import sys
from decimal import Decimal
from datetime import datetime, timedelta, date

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import db_engine
from database import db_seeder
from app import app
from core.config import PlatformConfig
from core.celery_app import celery_app
from core.wallet_service import FinancialService
from core.momo_adapter import MockMoMoAdapter
from tasks.webhook_tasks import process_momo_deposit_webhook_task, process_momo_payout_webhook_task
from tasks.reconciliation_tasks import run_periodic_reconciliation_task
from tasks.escrow_tasks import sweep_overdue_rentals_task
from tasks.notification_tasks import dispatch_notification_task

class Stage52BackgroundTasksTestSuite(unittest.TestCase):

    def setUp(self):
        app.testing = True
        self.client = app.test_client()
        # Seed fresh database for test isolation
        db_seeder.seed_database()

    # -------------------------------------------------------------------------
    # 1. CELERY APP CONFIGURATION & BEAT SCHEDULES
    # -------------------------------------------------------------------------

    def test_01_celery_configuration_and_beat_schedule(self):
        conf = celery_app.conf
        self.assertEqual(conf.task_serializer, "json")
        self.assertEqual(conf.result_serializer, "json")
        self.assertEqual(conf.timezone, "UTC")
        self.assertTrue(conf.enable_utc)
        self.assertTrue(conf.task_acks_late)
        self.assertTrue(conf.task_reject_on_worker_lost)
        
        # Verify Beat crontab schedule definitions
        beat_sched = conf.beat_schedule
        self.assertIn("hourly-financial-reconciliation", beat_sched)
        self.assertIn("daily-overdue-rental-sweeper", beat_sched)
        
        daily_job = beat_sched["daily-overdue-rental-sweeper"]
        self.assertEqual(daily_job["task"], "tasks.escrow_tasks.sweep_overdue_rentals_task")
        
        hourly_job = beat_sched["hourly-financial-reconciliation"]
        self.assertEqual(hourly_job["task"], "tasks.reconciliation_tasks.run_periodic_reconciliation_task")
        print("  [OK] PASS (01) | Celery app configuration, JSON serialization, and Beat crontabs verified")

    # -------------------------------------------------------------------------
    # 2. ASYNC DEPOSIT WEBHOOK TASK & DOUBLE-ENTRY LEDGER SETTLEMENT
    # -------------------------------------------------------------------------

    def test_02_async_deposit_webhook_task_execution(self):
        user_id = 1
        amount = Decimal("85.00")
        ref = f"TASK_DEP_{int(time.time()*1000)}"
        gw_tx_id = f"GW_{ref}"
        
        # Initial wallet balance
        w_before = FinancialService.get_wallet_summary(user_id)
        bal_before = Decimal(str(w_before["available_balance"]))
        
        # Dispatch Celery async task
        async_result = process_momo_deposit_webhook_task.delay(
            reference=ref,
            user_id=user_id,
            amount_str=str(amount),
            gateway_tx_id=gw_tx_id
        )
        res = async_result.result
        self.assertTrue(res["success"], f"Task execution failed: {res}")
        
        # Verify updated wallet balance
        w_after = FinancialService.get_wallet_summary(user_id)
        bal_after = Decimal(str(w_after["available_balance"]))
        self.assertEqual(bal_after, bal_before + amount)
        
        # Verify double-entry ledger parity: Clearing Wallet 8 (DEBIT) = Student Wallet 1 (CREDIT)
        clearing_tx = db_engine.execute_query(
            "SELECT * FROM wallet_transactions WHERE idempotency_key = ?;",
            (f"MOMO_DEP_{ref}_SYS_DEBIT",),
            fetchone=True
        )
        student_tx = db_engine.execute_query(
            "SELECT * FROM wallet_transactions WHERE idempotency_key = ?;",
            (f"MOMO_DEP_{ref}_CREDIT",),
            fetchone=True
        )
        self.assertIsNotNone(clearing_tx)
        self.assertEqual(clearing_tx["user_id"], 8)
        self.assertEqual(clearing_tx["entry_type"], "DEBIT")
        self.assertEqual(Decimal(str(clearing_tx["amount"])), amount)
        
        self.assertIsNotNone(student_tx)
        self.assertEqual(student_tx["user_id"], 1)
        self.assertEqual(student_tx["entry_type"], "CREDIT")
        self.assertEqual(Decimal(str(student_tx["amount"])), amount)
        print("  [OK] PASS (02) | Async deposit webhook task settled balanced double-entry ledger")

    # -------------------------------------------------------------------------
    # 3. DATABASE-LEVEL IDEMPOTENCY & DUPLICATE TASK RETRY SAFETY
    # -------------------------------------------------------------------------

    def test_03_async_deposit_webhook_task_idempotency_protection(self):
        user_id = 2
        amount = Decimal("150.00")
        ref = f"TASK_DEP_IDEM_{int(time.time()*1000)}"
        gw_tx_id = f"GW_{ref}"
        
        # 1st Execution
        res1 = process_momo_deposit_webhook_task.delay(
            reference=ref,
            user_id=user_id,
            amount_str=str(amount),
            gateway_tx_id=gw_tx_id
        ).result
        self.assertTrue(res1["success"])
        
        w_mid = FinancialService.get_wallet_summary(user_id)
        bal_mid = Decimal(str(w_mid["available_balance"]))
        
        # 2nd Execution (Simulating Celery Task Retry or Duplicate Webhook)
        res2 = process_momo_deposit_webhook_task.delay(
            reference=ref,
            user_id=user_id,
            amount_str=str(amount),
            gateway_tx_id=gw_tx_id
        ).result
        self.assertTrue(res2["success"])
        self.assertIn("already settled", res2["message"].lower())
        
        # Confirm balance remained strictly unchanged
        w_final = FinancialService.get_wallet_summary(user_id)
        self.assertEqual(Decimal(str(w_final["available_balance"])), bal_mid, "Duplicate task execution must not credit wallet twice")
        print("  [OK] PASS (03) | Database-level idempotency protected ledger against duplicate task retries")

    # -------------------------------------------------------------------------
    # 4. ASYNC PAYOUT CONFIRMATION & COMPENSATING REVERSAL TASKS
    # -------------------------------------------------------------------------

    def test_04_async_payout_webhook_task_execution(self):
        user_id = 1
        deposit_amt = Decimal("100.00")
        payout_amt = Decimal("40.00")
        dep_ref = f"DEP_PRE_{int(time.time()*1000)}"
        FinancialService.settle_momo_deposit(dep_ref, user_id, deposit_amt, "GW_PRE")
        
        # Request withdrawal (moves funds to pending)
        ok, msg, p_data = FinancialService.request_momo_withdrawal(user_id, payout_amt, "MTN", "0241112233")
        self.assertTrue(ok)
        payout_ref = p_data["reference"]
        
        w_pend = FinancialService.get_wallet_summary(user_id)
        self.assertEqual(Decimal(str(w_pend["pending_balance"])), payout_amt)
        
        # Scenario A: Async payout success task
        res_succ = process_momo_payout_webhook_task.delay(
            reference=payout_ref,
            success=True,
            notes="Gateway settled"
        ).result
        self.assertTrue(res_succ["success"])
        
        w_done = FinancialService.get_wallet_summary(user_id)
        self.assertEqual(Decimal(str(w_done["pending_balance"])), Decimal("0.00"))
        
        # Scenario B: Failed withdrawal compensating reversal
        ok_fail, _, p_fail_data = FinancialService.request_momo_withdrawal(user_id, Decimal("30.00"), "MTN", "0241112233")
        self.assertTrue(ok_fail)
        payout_fail_ref = p_fail_data["reference"]
        
        avail_pre_rev = Decimal(str(FinancialService.get_wallet_summary(user_id)["available_balance"]))
        
        res_fail = process_momo_payout_webhook_task.delay(
            reference=payout_fail_ref,
            success=False,
            notes="Insufficient destination float"
        ).result
        self.assertTrue(res_fail["success"])
        
        w_rev = FinancialService.get_wallet_summary(user_id)
        self.assertEqual(Decimal(str(w_rev["pending_balance"])), Decimal("0.00"))
        self.assertEqual(Decimal(str(w_rev["available_balance"])), avail_pre_rev + Decimal("30.00"))
        print("  [OK] PASS (04) | Async payout task verified for both completion and compensating reversal")

    # -------------------------------------------------------------------------
    # 5. PERIODIC FINANCIAL RECONCILIATION TASK
    # -------------------------------------------------------------------------

    def test_05_reconciliation_task_execution(self):
        res = run_periodic_reconciliation_task.delay().result
        self.assertTrue(res["success"])
        self.assertIn("matched_count", res)
        self.assertIn("discrepancy_count", res)
        self.assertGreaterEqual(res["matched_count"], 0)
        print(f"  [OK] PASS (05) | Scheduled reconciliation task executed successfully (Matched: {res['matched_count']})")

    # -------------------------------------------------------------------------
    # 6. DAILY OVERDUE RENTAL SWEEPER TASK
    # -------------------------------------------------------------------------

    def test_06_overdue_rental_sweeper_task(self):
        # Insert a simulated overdue rental transaction in the past
        past_end_date = (date.today() - timedelta(days=2)).strftime("%Y-%m-%d")
        past_start_date = (date.today() - timedelta(days=5)).strftime("%Y-%m-%d")
        
        # Create request first to satisfy foreign key
        req_id = db_engine.execute_query("""
            INSERT INTO rental_requests (listing_id, borrower_id, rent_start_date, rent_end_date, rental_purpose, status)
            VALUES (?, ?, ?, ?, 'Field Trip', 'Approved');
        """, (1, 2, past_start_date, past_end_date), fetch="lastrowid")
        
        db_engine.execute_query("""
            INSERT INTO rental_transactions (
                request_id, listing_id, borrower_id,
                rent_start_date, rent_end_date, total_days, gross_amount,
                commission_amount, owner_earnings, deposit_held, payment_status, rental_status
            ) VALUES (?, ?, ?, ?, ?, 3, 30.00, 3.00, 27.00, 50.00, 'Paid', 'Active');
        """, (req_id, 1, 2, past_start_date, past_end_date))
        
        res = sweep_overdue_rentals_task.delay().result
        self.assertTrue(res["success"])
        self.assertGreaterEqual(res["overdue_rentals_found"], 1)
        self.assertGreaterEqual(res["notifications_dispatched"], 2)
        print(f"  [OK] PASS (06) | Daily 00:00 UTC overdue rental sweeper detected {res['overdue_rentals_found']} rentals and notified users")

    # -------------------------------------------------------------------------
    # 7. ASYNC NOTIFICATION DISPATCH TASK
    # -------------------------------------------------------------------------

    def test_07_notification_task_dispatch(self):
        res = dispatch_notification_task.delay(
            user_id=1,
            title="Async Test Notification",
            message="Your listing received a rental booking request.",
            notif_type="info"
        ).result
        self.assertTrue(res["success"])
        self.assertIsNotNone(res["notification_id"])
        
        # Verify notification in database
        notifs = db_engine.execute_query(
            "SELECT * FROM notifications WHERE notification_id = ?;",
            (res["notification_id"],),
            fetchone=True
        )
        self.assertIsNotNone(notifs)
        self.assertEqual(notifs["user_id"], 1)
        self.assertEqual(notifs["title"], "Async Test Notification")
        print("  [OK] PASS (07) | Non-blocking async notification dispatch task verified")

    # -------------------------------------------------------------------------
    # 8. END-TO-END WEBHOOK HTTP PIPELINE WITH SIGNATURE VALIDATION
    # -------------------------------------------------------------------------

    def test_08_e2e_webhook_endpoint_via_task_pipeline(self):
        gateway = MockMoMoAdapter()
        user_id = 3
        amount = Decimal("60.00")
        ref = f"E2E_WEBHOOK_TASK_{int(time.time()*1000)}"
        
        # Track on mock adapter
        gateway.transactions[ref] = {
            "user_id": user_id,
            "amount": amount,
            "reference": ref,
            "gateway_tx_id": f"GW_{ref}",
            "status": "Successful",
            "type": "deposit"
        }
        
        payload_meta = gateway.generate_webhook_payload(reference=ref, amount_override=amount)
        payload_bytes = payload_meta["raw_bytes"]
        sig = payload_meta["signature"]
        
        response = self.client.post(
            '/api/payments/momo/webhook',
            data=payload_bytes,
            headers={
                "Content-Type": "application/json",
                "X-CampusLink-Signature": sig
            }
        )
        self.assertIn(response.status_code, (200, 202))
        data = json.loads(response.data)
        self.assertTrue(data["success"])
        
        # Confirm user wallet was credited
        w = FinancialService.get_wallet_summary(user_id)
        self.assertGreaterEqual(Decimal(str(w["available_balance"])), amount)
        print("  [OK] PASS (08) | HTTP Webhook endpoint successfully settled via background task pipeline")

if __name__ == '__main__':
    print("========================================================================")
    print("   CampusLink Phase 5 Stage 5.2: Background Tasks & Celery Test Suite")
    print("========================================================================")
    unittest.main()
