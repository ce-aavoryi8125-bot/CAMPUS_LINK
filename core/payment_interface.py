"""
core/payment_interface.py
-------------------------
Provider-Independent Payment Gateway Interface for CampusLink 2.0.
Defines abstract contracts for Mobile Money (MTN MoMo, Telecel Cash, AT Money)
deposit initiation, payout dispatches, transaction status verification, and webhook signature validation.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from decimal import Decimal
import hmac
import hashlib
import json

class GatewayResponse:
    """Standardized response from any payment gateway adapter."""
    def __init__(
        self,
        success: bool,
        reference: str,
        gateway_tx_id: Optional[str] = None,
        status: str = "Pending",
        message: str = "",
        raw_data: Optional[Dict[str, Any]] = None
    ):
        self.success = success
        self.reference = reference
        self.gateway_tx_id = gateway_tx_id
        self.status = status # 'Pending', 'Successful', 'Failed', 'Cancelled'
        self.message = message
        self.raw_data = raw_data or {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "reference": self.reference,
            "gateway_tx_id": self.gateway_tx_id,
            "status": self.status,
            "message": self.message,
            "raw_data": self.raw_data
        }


class PaymentGatewayInterface(ABC):
    """Abstract interface all payment gateway adapters must implement."""

    @abstractmethod
    def initiate_deposit(
        self,
        user_id: int,
        amount: Decimal,
        network: str,
        phone_number: str,
        reference: str,
        callback_url: Optional[str] = None
    ) -> GatewayResponse:
        """Initiates customer MoMo debit prompt (USSD push)."""
        pass

    @abstractmethod
    def initiate_payout(
        self,
        user_id: int,
        amount: Decimal,
        network: str,
        phone_number: str,
        reference: str
    ) -> GatewayResponse:
        """Dispatches funds from platform settlement account to student MoMo wallet."""
        pass

    @abstractmethod
    def verify_transaction(self, reference: str) -> GatewayResponse:
        """Queries gateway API for current status of a transaction reference."""
        pass

    @abstractmethod
    def verify_webhook_signature(
        self,
        raw_payload: bytes,
        signature_header: str,
        secret: str
    ) -> bool:
        """Validates cryptographic signature of an incoming gateway webhook."""
        pass
