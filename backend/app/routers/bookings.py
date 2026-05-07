from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.booking import BookingCreate, BookingResponse
from app.schemas.ticket import TicketResponse
from app.models.booking import Booking
from app.models.ticket import Ticket
from app.models.event import Event, EventStatus
from app.utils.dependancies import get_current_user
from app.database import get_db
from app.utils.helpers import generate_paystack_reference

router = APIRouter()


@router.post("/bookings", response_model=BookingResponse, status_code=status.HTTP_201_CREATED)
async def create_booking(
    booking_in: BookingCreate,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Event).where(Event.id == booking_in.event_id))
    event = result.scalar_one_or_none()
    if event is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")

    if event.status != EventStatus.published:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tickets can only be booked for published events.",
        )

    if booking_in.quantity > event.available_tickets:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Not enough tickets available for this event.",
        )

    reference = generate_paystack_reference()
    total_amount = event.ticket_price * booking_in.quantity

    booking = Booking(
        user_id=current_user.id,
        event_id=event.id,
        quantity=booking_in.quantity,
        total_amount=total_amount,
        paystack_reference=reference,
    )
    event.available_tickets -= booking_in.quantity

    db.add(booking)
    await db.flush()
    return booking


@router.get("/bookings/{booking_id}", response_model=BookingResponse)
async def get_booking(
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
            detail="You can only view your own bookings.",
        )

    return booking


@router.get("/bookings/me", response_model=list[BookingResponse])
async def get_my_bookings(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Booking).where(Booking.user_id == current_user.id))
    bookings = result.scalars().all()
    return bookings


@router.get("/bookings/{booking_id}/tickets", response_model=list[TicketResponse])
async def get_booking_tickets(
    booking_id: str,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    booking_result = await db.execute(select(Booking).where(Booking.id == booking_id))
    booking = booking_result.scalar_one_or_none()
    if booking is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")

    if booking.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only view tickets for your own bookings.",
        )

    result = await db.execute(select(Ticket).where(Ticket.booking_id == booking_id))
    tickets = result.scalars().all()
    return tickets
