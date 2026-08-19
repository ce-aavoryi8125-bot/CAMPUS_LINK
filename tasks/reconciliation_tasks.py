"""
tasks/reconciliation_tasks.py
-----------------------------
Scheduled and on-demand financial reconciliation background tasks.
Executes ReconciliationEngine across completed customer transactions to flag
any ghost payments, false credits, or amount mismatches.
"""
import logging
from core.celery_app import celery_app
from core.reconciliation import ReconciliationEngine

logger = logging.getLogger("campuslink.tasks.reconciliation")

@celery_app.task(
    name="tasks.reconciliation_tasks.run_periodic_reconciliation_task",
    acks_late=True
)
def run_periodic_reconciliation_task(start_date: str = None, end_date: str = None):
    """
    Executes a periodic financial reconciliation audit.
    Scheduled hourly via Celery Beat or triggered manually by administrators.
    """
    logger.info("Starting background financial reconciliation audit...")
    try:
        report = ReconciliationEngine.reconcile_transactions(start_date=start_date, end_date=end_date)
        summary = report.get("summary", {})
        matched = summary.get("matched_count", 0)
        discrepancies = summary.get("discrepancy_count", 0)
        
        logger.info("Reconciliation complete: %d matched, %d discrepancies found.", matched, discrepancies)
        if discrepancies > 0:
            logger.warning("AUDIT ALERT: %d financial reconciliation discrepancies flagged!", discrepancies)
            
        return {
            "success": True,
            "matched_count": matched,
            "discrepancy_count": discrepancies,
            "reconciliation_id": report.get("reconciliation_id")
        }
    except Exception as e:
        logger.error("Error during background financial reconciliation: %s", str(e))
        return {"success": False, "error": str(e)}
