from typing import Any
import httpx
from app.config import get_settings
from app.utils.helpers import generate_paystack_reference

settings = get_settings()


class PaystackClient:
    def __init__(self) -> None:
        self.base_url = settings.PAYSTACK_BASE_URL
        self.headers = {
            "Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}",
            "Content-Type": "application/json",
        }

    async def initialize_transaction(
        self,
        email: str,
        amount: int,
        metadata: dict[str, Any] | None = None,
        callback_url: str | None = None,
        reference: str | None = None,
    ) -> dict[str, Any]:
        payload = {
            "email": email,
            "amount": amount,
            "metadata": metadata or {},
        }
        if callback_url:
            payload["callback_url"] = callback_url
        payload["reference"] = reference or generate_paystack_reference()

        async with httpx.AsyncClient(base_url=self.base_url, headers=self.headers, timeout=15.0) as client:
            response = await client.post("/transaction/initialize", json=payload)
            response.raise_for_status()
            data = response.json()
            if not data.get("status"):
                raise RuntimeError(data.get("message", "Paystack initialization failed"))
            return data["data"]

    async def verify_transaction(self, reference: str) -> dict[str, Any]:
        async with httpx.AsyncClient(base_url=self.base_url, headers=self.headers, timeout=15.0) as client:
            response = await client.get(f"/transaction/verify/{reference}")
            response.raise_for_status()
            data = response.json()
            if not data.get("status"):
                raise RuntimeError(data.get("message", "Paystack verification failed"))
            return data["data"]


paystack_client = PaystackClient()
