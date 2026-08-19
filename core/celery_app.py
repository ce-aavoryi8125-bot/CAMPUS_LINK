"""
core/celery_app.py
------------------
Celery Application Factory and Configuration for CampusLink 2.0.
Manages:
1. Redis broker and result backend connection.
2. Serialization security (JSON only).
3. Resilient task acknowledgment (acks_late, reject_on_worker_lost).
4. Celery Beat periodic task schedules (Hourly Reconciliation, Daily 00:00 UTC Overdue Sweeper).
5. Dual-mode eager execution for unit testing without worker daemon.
"""
import os
import logging
from celery import Celery
from celery.schedules import crontab

from .config import PlatformConfig

logger = logging.getLogger("campuslink.celery")

def make_celery(app_name: str = "campuslink") -> Celery:
    """
    Constructs and configures the Celery application instance.
    """
    app = Celery(
        app_name,
        broker=PlatformConfig.CELERY_BROKER_URL,
        backend=PlatformConfig.CELERY_RESULT_BACKEND,
        include=[
            "tasks.webhook_tasks",
            "tasks.reconciliation_tasks",
            "tasks.escrow_tasks",
            "tasks.notification_tasks",
        ]
    )

    app.conf.update(
        task_serializer="json",
        result_serializer="json",
        accept_content=["json"],
        timezone="UTC",
        enable_utc=True,
        task_acks_late=True,
        task_reject_on_worker_lost=True,
        task_always_eager=PlatformConfig.CELERY_ALWAYS_EAGER,
        task_eager_propagates=True,
        task_time_limit=PlatformConfig.CELERY_TASK_TIME_LIMIT_SEC,
        worker_prefetch_multiplier=1,
        broker_connection_retry_on_startup=True,
        beat_schedule={
            "hourly-financial-reconciliation": {
                "task": "tasks.reconciliation_tasks.run_periodic_reconciliation_task",
                "schedule": crontab(minute=0),  # Top of every hour
            },
            "daily-overdue-rental-sweeper": {
                "task": "tasks.escrow_tasks.sweep_overdue_rentals_task",
                "schedule": crontab(hour=0, minute=0),  # Exactly 00:00 UTC daily
            },
        }
    )

    return app

celery_app = make_celery()
