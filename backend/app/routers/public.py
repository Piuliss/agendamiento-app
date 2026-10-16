from datetime import date, datetime, time, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models import Booking, BookingStatus, Complex, Court
from app.schemas import (
    BusyIntervalOut,
    CalendarDayOut,
    CartBookingCreate,
    CartBookingOut,
    ComplexPublicOut,
    ComplexScheduleOut,
    CourtOut,
)
from app.services.availability import get_busy_intervals_for_court
from app.services.batch_booking import create_public_cart
from app.services.complex_rules import published_courts

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
        bookings, wa, msg = await create_public_cart(db, complex_, items, contact)
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
