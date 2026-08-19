"""
tasks/notification_tasks.py
---------------------------
Asynchronous background notification dispatch tasks.
Allows API endpoints and background workflows to enqueue user notifications non-blockingly.
"""
import logging
from core.celery_app import celery_app
import controllers

logger = logging.getLogger("campuslink.tasks.notifications")

@celery_app.task(
    name="tasks.notification_tasks.dispatch_notification_task",
    acks_late=True
)
def dispatch_notification_task(user_id: int, title: str, message: str, notif_type: str = "info"):
    """
    Asynchronously inserts a notification record for a user.
    """
    logger.info("Dispatching async notification to user %s: %s", user_id, title)
    try:
        notif_id = controllers.create_notification(
            user_id=int(user_id),
            title=title,
            message=message,
            type=notif_type
        )
        return {"success": True, "notification_id": notif_id, "user_id": user_id}
    except Exception as e:
        logger.error("Failed to dispatch async notification to user %s: %s", user_id, str(e))
        return {"success": False, "error": str(e), "user_id": user_id}
