from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
from app.models.event import EventStatus


class EventCreate(BaseModel):
    title: str
    description: Optional[str] = None
    venue: str
    event_date: datetime
    total_tickets: int = Field(..., gt=0)
    ticket_price: int = Field(..., gt=0)
    currency: str = Field(default="NGN", min_length=3, max_length=3)
    status: EventStatus = EventStatus.draft


class EventUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    venue: Optional[str] = None
    event_date: Optional[datetime] = None
    total_tickets: Optional[int] = Field(None, gt=0)
    ticket_price: Optional[int] = Field(None, gt=0)
    currency: Optional[str] = Field(None, min_length=3, max_length=3)
    status: Optional[EventStatus] = None


class EventResponse(BaseModel):
    id: str
    organizer_id: str
    title: str
    description: Optional[str]
    venue: str
    event_date: datetime
    total_tickets: int
    available_tickets: int
    ticket_price: int
    currency: str
    status: EventStatus
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
