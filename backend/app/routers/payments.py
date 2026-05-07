from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.payment import PaymentResponse, PaymentVerifyResponse
from app.models.booking import Booking, BookingStatus
from app.models.payment import Payment, PaymentStatus
from app.utils.dependancies import get_current_user
from app.database import get_db
from app.services.paystack import paystack_client
from app.config import get_settings

router = APIRouter()
settings = get_settings()


@router.post("/payments/initialize", response_model=PaymentResponse, status_code=status.HTTP_201_CREATED)
async def initialize_payment(
    booking_id: str,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Booking).where(Booking.id == booking_id))
    booking = result.scalar_one_or_none()
    if booking is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")

    if booking.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only initialize payment for your own bookings.",
        )

    if booking.status != BookingStatus.pending:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Payment can only be initialized for pending bookings.",
        )

    payment_result = await db.execute(
        select(Payment).where(Payment.booking_id == booking_id)
    )
    existing_payment = payment_result.scalar_one_or_none()
    if existing_payment and existing_payment.status == PaymentStatus.success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This booking already has a successful payment.",
        )

    metadata = {
        "booking_id": booking.id,
        "user_id": booking.user_id,
        "event_id": booking.event_id,
        "quantity": booking.quantity,
    }

    try:
        paystack_response = await paystack_client.initialize_transaction(
            email=current_user.email,
            amount=booking.total_amount,
            metadata=metadata,
            callback_url=settings.CALLBACK_URL,
            reference=booking.paystack_reference,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to initialize payment with Paystack: {str(e)}",
        )

    payment = Payment(
        booking_id=booking.id,
        paystack_reference=booking.paystack_reference,
        amount=booking.total_amount,
        currency="NGN",
        status=PaymentStatus.pending,
        paystack_response=paystack_response,
    )
    db.add(payment)
    await db.flush()

    return payment


@router.get("/payments/callback", status_code=status.HTTP_200_OK)
async def payment_callback(
    reference: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Payment).where(Payment.paystack_reference == reference)
    )
    payment = result.scalar_one_or_none()
    if payment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment record not found for this reference.",
        )

    try:
        paystack_data = await paystack_client.verify_transaction(reference)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to verify payment with Paystack: {str(e)}",
        )

    if paystack_data.get("status") == "success":
        payment.status = PaymentStatus.success
        payment.paystack_transaction_id = paystack_data.get("id")
        payment.paid_at = paystack_data.get("paid_at")
        payment.payment_channel = paystack_data.get("channel")
        payment.paystack_response = paystack_data

        booking_result = await db.execute(
            select(Booking).where(Booking.id == payment.booking_id)
        )
        booking = booking_result.scalar_one()
        booking.status = BookingStatus.confirmed
    else:
        payment.status = PaymentStatus.failed
        payment.paystack_response = paystack_data

        booking_result = await db.execute(
            select(Booking).where(Booking.id == payment.booking_id)
        )
        booking = booking_result.scalar_one()
        if booking.status == BookingStatus.pending:
            booking.status = BookingStatus.failed

    await db.flush()
    return {"status": "ok", "message": "Payment verified and booking updated"}


@router.get("/payments/verify/{reference}", response_model=PaymentVerifyResponse)
async def verify_payment(
    reference: str,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Payment).where(Payment.paystack_reference == reference)
    )
    payment = result.scalar_one_or_none()
    if payment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found for this reference.",
        )

    booking_result = await db.execute(
        select(Booking).where(Booking.id == payment.booking_id)
    )
    booking = booking_result.scalar_one()

    if booking.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only verify your own payments.",
        )

    try:
        paystack_data = await paystack_client.verify_transaction(reference)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to verify payment with Paystack: {str(e)}",
        )

    if paystack_data.get("status") == "success" and payment.status != PaymentStatus.success:
        payment.status = PaymentStatus.success
        payment.paystack_transaction_id = paystack_data.get("id")
        payment.paid_at = paystack_data.get("paid_at")
        payment.payment_channel = paystack_data.get("channel")
        payment.paystack_response = paystack_data
        booking.status = BookingStatus.confirmed
        await db.flush()

    return PaymentVerifyResponse(
        reference=reference,
        status=payment.status,
        amount=payment.amount,
        currency=payment.currency,
        paid_at=payment.paid_at,
    )
