import enum
import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Integer, DateTime, Enum as SQLEnum, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class PaymentStatus(str, enum.Enum):
    pending = "pending"
    success = "success"
    failed = "failed"
    abandoned = "abandoned"


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    booking_id: Mapped[str] = mapped_column(
        String, ForeignKey("bookings.id"), nullable=False, index=True
    )
    paystack_reference: Mapped[str] = mapped_column(String, unique=True, nullable=False, index=True)
    paystack_transaction_id: Mapped[str] = mapped_column(String, nullable=True)
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String, nullable=False, default="NGN")
    status: Mapped[PaymentStatus] = mapped_column(
        SQLEnum(PaymentStatus), nullable=False, default=PaymentStatus.pending
    )
    payment_channel: Mapped[str] = mapped_column(String, nullable=True)
    paid_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    paystack_response: Mapped[dict] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc)
    )

    def __repr__(self) -> str:
        return f"<Payment id={self.id} booking_id={self.booking_id} status={self.status}>"
