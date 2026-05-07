from datetime import datetime
from pydantic import BaseModel, Field


class BookingCreate(BaseModel):
    event_id: str
    quantity: int = Field(..., gt=0)


class BookingResponse(BaseModel):
    id: str
    user_id: str
    event_id: str
    quantity: int
    total_amount: int
    status: str
    paystack_reference: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
