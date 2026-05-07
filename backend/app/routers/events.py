from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.event import EventCreate, EventUpdate, EventResponse
from app.models.event import Event, EventStatus
from app.models.user import UserRole
from app.utils.dependancies import require_role
from app.database import get_db

router = APIRouter()


@router.get("/events", response_model=list[EventResponse])
async def list_published_events(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Event).where(Event.status == EventStatus.published))
    events = result.scalars().all()
    return events


@router.get("/events/{event_id}", response_model=EventResponse)
async def get_event(event_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Event).where(Event.id == event_id))
    event = result.scalar_one_or_none()
    if event is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
    return event


@router.post("/events", response_model=EventResponse, status_code=status.HTTP_201_CREATED)
async def create_event(
    event_in: EventCreate,
    current_user=Depends(require_role("organizer", "admin")),
    db: AsyncSession = Depends(get_db),
):
    event = Event(
        organizer_id=current_user.id,
        title=event_in.title,
        description=event_in.description,
        venue=event_in.venue,
        event_date=event_in.event_date,
        total_tickets=event_in.total_tickets,
        available_tickets=event_in.total_tickets,
        ticket_price=event_in.ticket_price,
        currency=event_in.currency,
        status=event_in.status,
    )
    db.add(event)
    await db.flush()
    return event


@router.patch("/events/{event_id}", response_model=EventResponse)
async def update_event(
    event_id: str,
    event_in: EventUpdate,
    current_user=Depends(require_role("organizer", "admin")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Event).where(Event.id == event_id))
    event = result.scalar_one_or_none()
    if event is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")

    if current_user.role != UserRole.admin and event.organizer_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the event organizer or admin can update this event.",
        )

    update_data = event_in.model_dump(exclude_unset=True)
    if "total_tickets" in update_data and update_data["total_tickets"] is not None:
        update_data["available_tickets"] = event.available_tickets + (
            update_data["total_tickets"] - event.total_tickets
        )

    for field, value in update_data.items():
        setattr(event, field, value)

    await db.flush()
    return event
