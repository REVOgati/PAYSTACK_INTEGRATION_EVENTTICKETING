from datetime import datetime
from typing import Optional
from pydantic import BaseModel
from app.models.payment import PaymentStatus


class PaymentResponse(BaseModel):
    id: str
    booking_id: str
    paystack_reference: str
    paystack_transaction_id: Optional[str]
    amount: int
    currency: str
    status: PaymentStatus
    payment_channel: Optional[str]
    paid_at: Optional[datetime]
    paystack_response: Optional[dict]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PaymentVerifyResponse(BaseModel):
    reference: str
    status: PaymentStatus
    amount: int
    currency: str
    paid_at: Optional[datetime]
