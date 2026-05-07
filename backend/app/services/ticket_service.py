import secrets
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.ticket import Ticket
from app.models.booking import Booking


def generate_ticket_code() -> str:
    return f"TKT-{secrets.token_hex(6).upper()}"


async def issue_tickets_for_booking(
    booking_id: str, db: AsyncSession
) -> list[Ticket]:
    booking_result = await db.execute(
        select(Booking).where(Booking.id == booking_id)
    )
    booking = booking_result.scalar_one_or_none()
    if not booking:
        raise ValueError(f"Booking {booking_id} not found")

    tickets = []
    for _ in range(booking.quantity):
        ticket = Ticket(
            booking_id=booking.id,
            user_id=booking.user_id,
            event_id=booking.event_id,
            ticket_code=generate_ticket_code(),
        )
        db.add(ticket)
        tickets.append(ticket)

    await db.flush()
    return tickets
