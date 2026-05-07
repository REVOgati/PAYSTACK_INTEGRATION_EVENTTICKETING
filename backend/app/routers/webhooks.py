import hmac
import hashlib
import json
import logging
from fastapi import APIRouter, HTTPException, status, Request, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models.payment import Payment, PaymentStatus
from app.models.booking import Booking, BookingStatus
from app.models.event import Event
from app.services.ticket_service import issue_tickets_for_booking
from app.config import get_settings

router = APIRouter()
settings = get_settings()
logger = logging.getLogger(__name__)


def validate_paystack_webhook(body: bytes, signature: str) -> bool:
    computed_hash = hmac.new(
        settings.PAYSTACK_SECRET_KEY.encode(),
        body,
        hashlib.sha512,
    ).hexdigest()
    return hmac.compare_digest(computed_hash, signature)


@router.post("/webhooks/paystack", status_code=status.HTTP_200_OK)
async def paystack_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    # Get the raw body
    body = await request.body()
    signature = request.headers.get("x-paystack-signature", "")

    if not validate_paystack_webhook(body, signature):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid webhook signature",
        )

    try:
        payload = json.loads(body.decode())
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON payload",
        )

    event_type = payload.get("event")
    data = payload.get("data", {})

    # Handle charge.success event
    if event_type == "charge.success":
        reference = data.get("reference")
        if not reference:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing reference in webhook",
            )

        logger.info(f"Processing charge.success webhook for reference: {reference}")

        payment_result = await db.execute(
            select(Payment).where(Payment.paystack_reference == reference)
        )
        payment = payment_result.scalar_one_or_none()

        if payment and payment.status != PaymentStatus.success:
            payment.status = PaymentStatus.success
            payment.paystack_transaction_id = data.get("id")
            payment.paid_at = data.get("paid_at")
            payment.payment_channel = data.get("channel")
            payment.paystack_response = data

            booking_result = await db.execute(
                select(Booking).where(Booking.id == payment.booking_id)
            )
            booking = booking_result.scalar_one_or_none()

            if booking and booking.status == BookingStatus.pending:
                booking.status = BookingStatus.confirmed
                await issue_tickets_for_booking(booking.id, db)
                logger.info(f"Booking {booking.id} confirmed and tickets issued. Reference: {reference}")

    # Handle charge.failed event
    elif event_type == "charge.failed":
        reference = data.get("reference")
        if not reference:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing reference in webhook",
            )

        logger.warning(f"Processing charge.failed webhook for reference: {reference}")

        payment_result = await db.execute(
            select(Payment).where(Payment.paystack_reference == reference)
        )
        payment = payment_result.scalar_one_or_none()

        if payment and payment.status != PaymentStatus.failed:
            payment.status = PaymentStatus.failed
            payment.paystack_response = data

            booking_result = await db.execute(
                select(Booking).where(Booking.id == payment.booking_id)
            )
            booking = booking_result.scalar_one_or_none()

            if booking and booking.status == BookingStatus.pending:
                booking.status = BookingStatus.failed
                event_result = await db.execute(
                    select(Event).where(Event.id == booking.event_id)
                )
                event = event_result.scalar_one()
                event.available_tickets += booking.quantity
                logger.warning(f"Booking {booking.id} failed. Tickets released. Reference: {reference}")

    return {"status": "ok", "message": "Webhook processed"}
