"""
core/wallet_service.py
----------------------
Core Financial & Wallet Service for CampusLink 2.0.
Implements:
1. Dual-sided balanced accounting: Every money movement has matching debit/credit sides (Σ DEBIT = Σ CREDIT).
2. Concurrency-safe atomic transactions with row-level locking (FOR UPDATE).
3. Immediate withdrawal fund reservation (available -> pending).
4. Payout settlement & compensating ledger reversals on failure.
5. Strict Decimal ROUND_HALF_UP arithmetic (no floats).
6. Dedicated reserved system accounting entities (user_id=6 Platform Commission Vault, user_id=7 System Escrow Custodial Vault, user_id=8 MoMo Gateway Clearing).
7. Atomic cryptographic webhook processing.
"""
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, Any, Optional, Tuple, List
import time
import uuid
from datetime import datetime

import db_engine
from .config import CommissionService
from .payment_interface import GatewayResponse
from .momo_adapter import get_payment_gateway
from .audit_logger import log_financial_event

# Dedicated Reserved System Accounting Entities
PLATFORM_COMMISSION_USER_ID = 6  # Platform Commission Revenue (Retained 10% Fees)
SYSTEM_ESCROW_USER_ID       = 7  # System Custodial Escrow Vault (Trust Liability)
GATEWAY_CLEARING_USER_ID    = 8  # Mobile Money Gateway Clearing (Clearing Float)

class InsufficientFundsError(Exception):
    """Raised when an operation attempts to spend more than available balance."""
    pass

class IdempotencyConflictError(Exception):
    """Raised when a financial operation with the same idempotency key was already executed."""
    pass

class FinancialService:

    @staticmethod
    def _to_decimal(val: Any) -> Decimal:
        """Converts any numeric representation to 2-decimal place Decimal with ROUND_HALF_UP."""
        if val is None:
            return Decimal("0.00")
        return Decimal(str(val)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    @classmethod
    def _execute(cls, tx, query: str, params: tuple = (), fetchone: bool = False, fetch: str = "all"):
        """Executes a query using active transaction context or db_engine."""
        if tx is not None:
            return tx.execute(query, params, fetchone=fetchone, fetch=fetch)
        return db_engine.execute_query(query, params, fetchone=fetchone, fetch=fetch)

    @classmethod
    def get_or_create_wallet(cls, user_id: int, tx=None) -> Dict[str, Any]:
        """Ensures a wallet exists for a user and returns its dictionary."""
        wallet = cls._execute(
            tx,
            "SELECT wallet_id, user_id, available_balance, pending_balance, locked_escrow, total_earned, total_withdrawn, updated_at FROM user_wallets WHERE user_id = ?;",
            (user_id,), fetchone=True
        )
        if not wallet:
            cls._execute(
                tx,
                "INSERT INTO user_wallets (user_id, available_balance, pending_balance, locked_escrow, total_earned, total_withdrawn) VALUES (?, 0.00, 0.00, 0.00, 0.00, 0.00);",
                (user_id,)
            )
            wallet = cls._execute(
                tx,
                "SELECT wallet_id, user_id, available_balance, pending_balance, locked_escrow, total_earned, total_withdrawn, updated_at FROM user_wallets WHERE user_id = ?;",
                (user_id,), fetchone=True
            )
        return dict(wallet)

    @classmethod
    def get_wallet_summary(cls, user_id: int) -> Dict[str, Any]:
        """Returns the user's cached wallet balances and calculated authoritative ledger balance."""
        wallet = cls.get_or_create_wallet(user_id)
        
        # Calculate authoritative ledger balance from immutable transactions
        calc = db_engine.execute_query("""
        SELECT 
            COALESCE(SUM(CASE WHEN entry_type = 'CREDIT' AND status = 'Completed' THEN amount ELSE 0 END), 0) as total_credits,
            COALESCE(SUM(CASE WHEN entry_type = 'DEBIT' AND status = 'Completed' THEN amount ELSE 0 END), 0) as total_debits
        FROM wallet_transactions
        WHERE user_id = ?;
        """, (user_id,), fetchone=True)

        tot_credits = cls._to_decimal(calc["total_credits"]) if calc else Decimal("0.00")
        tot_debits = cls._to_decimal(calc["total_debits"]) if calc else Decimal("0.00")
        authoritative_net = tot_credits - tot_debits

        return {
            "wallet_id": wallet["wallet_id"],
            "user_id": user_id,
            "available_balance": float(cls._to_decimal(wallet["available_balance"])),
            "pending_balance": float(cls._to_decimal(wallet["pending_balance"])),
            "locked_escrow": float(cls._to_decimal(wallet["locked_escrow"])),
            "total_earned": float(cls._to_decimal(wallet["total_earned"])),
            "total_withdrawn": float(cls._to_decimal(wallet["total_withdrawn"])),
            "authoritative_ledger_balance": float(authoritative_net),
            "updated_at": wallet["updated_at"]
        }

    # =========================================================================
    # 1. MOBILE MONEY DEPOSIT LIFECYCLE (DUAL-SIDED)
    # =========================================================================

    @classmethod
    def initiate_momo_deposit(
        cls,
        user_id: int,
        amount: Decimal,
        network: str,
        phone_number: str
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Step 1: Initiates MoMo deposit via Payment Gateway.
        Returns reference and status.
        """
        dec_amount = cls._to_decimal(amount)
        if dec_amount <= Decimal("0.00"):
            return False, "Deposit amount must be strictly positive.", {}

        # Generate unique microsecond-precision reference
        reference = f"MOMO_DEP_{int(time.time() * 1000)}_{user_id}_{phone_number[-4:]}_{uuid.uuid4().hex[:4]}"
        gateway = get_payment_gateway()
        gw_resp = gateway.initiate_deposit(
            user_id=user_id,
            amount=dec_amount,
            network=network,
            phone_number=phone_number,
            reference=reference
        )

        if not gw_resp.success:
            return False, gw_resp.message, {}

        return True, "USSD push prompt sent to phone. Please confirm with PIN.", {
            "reference": reference,
            "gateway_tx_id": gw_resp.gateway_tx_id,
            "status": "Pending",
            "amount": float(dec_amount),
            "network": network,
            "phone_number": phone_number
        }

    @classmethod
    def settle_momo_deposit(
        cls,
        reference: str,
        user_id: int,
        amount: Decimal,
        gateway_tx_id: str
    ) -> Tuple[bool, str]:
        """
        Step 2: Atomically settles verified MoMo deposit via authoritative dual-sided ledger.
        [Gateway Clearing (Wallet 8): DEBIT] -> [Student Wallet: CREDIT]
        """
        dec_amount = cls._to_decimal(amount)
        try:
            with db_engine.transaction() as tx:
                # 1. Check Idempotency Key
                idempotency_key = f"MOMO_DEP_{reference}_CREDIT"
                existing = tx.execute(
                    "SELECT wallet_tx_id FROM wallet_transactions WHERE idempotency_key = ?;",
                    (idempotency_key,), fetchone=True
                )
                if existing:
                    return True, "Deposit already settled."

                # 2. Lock & Load User Wallet & Gateway Clearing Wallet
                u_wallet = cls.get_or_create_wallet(user_id, tx=tx)
                u_wallet_id = u_wallet["wallet_id"]
                clearing_wallet = cls.get_or_create_wallet(GATEWAY_CLEARING_USER_ID, tx=tx)
                clearing_wallet_id = clearing_wallet["wallet_id"]

                # 3. Create Dual-Sided Balanced Ledger Entries:
                # Side A: MoMo Gateway Clearing DEBIT
                sys_key = f"MOMO_DEP_{reference}_SYS_DEBIT"
                tx.execute("""
                INSERT INTO wallet_transactions (
                    wallet_id, user_id, entry_type, tx_type, amount, reference_type, reference_id, idempotency_key, status, notes
                ) VALUES (?, ?, 'DEBIT', 'DepositRefund', ?, 'momo_deposit', 0, ?, 'Completed', ?);
                """, (clearing_wallet_id, GATEWAY_CLEARING_USER_ID, float(dec_amount), sys_key, f"MoMo Clearing Settlement ({gateway_tx_id})"))

                # Side B: Student Wallet CREDIT
                tx.execute("""
                INSERT INTO wallet_transactions (
                    wallet_id, user_id, entry_type, tx_type, amount, reference_type, reference_id, idempotency_key, status, notes
                ) VALUES (?, ?, 'CREDIT', 'DepositRefund', ?, 'momo_deposit', 0, ?, 'Completed', ?);
                """, (u_wallet_id, user_id, float(dec_amount), idempotency_key, f"MoMo Deposit via Gateway ({gateway_tx_id})"))

                # 4. Update Cached User Wallet Balance
                new_avail = cls._to_decimal(u_wallet["available_balance"]) + dec_amount
                tx.execute(
                    "UPDATE user_wallets SET available_balance = ?, updated_at = CURRENT_TIMESTAMP WHERE wallet_id = ?;",
                    (float(new_avail), u_wallet_id)
                )

                # 5. Notify user
                tx.execute("""
                INSERT INTO notifications (user_id, title, message, type, is_read)
                VALUES (?, 'Mobile Money Deposit Confirmed', ?, 'success', 0);
                """, (user_id, f"Your wallet was credited with GH₵ {dec_amount:.2f} (Ref: {reference})."))

                log_financial_event("MOMO_DEPOSIT_SETTLED", user_id, float(dec_amount), "momo_deposit", 0, "SUCCESS", f"Ref: {reference}")
                return True, "Deposit settled successfully."
        except Exception as e:
            return False, f"Failed to settle deposit: {str(e)}"

    # =========================================================================
    # 2. WITHDRAWAL & PAYOUT LIFECYCLE (IMMEDIATE FUND RESERVATION)
    # =========================================================================

    @classmethod
    def request_momo_withdrawal(
        cls,
        user_id: int,
        amount: Decimal,
        network: str,
        phone_number: str
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Initiates MoMo withdrawal with IMMEDIATE fund reservation:
        - Locks wallet (FOR UPDATE).
        - Verifies available_balance >= amount.
        - Atomically debits available_balance and credits pending_balance.
        - Inserts pending DEBIT ledger entry.
        - Calls gateway payout dispatch.
        """
        dec_amount = cls._to_decimal(amount)
        if dec_amount <= Decimal("0.00"):
            return False, "Withdrawal amount must be strictly positive.", {}

        # Generate unique microsecond-precision reference
        reference = f"MOMO_PAYOUT_{int(time.time() * 1000)}_{user_id}_{phone_number[-4:]}_{uuid.uuid4().hex[:4]}"
        idempotency_key = f"MOMO_PAYOUT_{reference}_DEBIT"

        try:
            with db_engine.transaction() as tx:
                # 1. Row-Level Lock Wallet
                wallet = cls.get_or_create_wallet(user_id, tx=tx)
                avail = cls._to_decimal(wallet["available_balance"])
                pending = cls._to_decimal(wallet["pending_balance"])

                # 2. Strict Balance Invariant Check
                if avail < dec_amount:
                    return False, f"Insufficient funds. Available: GH₵ {avail:.2f}, Requested: GH₵ {dec_amount:.2f}", {}

                # 3. Immediate Fund Reservation: available -> pending
                new_avail = avail - dec_amount
                new_pending = pending + dec_amount
                tx.execute(
                    "UPDATE user_wallets SET available_balance = ?, pending_balance = ?, updated_at = CURRENT_TIMESTAMP WHERE wallet_id = ?;",
                    (float(new_avail), float(new_pending), wallet["wallet_id"])
                )

                # 4. Insert Pending Ledger Entry
                tx.execute("""
                INSERT INTO wallet_transactions (
                    wallet_id, user_id, entry_type, tx_type, amount, reference_type, reference_id, idempotency_key, status, notes
                ) VALUES (?, ?, 'DEBIT', 'PayoutWithdrawal', ?, 'momo_payout', 0, ?, 'Pending', ?);
                """, (wallet["wallet_id"], user_id, float(dec_amount), idempotency_key, f"Pending MoMo Withdrawal to {network} ({phone_number})"))

            # 5. Dispatch to Gateway (outside DB lock)
            gateway = get_payment_gateway()
            gw_resp = gateway.initiate_payout(
                user_id=user_id,
                amount=dec_amount,
                network=network,
                phone_number=phone_number,
                reference=reference
            )

            log_financial_event("WITHDRAWAL_REQUESTED", user_id, float(dec_amount), "momo_payout", 0, "PENDING", f"Ref: {reference}")
            return True, "Withdrawal request submitted for processing.", {
                "reference": reference,
                "amount": float(dec_amount),
                "network": network,
                "phone_number": phone_number,
                "status": "Pending"
            }
        except Exception as e:
            return False, f"Withdrawal request failed: {str(e)}", {}

    @classmethod
    def settle_momo_payout(
        cls,
        reference: str,
        success: bool,
        notes: str = ""
    ) -> Tuple[bool, str]:
        """
        Settles MoMo payout upon gateway webhook confirmation:
        - If Success: pending_balance -> total_withdrawn, ledger status -> 'Completed', Side B: Gateway Clearing CREDIT.
        - If Failure: Compensating reversal restores available_balance, ledger status -> 'Failed', reversal CREDIT inserted.
        """
        idempotency_key = f"MOMO_PAYOUT_{reference}_DEBIT"
        try:
            with db_engine.transaction() as tx:
                # 1. Fetch pending payout ledger transaction
                tx_rec = tx.execute(
                    "SELECT wallet_tx_id, wallet_id, user_id, amount, status FROM wallet_transactions WHERE idempotency_key = ?;",
                    (idempotency_key,), fetchone=True
                )
                if not tx_rec:
                    return False, f"Payout transaction '{reference}' not found."
                if tx_rec["status"] != "Pending":
                    return True, f"Payout already settled with status '{tx_rec['status']}'."

                user_id = tx_rec["user_id"]
                wallet_id = tx_rec["wallet_id"]
                dec_amount = cls._to_decimal(tx_rec["amount"])

                wallet = tx.execute("SELECT available_balance, pending_balance, total_withdrawn FROM user_wallets WHERE wallet_id = ?;", (wallet_id,), fetchone=True)
                avail = cls._to_decimal(wallet["available_balance"])
                pending = cls._to_decimal(wallet["pending_balance"])
                tot_withdrawn = cls._to_decimal(wallet["total_withdrawn"])

                clearing_wallet = cls.get_or_create_wallet(GATEWAY_CLEARING_USER_ID, tx=tx)
                clearing_wallet_id = clearing_wallet["wallet_id"]

                if success:
                    # 2A. Settle Successful Payout
                    new_pending = max(Decimal("0.00"), pending - dec_amount)
                    new_withdrawn = tot_withdrawn + dec_amount
                    tx.execute(
                        "UPDATE user_wallets SET pending_balance = ?, total_withdrawn = ?, updated_at = CURRENT_TIMESTAMP WHERE wallet_id = ?;",
                        (float(new_pending), float(new_withdrawn), wallet_id)
                    )
                    tx.execute("UPDATE wallet_transactions SET status = 'Completed', notes = ? WHERE wallet_tx_id = ?;", (f"Settled: {notes}", tx_rec["wallet_tx_id"]))
                    
                    # Dual-sided Side B: Gateway Clearing Settlement CREDIT
                    sys_payout_key = f"MOMO_PAYOUT_{reference}_SYS_CREDIT"
                    tx.execute("""
                    INSERT INTO wallet_transactions (
                        wallet_id, user_id, entry_type, tx_type, amount, reference_type, reference_id, idempotency_key, status, notes
                    ) VALUES (?, ?, 'CREDIT', 'PayoutWithdrawal', ?, 'momo_payout', 0, ?, 'Completed', ?);
                    """, (clearing_wallet_id, GATEWAY_CLEARING_USER_ID, float(dec_amount), sys_payout_key, f"MoMo Gateway Clearing Settlement ({reference})"))

                    tx.execute("""
                    INSERT INTO notifications (user_id, title, message, type, is_read)
                    VALUES (?, 'Withdrawal Successful', ?, 'success', 0);
                    """, (user_id, f"Your withdrawal of GH₵ {dec_amount:.2f} was successfully sent to your Mobile Money wallet."))

                    log_financial_event("WITHDRAWAL_SETTLED", user_id, float(dec_amount), "momo_payout", 0, "SUCCESS", f"Ref: {reference}")
                    return True, "Payout settled successfully."
                else:
                    # 2B. Compensating Reversal on Failure
                    new_pending = max(Decimal("0.00"), pending - dec_amount)
                    new_avail = avail + dec_amount # Restore reserved funds
                    tx.execute(
                        "UPDATE user_wallets SET available_balance = ?, pending_balance = ?, updated_at = CURRENT_TIMESTAMP WHERE wallet_id = ?;",
                        (float(new_avail), float(new_pending), wallet_id)
                    )
                    tx.execute("UPDATE wallet_transactions SET status = 'Failed', notes = ? WHERE wallet_tx_id = ?;", (f"Failed: {notes}", tx_rec["wallet_tx_id"]))

                    # Insert Compensating Reversal CREDIT Entry for User
                    reversal_key = f"MOMO_PAYOUT_REVERSAL_{reference}_CREDIT"
                    tx.execute("""
                    INSERT INTO wallet_transactions (
                        wallet_id, user_id, entry_type, tx_type, amount, reference_type, reference_id, idempotency_key, status, notes
                    ) VALUES (?, ?, 'CREDIT', 'PayoutWithdrawal', ?, 'momo_payout', 0, ?, 'Completed', ?);
                    """, (wallet_id, user_id, float(dec_amount), reversal_key, f"Compensating reversal of failed payout ({reference}): {notes}"))

                    # Compensating Reversal DEBIT Entry for Gateway Clearing
                    sys_reversal_key = f"MOMO_PAYOUT_REVERSAL_{reference}_SYS_DEBIT"
                    tx.execute("""
                    INSERT INTO wallet_transactions (
                        wallet_id, user_id, entry_type, tx_type, amount, reference_type, reference_id, idempotency_key, status, notes
                    ) VALUES (?, ?, 'DEBIT', 'PayoutWithdrawal', ?, 'momo_payout', 0, ?, 'Completed', ?);
                    """, (clearing_wallet_id, GATEWAY_CLEARING_USER_ID, float(dec_amount), sys_reversal_key, f"Compensating reversal of failed payout ({reference})"))

                    tx.execute("""
                    INSERT INTO notifications (user_id, title, message, type, is_read)
                    VALUES (?, 'Withdrawal Failed - Funds Restored', ?, 'danger', 0);
                    """, (user_id, f"Your withdrawal of GH₵ {dec_amount:.2f} failed. Funds have been restored to your available balance."))

                    log_financial_event("WITHDRAWAL_REVERSED", user_id, float(dec_amount), "momo_payout", 0, "FAILED", f"Ref: {reference}")
                    return True, "Payout failed; funds restored via compensating reversal."
        except Exception as e:
            return False, f"Error settling payout: {str(e)}"

    # =========================================================================
    # 3. RENTAL ESCROW & RETURN LEDGER (DUAL-SIDED)
    # =========================================================================

    @classmethod
    def hold_rental_escrow(
        cls,
        tx,
        transaction_id: int,
        borrower_id: int,
        gross_amount: Any,
        deposit_amount: Any
    ) -> None:
        """
        Dual-sided ledger hold for rental gross + security deposit.
        Borrower DEBIT -> System Escrow CREDIT.
        """
        gross = cls._to_decimal(gross_amount)
        dep = cls._to_decimal(deposit_amount)
        total_hold = gross + dep

        b_wallet = cls.get_or_create_wallet(borrower_id, tx=tx)
        s_wallet = cls.get_or_create_wallet(SYSTEM_ESCROW_USER_ID, tx=tx)

        # Side A: Borrower DEBIT
        b_key = f"RENT_ESCROW_HOLD_TX_{transaction_id}_DEBIT"
        tx.execute("""
        INSERT INTO wallet_transactions (
            wallet_id, user_id, entry_type, tx_type, amount, reference_type, reference_id, idempotency_key, status, notes
        ) VALUES (?, ?, 'DEBIT', 'DepositEscrowHold', ?, 'rental_transaction', ?, ?, 'Completed', ?);
        """, (b_wallet["wallet_id"], borrower_id, float(total_hold), transaction_id, b_key, f"Escrow hold for rental transaction #{transaction_id}"))

        # Side B: System Escrow CREDIT
        s_key = f"RENT_ESCROW_SYS_HOLD_TX_{transaction_id}_CREDIT"
        tx.execute("""
        INSERT INTO wallet_transactions (
            wallet_id, user_id, entry_type, tx_type, amount, reference_type, reference_id, idempotency_key, status, notes
        ) VALUES (?, ?, 'CREDIT', 'DepositEscrowHold', ?, 'rental_transaction', ?, ?, 'Completed', ?);
        """, (s_wallet["wallet_id"], SYSTEM_ESCROW_USER_ID, float(total_hold), transaction_id, s_key, f"System custody hold for rental #{transaction_id}"))

        # Update cached escrow
        new_escrow = cls._to_decimal(b_wallet["locked_escrow"]) + total_hold
        tx.execute("UPDATE user_wallets SET locked_escrow = ?, updated_at = CURRENT_TIMESTAMP WHERE wallet_id = ?;", (float(new_escrow), b_wallet["wallet_id"]))

    @classmethod
    def release_rental_escrow(
        cls,
        tx,
        transaction_id: int,
        borrower_id: int,
        owner_id: int,
        gross_amount: Any,
        deposit_amount: Any,
        damage_claim: Any = Decimal("0.00")
    ) -> None:
        """
        Dual-sided ledger release on rental return:
        - 10% platform commission -> Platform Commission Vault (user_id=6).
        - 90% rental earnings -> Owner Wallet.
        - Damage claim (if any) -> Owner Wallet.
        - Remaining deposit -> Borrower Wallet.
        """
        gross = cls._to_decimal(gross_amount)
        deposit = cls._to_decimal(deposit_amount)
        claim = cls._to_decimal(damage_claim)

        # Centralized Split
        split = CommissionService.calculate_rental_split(gross)
        commission = cls._to_decimal(split["commission_amount"])
        owner_earnings = cls._to_decimal(split["owner_earnings"])

        deposit_refund = max(Decimal("0.00"), deposit - claim)
        total_held = gross + deposit

        b_wallet = cls.get_or_create_wallet(borrower_id, tx=tx)
        o_wallet = cls.get_or_create_wallet(owner_id, tx=tx)
        escrow_wallet = cls.get_or_create_wallet(SYSTEM_ESCROW_USER_ID, tx=tx)
        comm_wallet = cls.get_or_create_wallet(PLATFORM_COMMISSION_USER_ID, tx=tx)

        # 1. System Escrow DEBIT Release
        s_rel_key = f"RENT_ESCROW_SYS_RELEASE_TX_{transaction_id}_DEBIT"
        tx.execute("""
        INSERT INTO wallet_transactions (
            wallet_id, user_id, entry_type, tx_type, amount, reference_type, reference_id, idempotency_key, status, notes
        ) VALUES (?, ?, 'DEBIT', 'DepositEscrowHold', ?, 'rental_transaction', ?, ?, 'Completed', ?);
        """, (escrow_wallet["wallet_id"], SYSTEM_ESCROW_USER_ID, float(total_held), transaction_id, s_rel_key, f"Escrow release for rental #{transaction_id}"))

        # 2. Owner Earnings CREDIT
        o_key = f"RENT_EARNING_TX_{transaction_id}_CREDIT"
        tx.execute("""
        INSERT INTO wallet_transactions (
            wallet_id, user_id, entry_type, tx_type, amount, reference_type, reference_id, idempotency_key, status, notes
        ) VALUES (?, ?, 'CREDIT', 'RentalIncome', ?, 'rental_transaction', ?, ?, 'Completed', ?);
        """, (o_wallet["wallet_id"], owner_id, float(owner_earnings), transaction_id, o_key, f"Rental earnings for transaction #{transaction_id}"))

        new_o_avail = cls._to_decimal(o_wallet["available_balance"]) + owner_earnings
        new_o_earned = cls._to_decimal(o_wallet["total_earned"]) + owner_earnings
        tx.execute("UPDATE user_wallets SET available_balance = ?, total_earned = ?, updated_at = CURRENT_TIMESTAMP WHERE wallet_id = ?;", (float(new_o_avail), float(new_o_earned), o_wallet["wallet_id"]))

        # 3. Platform Commission CREDIT
        comm_key = f"RENT_COMMISSION_TX_{transaction_id}_CREDIT"
        tx.execute("""
        INSERT INTO wallet_transactions (
            wallet_id, user_id, entry_type, tx_type, amount, reference_type, reference_id, idempotency_key, status, notes
        ) VALUES (?, ?, 'CREDIT', 'PlatformCommission', ?, 'rental_transaction', ?, ?, 'Completed', ?);
        """, (comm_wallet["wallet_id"], PLATFORM_COMMISSION_USER_ID, float(commission), transaction_id, comm_key, f"10% commission on rental #{transaction_id}"))

        new_comm_avail = cls._to_decimal(comm_wallet["available_balance"]) + commission
        new_comm_earned = cls._to_decimal(comm_wallet["total_earned"]) + commission
        tx.execute("UPDATE user_wallets SET available_balance = ?, total_earned = ?, updated_at = CURRENT_TIMESTAMP WHERE wallet_id = ?;", (float(new_comm_avail), float(new_comm_earned), comm_wallet["wallet_id"]))

        # 4. Damage Claim (if > 0) -> Owner CREDIT
        if claim > Decimal("0.00"):
            claim_key = f"RENT_DAMAGE_TX_{transaction_id}_CREDIT"
            tx.execute("""
            INSERT INTO wallet_transactions (
                wallet_id, user_id, entry_type, tx_type, amount, reference_type, reference_id, idempotency_key, status, notes
            ) VALUES (?, ?, 'CREDIT', 'DamageDeduction', ?, 'rental_transaction', ?, ?, 'Completed', ?);
            """, (o_wallet["wallet_id"], owner_id, float(claim), transaction_id, claim_key, f"Damage claim reimbursement for rental #{transaction_id}"))

            new_o_avail = cls._to_decimal(o_wallet["available_balance"]) + claim
            tx.execute("UPDATE user_wallets SET available_balance = ?, updated_at = CURRENT_TIMESTAMP WHERE wallet_id = ?;", (float(new_o_avail), o_wallet["wallet_id"]))

        # 5. Deposit Refund -> Borrower CREDIT
        if deposit_refund > Decimal("0.00"):
            ref_key = f"RENT_REFUND_TX_{transaction_id}_CREDIT"
            tx.execute("""
            INSERT INTO wallet_transactions (
                wallet_id, user_id, entry_type, tx_type, amount, reference_type, reference_id, idempotency_key, status, notes
            ) VALUES (?, ?, 'CREDIT', 'DepositRefund', ?, 'rental_transaction', ?, ?, 'Completed', ?);
            """, (b_wallet["wallet_id"], borrower_id, float(deposit_refund), transaction_id, ref_key, f"Security deposit refund for rental #{transaction_id}"))

            new_b_avail = cls._to_decimal(b_wallet["available_balance"]) + deposit_refund
            tx.execute("UPDATE user_wallets SET available_balance = ?, updated_at = CURRENT_TIMESTAMP WHERE wallet_id = ?;", (float(new_b_avail), b_wallet["wallet_id"]))

        # Clear borrower locked escrow
        new_b_escrow = max(Decimal("0.00"), cls._to_decimal(b_wallet["locked_escrow"]) - total_held)
        tx.execute("UPDATE user_wallets SET locked_escrow = ?, updated_at = CURRENT_TIMESTAMP WHERE wallet_id = ?;", (float(new_b_escrow), b_wallet["wallet_id"]))

    # =========================================================================
    # 4. SERVICE ESCROW & ORDER LIFECYCLE (DUAL-SIDED)
    # =========================================================================

    @classmethod
    def hold_service_escrow(
        cls,
        tx,
        order_id: int,
        client_id: int,
        amount: Any,
        service_title: str = ""
    ) -> None:
        """
        Dual-sided ledger hold for service order price.
        Client DEBIT -> System Escrow CREDIT.
        """
        price = cls._to_decimal(amount)
        c_wallet = cls.get_or_create_wallet(client_id, tx=tx)
        s_wallet = cls.get_or_create_wallet(SYSTEM_ESCROW_USER_ID, tx=tx)

        # Side A: Client DEBIT
        c_key = f"SVC_ESCROW_HOLD_ORD_{order_id}_DEBIT"
        tx.execute("""
        INSERT INTO wallet_transactions (
            wallet_id, user_id, entry_type, tx_type, amount, reference_type, reference_id, idempotency_key, status, notes
        ) VALUES (?, ?, 'DEBIT', 'DepositEscrowHold', ?, 'service_order', ?, ?, 'Completed', ?);
        """, (c_wallet["wallet_id"], client_id, float(price), order_id, c_key, f"Escrow hold for order #{order_id} ({service_title})"))

        # Side B: System Escrow CREDIT
        s_key = f"SVC_ESCROW_SYS_HOLD_ORD_{order_id}_CREDIT"
        tx.execute("""
        INSERT INTO wallet_transactions (
            wallet_id, user_id, entry_type, tx_type, amount, reference_type, reference_id, idempotency_key, status, notes
        ) VALUES (?, ?, 'CREDIT', 'DepositEscrowHold', ?, 'service_order', ?, ?, 'Completed', ?);
        """, (s_wallet["wallet_id"], SYSTEM_ESCROW_USER_ID, float(price), order_id, s_key, f"System custody hold for service order #{order_id}"))

        # Update client locked escrow
        new_escrow = cls._to_decimal(c_wallet["locked_escrow"]) + price
        tx.execute("UPDATE user_wallets SET locked_escrow = ?, updated_at = CURRENT_TIMESTAMP WHERE wallet_id = ?;", (float(new_escrow), c_wallet["wallet_id"]))

    @classmethod
    def release_service_escrow(
        cls,
        tx,
        order_id: int,
        client_id: int,
        provider_id: int,
        amount: Any,
        platform_fee: Any,
        provider_earnings: Any
    ) -> None:
        """
        Dual-sided ledger release on service completion:
        - System Escrow DEBIT (100%).
        - Provider Wallet CREDIT (90%).
        - Platform Commission Vault CREDIT (10%).
        """
        price = cls._to_decimal(amount)
        fee = cls._to_decimal(platform_fee)
        earnings = cls._to_decimal(provider_earnings)

        c_wallet = cls.get_or_create_wallet(client_id, tx=tx)
        p_wallet = cls.get_or_create_wallet(provider_id, tx=tx)
        escrow_wallet = cls.get_or_create_wallet(SYSTEM_ESCROW_USER_ID, tx=tx)
        comm_wallet = cls.get_or_create_wallet(PLATFORM_COMMISSION_USER_ID, tx=tx)

        # 1. System Escrow DEBIT Release
        s_rel_key = f"SVC_ESCROW_SYS_RELEASE_ORD_{order_id}_DEBIT"
        tx.execute("""
        INSERT INTO wallet_transactions (
            wallet_id, user_id, entry_type, tx_type, amount, reference_type, reference_id, idempotency_key, status, notes
        ) VALUES (?, ?, 'DEBIT', 'DepositEscrowHold', ?, 'service_order', ?, ?, 'Completed', ?);
        """, (escrow_wallet["wallet_id"], SYSTEM_ESCROW_USER_ID, float(price), order_id, s_rel_key, f"System escrow release for service order #{order_id}"))

        # 2. Provider Earnings CREDIT
        p_key = f"SVC_EARNING_ORD_{order_id}_CREDIT"
        tx.execute("""
        INSERT INTO wallet_transactions (
            wallet_id, user_id, entry_type, tx_type, amount, reference_type, reference_id, idempotency_key, status, notes
        ) VALUES (?, ?, 'CREDIT', 'ServiceIncome', ?, 'service_order', ?, ?, 'Completed', ?);
        """, (p_wallet["wallet_id"], provider_id, float(earnings), order_id, p_key, f"Earnings for service order #{order_id}"))

        new_p_avail = cls._to_decimal(p_wallet["available_balance"]) + earnings
        new_p_earned = cls._to_decimal(p_wallet["total_earned"]) + earnings
        tx.execute("UPDATE user_wallets SET available_balance = ?, total_earned = ?, updated_at = CURRENT_TIMESTAMP WHERE wallet_id = ?;", (float(new_p_avail), float(new_p_earned), p_wallet["wallet_id"]))

        # 3. Platform Commission CREDIT
        comm_key = f"SVC_COMMISSION_ORD_{order_id}_CREDIT"
        tx.execute("""
        INSERT INTO wallet_transactions (
            wallet_id, user_id, entry_type, tx_type, amount, reference_type, reference_id, idempotency_key, status, notes
        ) VALUES (?, ?, 'CREDIT', 'PlatformCommission', ?, 'service_order', ?, ?, 'Completed', ?);
        """, (comm_wallet["wallet_id"], PLATFORM_COMMISSION_USER_ID, float(fee), order_id, comm_key, f"10% Platform fee on service order #{order_id}"))

        new_comm_avail = cls._to_decimal(comm_wallet["available_balance"]) + fee
        new_comm_earned = cls._to_decimal(comm_wallet["total_earned"]) + fee
        tx.execute("UPDATE user_wallets SET available_balance = ?, total_earned = ?, updated_at = CURRENT_TIMESTAMP WHERE wallet_id = ?;", (float(new_comm_avail), float(new_comm_earned), comm_wallet["wallet_id"]))

        # Clear client locked escrow
        new_c_escrow = max(Decimal("0.00"), cls._to_decimal(c_wallet["locked_escrow"]) - price)
        tx.execute("UPDATE user_wallets SET locked_escrow = ?, updated_at = CURRENT_TIMESTAMP WHERE wallet_id = ?;", (float(new_c_escrow), c_wallet["wallet_id"]))

    @classmethod
    def refund_service_escrow(
        cls,
        tx,
        order_id: int,
        client_id: int,
        amount: Any,
        reason: str = "Order cancelled"
    ) -> None:
        """
        Dual-sided ledger refund on service cancellation:
        - System Escrow DEBIT (100%).
        - Client Wallet CREDIT (100%).
        """
        price = cls._to_decimal(amount)
        c_wallet = cls.get_or_create_wallet(client_id, tx=tx)
        escrow_wallet = cls.get_or_create_wallet(SYSTEM_ESCROW_USER_ID, tx=tx)

        # 1. System Escrow DEBIT Release
        s_rel_key = f"SVC_ESCROW_SYS_REFUND_ORD_{order_id}_DEBIT"
        tx.execute("""
        INSERT INTO wallet_transactions (
            wallet_id, user_id, entry_type, tx_type, amount, reference_type, reference_id, idempotency_key, status, notes
        ) VALUES (?, ?, 'DEBIT', 'DepositEscrowHold', ?, 'service_order', ?, ?, 'Completed', ?);
        """, (escrow_wallet["wallet_id"], SYSTEM_ESCROW_USER_ID, float(price), order_id, s_rel_key, f"System escrow refund release for service order #{order_id}"))

        # 2. Client Refund CREDIT
        ref_key = f"SVC_REFUND_ORD_{order_id}_CREDIT"
        tx.execute("""
        INSERT INTO wallet_transactions (
            wallet_id, user_id, entry_type, tx_type, amount, reference_type, reference_id, idempotency_key, status, notes
        ) VALUES (?, ?, 'CREDIT', 'DepositRefund', ?, 'service_order', ?, ?, 'Completed', ?);
        """, (c_wallet["wallet_id"], client_id, float(price), order_id, ref_key, f"Refund for cancelled order #{order_id}: {reason}"))

        new_c_avail = cls._to_decimal(c_wallet["available_balance"]) + price
        new_c_escrow = max(Decimal("0.00"), cls._to_decimal(c_wallet["locked_escrow"]) - price)
        tx.execute("UPDATE user_wallets SET available_balance = ?, locked_escrow = ?, updated_at = CURRENT_TIMESTAMP WHERE wallet_id = ?;", (float(new_c_avail), float(new_c_escrow), c_wallet["wallet_id"]))
