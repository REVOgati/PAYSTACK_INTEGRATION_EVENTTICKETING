from datetime import datetime
from pydantic import BaseModel
from app.models.ticket import TicketStatus


class TicketResponse(BaseModel):
    id: str
    booking_id: str
    user_id: str
    event_id: str
    ticket_code: str
    status: TicketStatus
    issued_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
