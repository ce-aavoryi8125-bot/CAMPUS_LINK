"""
tasks/webhook_tasks.py
----------------------
Asynchronous background tasks for Mobile Money webhook processing.
Delegates all ledger state transitions directly to FinancialService to guarantee
financial invariants, double-entry parity, and database-level idempotency.
"""
import logging
from decimal import Decimal
from core.celery_app import celery_app
from core.wallet_service import FinancialService

logger = logging.getLogger("campuslink.tasks.webhooks")

@celery_app.task(
    bind=True,
    name="tasks.webhook_tasks.process_momo_deposit_webhook_task",
    max_retries=3,
    default_retry_delay=5,
    autoretry_for=(),  # Controlled manual retry for transient errors only
    acks_late=True
)
def process_momo_deposit_webhook_task(self, reference: str, user_id: int, amount_str: str, gateway_tx_id: str):
    """
    Asynchronously processes a successful Mobile Money deposit webhook.
    Invokes FinancialService.settle_momo_deposit to execute atomic, balanced double-entry accounting.
    """
    logger.info("Processing async deposit webhook task for ref: %s, user: %s, amount: %s", reference, user_id, amount_str)
    try:
        amount = Decimal(str(amount_str))
        ok, msg = FinancialService.settle_momo_deposit(
            reference=reference,
            user_id=int(user_id),
            amount=amount,
            gateway_tx_id=gateway_tx_id
        )
        logger.info("Async deposit settlement result for %s: ok=%s, msg=%s", reference, ok, msg)
        return {"success": ok, "message": msg, "reference": reference}
    except Exception as e:
        logger.error("Exception during async deposit settlement for %s: %s", reference, str(e))
        # Retry only on unexpected runtime errors; idempotency prevents double-crediting
        raise self.retry(exc=e)

@celery_app.task(
    bind=True,
    name="tasks.webhook_tasks.process_momo_payout_webhook_task",
    max_retries=3,
    default_retry_delay=5,
    autoretry_for=(),
    acks_late=True
)
def process_momo_payout_webhook_task(self, reference: str, success: bool, notes: str = ""):
    """
    Asynchronously processes a Mobile Money payout confirmation / failure callback.
    Invokes FinancialService.settle_momo_payout to execute atomic confirmation or compensating reversal.
    """
    logger.info("Processing async payout webhook task for ref: %s, success: %s", reference, success)
    try:
        ok, msg = FinancialService.settle_momo_payout(
            reference=reference,
            success=success,
            notes=notes
        )
        logger.info("Async payout settlement result for %s: ok=%s, msg=%s", reference, ok, msg)
        return {"success": ok, "message": msg, "reference": reference}
    except Exception as e:
        logger.error("Exception during async payout settlement for %s: %s", reference, str(e))
        raise self.retry(exc=e)
