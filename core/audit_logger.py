"""
core/audit_logger.py
--------------------
Security and Financial Audit Logger for CampusLink 2.0.
Logs sensitive actions such as logins, password updates, rental approvals, returns,
and wallet transactions.
"""
import logging
import json
from datetime import datetime, timezone
from typing import Optional, Dict, Any

# Configure structured audit logger
audit_logger = logging.getLogger("campuslink.audit")
audit_logger.setLevel(logging.INFO)

if not audit_logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('[AUDIT %(asctime)s] %(message)s')
    handler.setFormatter(formatter)
    audit_logger.addHandler(handler)

def log_security_event(
    event_type: str,
    user_id: Optional[int],
    status: str,
    ip_address: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None
):
    """Logs an auditable security event (login, role check failure, password change)."""
    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event_type": event_type,
        "user_id": user_id,
        "status": status,
        "ip_address": ip_address,
        "details": details or {}
    }
    audit_logger.info(json.dumps(payload))

def log_financial_event(
    action: str,
    user_id: int,
    amount: float,
    reference_type: str,
    reference_id: int,
    status: str = "SUCCESS",
    notes: str = ""
):
    """Logs an auditable financial event (commission split, earnings, escrow hold/release)."""
    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event": "FINANCIAL_TRANSACTION",
        "action": action,
        "user_id": user_id,
        "amount": amount,
        "reference_type": reference_type,
        "reference_id": reference_id,
        "status": status,
        "notes": notes
    }
    audit_logger.info(json.dumps(payload))
