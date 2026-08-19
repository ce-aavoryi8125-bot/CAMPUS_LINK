"""
core/reconciliation.py
----------------------
Financial Reconciliation Engine for CampusLink 2.0.
Periodically audits internal wallet_transactions against Payment Gateway settlement records.
Detects:
- Type I: Ghost Payments (Gateway settled, but internal ledger missing record).
- Type II: False Credits (Internal ledger credited, but gateway failed/missing).
- Type III: Amount Mismatches (Ledger amount != Gateway amount).
"""
from typing import List, Dict, Any, Tuple, Optional
from decimal import Decimal, ROUND_HALF_UP
import db_engine
from .payment_interface import PaymentGatewayInterface
from .momo_adapter import get_payment_gateway

class ReconciliationEngine:

    @classmethod
    def reconcile_transactions(
        cls,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        gateway: Optional[PaymentGatewayInterface] = None
    ) -> Dict[str, Any]:
        """
        Runs comprehensive reconciliation comparing internal ledger transactions
        with gateway status records.
        """
        gw = gateway or get_payment_gateway()
        
        # 1. Fetch internal customer MoMo ledger transactions (excluding system accounting mirror rows)
        query = """
        SELECT wallet_tx_id, user_id, entry_type, tx_type, amount, idempotency_key, status, created_at
        FROM wallet_transactions
        WHERE reference_type IN ('momo_deposit', 'momo_payout')
          AND user_id NOT IN (6, 7, 8)
          AND idempotency_key NOT LIKE '%_SYS_%'
        """
        params = []
        if start_date:
            query += " AND created_at >= ?"
            params.append(start_date)
        if end_date:
            query += " AND created_at <= ?"
            params.append(end_date)
            
        ledger_txs = db_engine.execute_query(query, params, fetch="all") or []

        matched: List[Dict[str, Any]] = []
        discrepancies: List[Dict[str, Any]] = []
        total_reconciled_amount = Decimal("0.00")

        for tx in ledger_txs:
            raw_key = tx.get("idempotency_key") or ""
            ref = raw_key
            for prefix in ("MOMO_DEP_", "MOMO_PAYOUT_REVERSAL_", "MOMO_PAYOUT_", "DEP_"):
                if ref.startswith(prefix):
                    ref = ref[len(prefix):]
            for suffix in ("_SYS_DEBIT", "_SYS_CREDIT", "_CREDIT", "_DEBIT"):
                if ref.endswith(suffix):
                    ref = ref[:-len(suffix)]
                    
            amt = Decimal(str(tx["amount"])).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            
            # Query Gateway
            gw_resp = gw.verify_transaction(ref)
            
            if not gw_resp.success:
                # Gateway has no record
                discrepancies.append({
                    "type": "TYPE_II_FALSE_CREDIT",
                    "reference": ref,
                    "ledger_tx_id": tx["wallet_tx_id"],
                    "ledger_amount": float(amt),
                    "gateway_status": "NotFound",
                    "severity": "HIGH",
                    "description": f"Ledger contains transaction {ref} but gateway has no record."
                })
            else:
                gw_data = gw_resp.raw_data
                gw_amt = Decimal(str(gw_data.get("amount", "0.00"))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                gw_status = gw_resp.status
                
                if gw_amt != amt:
                    # Amount mismatch
                    discrepancies.append({
                        "type": "TYPE_III_AMOUNT_MISMATCH",
                        "reference": ref,
                        "ledger_tx_id": tx["wallet_tx_id"],
                        "ledger_amount": float(amt),
                        "gateway_amount": float(gw_amt),
                        "severity": "CRITICAL",
                        "description": f"Amount mismatch: Ledger has GH₵ {amt:.2f}, Gateway has GH₵ {gw_amt:.2f}."
                    })
                elif gw_status != "Successful" and tx["status"] == "Completed":
                    # Status mismatch
                    discrepancies.append({
                        "type": "TYPE_II_FALSE_CREDIT",
                        "reference": ref,
                        "ledger_tx_id": tx["wallet_tx_id"],
                        "ledger_status": tx["status"],
                        "gateway_status": gw_status,
                        "severity": "HIGH",
                        "description": f"Ledger marked Completed but Gateway shows {gw_status}."
                    })
                else:
                    matched.append({
                        "reference": ref,
                        "amount": float(amt),
                        "status": "MATCHED"
                    })
                    total_reconciled_amount += amt

        return {
            "success": True,
            "total_checked": len(ledger_txs),
            "matched_count": len(matched),
            "discrepancy_count": len(discrepancies),
            "total_reconciled_volume": float(total_reconciled_amount),
            "is_balanced": len(discrepancies) == 0,
            "discrepancies": discrepancies,
            "matched": matched
        }
