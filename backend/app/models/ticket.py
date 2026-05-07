import enum
import uuid
from datetime import datetime, timezone
from sqlalchemy import String, DateTime, Enum as SQLEnum, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class TicketStatus(str, enum.Enum):
    active = "active"
    used = "used"
    cancelled = "cancelled"


class Ticket(Base):
    __tablename__ = "tickets"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    booking_id: Mapped[str] = mapped_column(
        String, ForeignKey("bookings.id"), nullable=False, index=True
    )
    user_id: Mapped[str] = mapped_column(
        String, ForeignKey("users.id"), nullable=False, index=True
    )
    event_id: Mapped[str] = mapped_column(
        String, ForeignKey("events.id"), nullable=False, index=True
    )
    ticket_code: Mapped[str] = mapped_column(String, nullable=False, unique=True, index=True)
    status: Mapped[TicketStatus] = mapped_column(
        SQLEnum(TicketStatus), nullable=False, default=TicketStatus.active
    )
    issued_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc)
    )

    def __repr__(self) -> str:
        return f"<Ticket id={self.id} ticket_code={self.ticket_code} status={self.status}>"
