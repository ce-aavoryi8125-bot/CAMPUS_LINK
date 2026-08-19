"""
tasks/escrow_tasks.py
---------------------
Scheduled background task for overdue rental detection and maintenance ticket sweeps.
Triggered daily at 00:00 UTC via Celery Beat crontab(hour=0, minute=0).
"""
import logging
from datetime import datetime, date
from core.celery_app import celery_app
import db_engine
import controllers

logger = logging.getLogger("campuslink.tasks.escrow")

@celery_app.task(
    name="tasks.escrow_tasks.sweep_overdue_rentals_task",
    acks_late=True
)
def sweep_overdue_rentals_task():
    """
    Scans for active rental transactions where rent_end_date has elapsed.
    Dispatches automated overdue notifications to borrowers and owners.
    """
    logger.info("Executing daily 00:00 UTC overdue rental sweeper...")
    today_str = date.today().strftime("%Y-%m-%d")
    
    query = """
        SELECT t.transaction_id, t.listing_id, t.borrower_id, t.rent_end_date, l.title, l.owner_id
        FROM rental_transactions t
        JOIN listings l ON t.listing_id = l.listing_id
        WHERE t.rental_status = 'Active' AND t.rent_end_date < ?;
    """
    
    overdue_rows = db_engine.execute_query(query, (today_str,), fetch="all") or []
    overdue_count = len(overdue_rows)
    notified_count = 0
    
    for row in overdue_rows:
        tx_id = row.get("transaction_id")
        borrower_id = row.get("borrower_id")
        owner_id = row.get("owner_id")
        title = row.get("title")
        end_date = row.get("rent_end_date")
        
        # Notify borrower
        controllers.create_notification(
            user_id=borrower_id,
            title="Overdue Equipment Return Alert",
            message=f"Your rental for '{title}' ended on {end_date}. Please return the item to avoid deposit deductions.",
            type="warning"
        )
        # Notify owner
        controllers.create_notification(
            user_id=owner_id,
            title="Rental Return Pending",
            message=f"The rental for your listing '{title}' was due on {end_date}. Please confirm once returned.",
            type="info"
        )
        notified_count += 2
        
    logger.info("Overdue sweeper finished: identified %d overdue rentals, dispatched %d notifications.", overdue_count, notified_count)
    return {
        "success": True,
        "overdue_rentals_found": overdue_count,
        "notifications_dispatched": notified_count,
        "sweep_date": today_str
    }
