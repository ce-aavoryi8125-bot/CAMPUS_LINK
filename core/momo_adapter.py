"""
core/momo_adapter.py
--------------------
Mobile Money Gateway Adapters for CampusLink 2.0.
Includes:
- MockMoMoAdapter: In-memory simulator for local development, unit tests, and CI/CD.
- Pluggable extension points for Paystack, Hubtel, and MTN MoMo Open API.
"""
import hmac
import hashlib
import json
import time
from typing import Dict, Any, Optional
from decimal import Decimal

from .payment_interface import PaymentGatewayInterface, GatewayResponse

class MockMoMoAdapter(PaymentGatewayInterface):
    """
    In-memory Mock Mobile Money Adapter for development and adversarial testing.
    Simulates USSD push prompts, async webhook callbacks, and settlement responses.
    """

    def __init__(self, webhook_secret: str = "campuslink_mock_webhook_secret_2026"):
        self.webhook_secret = webhook_secret
        self.transactions: Dict[str, Dict[str, Any]] = {}

    def initiate_deposit(
        self,
        user_id: int,
        amount: Decimal,
        network: str,
        phone_number: str,
        reference: str,
        callback_url: Optional[str] = None
    ) -> GatewayResponse:
        clean_phone = str(phone_number).strip().replace(" ", "").replace("-", "")
        if len(clean_phone) < 9 or not clean_phone.replace("+", "").isdigit():
            return GatewayResponse(
                success=False,
                reference=reference,
                status="Failed",
                message="Invalid Ghanaian phone number format. Must be 10 digits (e.g. 0244123456)."
            )

        gateway_tx_id = f"MOCK_GW_DEP_{int(time.time() * 1000)}_{reference[-6:]}"
        self.transactions[reference] = {
            "user_id": user_id,
            "amount": amount,
            "network": network,
            "phone_number": clean_phone,
            "reference": reference,
            "gateway_tx_id": gateway_tx_id,
            "status": "Pending",
            "type": "deposit",
            "created_at": time.time()
        }

        return GatewayResponse(
            success=True,
            reference=reference,
            gateway_tx_id=gateway_tx_id,
            status="Pending",
            message=f"USSD prompt dispatched to {network} ({clean_phone}). Awaiting PIN confirmation.",
            raw_data=self.transactions[reference]
        )

    def initiate_payout(
        self,
        user_id: int,
        amount: Decimal,
        network: str,
        phone_number: str,
        reference: str
    ) -> GatewayResponse:
        clean_phone = str(phone_number).strip().replace(" ", "").replace("-", "")
        if len(clean_phone) < 9 or not clean_phone.replace("+", "").isdigit():
            return GatewayResponse(
                success=False,
                reference=reference,
                status="Failed",
                message="Invalid payout phone number."
            )

        gateway_tx_id = f"MOCK_GW_PAYOUT_{int(time.time() * 1000)}_{reference[-6:]}"
        self.transactions[reference] = {
            "user_id": user_id,
            "amount": amount,
            "network": network,
            "phone_number": clean_phone,
            "reference": reference,
            "gateway_tx_id": gateway_tx_id,
            "status": "Pending",
            "type": "payout",
            "created_at": time.time()
        }

        return GatewayResponse(
            success=True,
            reference=reference,
            gateway_tx_id=gateway_tx_id,
            status="Pending",
            message=f"Payout of GH₵ {amount:.2f} dispatched to {network} ({clean_phone}).",
            raw_data=self.transactions[reference]
        )

    def verify_transaction(self, reference: str) -> GatewayResponse:
        if reference not in self.transactions:
            return GatewayResponse(
                success=False,
                reference=reference,
                status="NotFound",
                message=f"Transaction reference '{reference}' not found on gateway."
            )

        tx = self.transactions[reference]
        return GatewayResponse(
            success=True,
            reference=reference,
            gateway_tx_id=tx["gateway_tx_id"],
            status=tx["status"],
            message=f"Transaction is currently {tx['status']}.",
            raw_data=tx
        )

    def verify_webhook_signature(
        self,
        raw_payload: bytes,
        signature_header: str,
        secret: Optional[str] = None
    ) -> bool:
        """Validates HMAC-SHA512 cryptographic webhook signature."""
        active_secret = secret or self.webhook_secret
        if not signature_header or not active_secret:
            return False

        computed = hmac.new(
            active_secret.encode('utf-8'),
            raw_payload,
            hashlib.sha512
        ).hexdigest()

        return hmac.compare_digest(computed.lower(), signature_header.lower())

    def generate_webhook_payload(
        self,
        reference: str,
        event_type: str = "charge.success",
        status: str = "Successful",
        amount_override: Optional[Decimal] = None
    ) -> Dict[str, Any]:
        """Helper to generate signed mock webhook payload for testing."""
        tx = self.transactions.get(reference, {})
        amt = amount_override if amount_override is not None else tx.get("amount", Decimal("0.00"))
        gw_id = tx.get("gateway_tx_id", f"GW_{reference}")

        payload = {
            "event": event_type,
            "timestamp": int(time.time()),
            "data": {
                "reference": reference,
                "gateway_tx_id": gw_id,
                "status": status,
                "amount": float(amt),
                "currency": "GHS",
                "network": tx.get("network", "MTN"),
                "phone_number": tx.get("phone_number", "0244123456"),
                "customer": {
                    "user_id": tx.get("user_id", 1)
                }
            }
        }
        raw_bytes = json.dumps(payload, sort_keys=True).encode('utf-8')
        sig = hmac.new(self.webhook_secret.encode('utf-8'), raw_bytes, hashlib.sha512).hexdigest()
        return {
            "payload": payload,
            "raw_bytes": raw_bytes,
            "signature": sig
        }

# Global Adapter Factory
_global_adapter: Optional[PaymentGatewayInterface] = None

def get_payment_gateway() -> PaymentGatewayInterface:
    global _global_adapter
    if _global_adapter is None:
        _global_adapter = MockMoMoAdapter()
    return _global_adapter

def set_payment_gateway(adapter: PaymentGatewayInterface):
    global _global_adapter
    _global_adapter = adapter
