from datetime import date, datetime, time, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models import Booking, BookingStatus, Complex, Court
from app.schemas import (
    BusyIntervalOut,
    CalendarBookingEventOut,
    CalendarBusyOut,
    CalendarDayOut,
    CalendarEventsOut,
    CartBookingCreate,
    CartBookingOut,
    ComplexPublicOut,
    ComplexScheduleOut,
    CourtAvailabilityOut,
    CourtOut,
    SlotHoldCreate,
    SlotHoldOut,
)
from app.services.availability import fully_busy_intervals_for_complex, is_booking_allowed
from app.services.batch_booking import create_public_cart
from app.services.complex_rules import published_courts
from app.services.holds import (
    HOLD_SECONDS,
    acquire_hold,
    release_hold_interval,
    release_session_holds,
)

router = APIRouter(prefix="/api/public", tags=["public"])


def _complex_schedule(complex_: Complex) -> ComplexScheduleOut:
    return ComplexScheduleOut(
        hours_start=complex_.hours_start,
        hours_end=complex_.hours_end,
        public_hours_start=complex_.public_hours_start,
        teacher_hours_start=complex_.hours_start,
        teacher_hours_end=complex_.public_hours_start,
        public_hours_start_field=complex_.public_hours_start,
    )


@router.get("/complexes/{slug}", response_model=ComplexPublicOut)
def get_complex_public(slug: str, db: Session = Depends(get_db)):
    complex_ = db.scalar(select(Complex).where(Complex.slug == slug))
    if not complex_:
        raise HTTPException(status_code=404, detail="Complejo no encontrado")
    courts = published_courts(db, complex_)
    return ComplexPublicOut(
        id=complex_.id,
        name=complex_.name,
        slug=complex_.slug,
        whatsapp_number=complex_.whatsapp_number,
        hours_start=complex_.hours_start,
        hours_end=complex_.hours_end,
        public_hours_start=complex_.public_hours_start,
        schedule=_complex_schedule(complex_),
        courts=[CourtOut.model_validate(c) for c in courts],
    )


@router.get("/complexes/{slug}/calendar-events", response_model=CalendarEventsOut)
def get_calendar_events(
    slug: str,
    from_date: date = Query(..., alias="from"),
    days: int = Query(14, ge=1, le=31),
    db: Session = Depends(get_db),
):
    complex_ = db.scalar(select(Complex).where(Complex.slug == slug))
    if not complex_:
        raise HTTPException(status_code=404, detail="Complejo no encontrado")
    court_ids = [c.id for c in published_courts(db, complex_)]
    if not court_ids:
        return CalendarEventsOut(events=[])
    end_bound = from_date + timedelta(days=days)
    rows = db.execute(
        select(Booking, Court.name)
        .join(Court, Booking.court_id == Court.id)
        .where(
            Booking.complex_id == complex_.id,
            Booking.court_id.in_(court_ids),
            Booking.status.in_((BookingStatus.PENDING, BookingStatus.CONFIRMED)),
            Booking.starts_at < datetime.combine(end_bound, time.max),
            Booking.ends_at > datetime.combine(from_date, time.min),
        )
        .order_by(Booking.starts_at)
    ).all()
    events: list[CalendarBookingEventOut] = []
    for booking, court_name in rows:
        title = booking.customer_name or "Reserva"
        events.append(
            CalendarBookingEventOut(
                id=booking.id,
                court_id=booking.court_id,
                court_name=court_name,
                starts_at=booking.starts_at,
                ends_at=booking.ends_at,
                status=booking.status.value,
                label=f"{court_name} · {title}",
            )
        )
    return CalendarEventsOut(events=events)


@router.get("/complexes/{slug}/calendar-busy", response_model=CalendarBusyOut)
def get_calendar_busy_aggregate(
    slug: str,
    from_date: date = Query(..., alias="from"),
    days: int = Query(14, ge=1, le=31),
    db: Session = Depends(get_db),
):
    complex_ = db.scalar(select(Complex).where(Complex.slug == slug))
    if not complex_:
        raise HTTPException(status_code=404, detail="Complejo no encontrado")
    busy: list[BusyIntervalOut] = []
    for i in range(days):
        d = from_date + timedelta(days=i)
        for s_start, s_end in fully_busy_intervals_for_complex(db, complex_, d):
            busy.append(
                BusyIntervalOut(
                    starts_at=s_start,
                    ends_at=s_end,
                    status="unavailable",
                    kind="aggregate",
                )
            )
    return CalendarBusyOut(busy=busy)


@router.get("/complexes/{slug}/courts-availability", response_model=list[CourtAvailabilityOut])
def courts_availability(
    slug: str,
    starts_at: datetime = Query(...),
    ends_at: datetime = Query(...),
    session_id: str | None = Query(default=None, max_length=64),
    db: Session = Depends(get_db),
):
    complex_ = db.scalar(select(Complex).where(Complex.slug == slug))
    if not complex_:
        raise HTTPException(status_code=404, detail="Complejo no encontrado")
    courts = published_courts(db, complex_)
    result: list[CourtAvailabilityOut] = []
    for court in courts:
        ok = is_booking_allowed(
            db,
            complex_,
            court.id,
            starts_at,
            ends_at,
            for_public=True,
            holding_session_id=session_id,
        )
        result.append(
            CourtAvailabilityOut(court_id=court.id, name=court.name, available=ok)
        )
    return result


@router.post("/complexes/{slug}/holds", response_model=SlotHoldOut)
def create_slot_hold(slug: str, body: SlotHoldCreate, db: Session = Depends(get_db)):
    complex_ = db.scalar(select(Complex).where(Complex.slug == slug))
    if not complex_:
        raise HTTPException(status_code=404, detail="Complejo no encontrado")
    try:
        hold = acquire_hold(
            db,
            complex_,
            body.court_id,
            body.starts_at,
            body.ends_at,
            body.session_id.strip(),
        )
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    return SlotHoldOut(
        court_id=hold.court_id,
        starts_at=hold.starts_at,
        ends_at=hold.ends_at,
        session_id=hold.session_id,
        expires_at=hold.expires_at,
        ttl_seconds=HOLD_SECONDS,
    )


@router.delete("/complexes/{slug}/holds", status_code=204)
def delete_slot_holds(
    slug: str,
    session_id: str = Query(..., min_length=8, max_length=64),
    court_id: int | None = Query(default=None),
    starts_at: datetime | None = Query(default=None),
    ends_at: datetime | None = Query(default=None),
    db: Session = Depends(get_db),
):
    complex_ = db.scalar(select(Complex).where(Complex.slug == slug))
    if not complex_:
        raise HTTPException(status_code=404, detail="Complejo no encontrado")
    sid = session_id.strip()
    if court_id is not None and starts_at is not None and ends_at is not None:
        release_hold_interval(db, court_id, starts_at, ends_at, sid)
    else:
        release_session_holds(db, sid)
    return None


@router.get("/complexes/{slug}/calendar", response_model=list[CalendarDayOut])
def get_calendar_busy(
    slug: str,
    court_id: int = Query(...),
    from_date: date = Query(..., alias="from"),
    days: int = Query(7, ge=1, le=31),
    db: Session = Depends(get_db),
):
    complex_ = db.scalar(select(Complex).where(Complex.slug == slug))
    if not complex_:
        raise HTTPException(status_code=404, detail="Complejo no encontrado")
    court = db.get(Court, court_id)
    if not court or court.complex_id != complex_.id:
        raise HTTPException(status_code=404, detail="Cancha no encontrada")
    result: list[CalendarDayOut] = []
    for i in range(days):
        d = from_date + timedelta(days=i)
        day_start = datetime.combine(d, time.min)
        day_end = datetime.combine(d, time.max)
        bookings = db.scalars(
            select(Booking).where(
                Booking.complex_id == complex_.id,
                Booking.court_id == court_id,
                Booking.starts_at < day_end,
                Booking.ends_at > day_start,
                Booking.status.in_((BookingStatus.PENDING, BookingStatus.CONFIRMED)),
            )
        ).all()
        busy: list[BusyIntervalOut] = []
        for b in bookings:
            busy.append(
                BusyIntervalOut(
                    starts_at=b.starts_at,
                    ends_at=b.ends_at,
                    status=b.status.value,
                    kind=b.kind.value,
                )
            )
        result.append(CalendarDayOut(date=d, court_id=court_id, busy=busy))
    return result


@router.post("/complexes/{slug}/cart", response_model=CartBookingOut)
async def create_cart(slug: str, body: CartBookingCreate, db: Session = Depends(get_db)):
    complex_ = db.scalar(select(Complex).where(Complex.slug == slug))
    if not complex_:
        raise HTTPException(status_code=404, detail="Complejo no encontrado")
    items = [(it.court_id, it.starts_at, it.ends_at) for it in body.items]
    contact = {
        "name": body.customer_name.strip(),
        "phone": body.customer_phone.strip(),
        "email": (body.customer_email or "").strip(),
        "notes": (body.customer_notes or "").strip(),
    }
    try:
        session_id = (body.session_id or "").strip() or None
        bookings, wa, msg = await create_public_cart(
            db, complex_, items, contact, session_id=session_id
        )
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    return CartBookingOut(
        booking_ids=[b.id for b in bookings],
        items_count=len(bookings),
        whatsapp_url=wa,
        whatsapp_message=msg,
        message=(
            "Tus reservas quedaron pendientes de confirmación oficial. "
            "Cada turno tiene evento tentativo en calendario. Abrí WhatsApp para enviar el detalle."
        ),
    )
