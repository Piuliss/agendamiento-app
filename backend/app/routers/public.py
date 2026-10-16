from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.config import get_settings
from app.database import get_db
from app.models import Booking, BookingStatus, Complex, Court
from app.schemas import (
    AvailabilityDayOut,
    BookingCreate,
    BookingPublicOut,
    ComplexPublicOut,
    SlotOut,
)
from app.services.availability import assert_booking_allowed, available_slots_for_court
from app.services.booking_outputs import ensure_booking_outputs

router = APIRouter(prefix="/api/public", tags=["public"])


@router.get("/complexes/{slug}", response_model=ComplexPublicOut)
def get_complex_public(slug: str, db: Session = Depends(get_db)):
    complex_ = db.scalar(
        select(Complex)
        .options(joinedload(Complex.courts))
        .where(Complex.slug == slug)
    )
    if not complex_:
        raise HTTPException(status_code=404, detail="Complejo no encontrado")
    courts = [c for c in complex_.courts if c.active]
    data = ComplexPublicOut.model_validate(complex_)
    data.courts = courts
    return data


@router.get("/complexes/{slug}/availability", response_model=list[AvailabilityDayOut])
def get_availability(
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
    if not court or court.complex_id != complex_.id or not court.active:
        raise HTTPException(status_code=404, detail="Cancha no encontrada")
    result: list[AvailabilityDayOut] = []
    for i in range(days):
        d = from_date + timedelta(days=i)
        slots = available_slots_for_court(db, complex_, court, d)
        result.append(
            AvailabilityDayOut(
                date=d,
                court_id=court_id,
                slots=[SlotOut(starts_at=s, ends_at=e) for s, e in slots],
            )
        )
    return result


@router.post("/complexes/{slug}/bookings", response_model=BookingPublicOut)
async def create_booking(slug: str, body: BookingCreate, db: Session = Depends(get_db)):
    settings = get_settings()
    complex_ = db.scalar(select(Complex).where(Complex.slug == slug))
    if not complex_:
        raise HTTPException(status_code=404, detail="Complejo no encontrado")
    ends_at = body.starts_at + timedelta(minutes=settings.slot_duration_minutes)
    try:
        assert_booking_allowed(db, complex_, body.court_id, body.starts_at, ends_at)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    court = db.get(Court, body.court_id)
    if not court:
        raise HTTPException(status_code=404, detail="Cancha no encontrada")
    booking = Booking(
        complex_id=complex_.id,
        court_id=body.court_id,
        starts_at=body.starts_at,
        ends_at=ends_at,
        customer_name=body.customer_name.strip(),
        customer_phone=body.customer_phone.strip(),
        customer_email=(body.customer_email or "").strip(),
        customer_notes=(body.customer_notes or "").strip(),
        status=BookingStatus.PENDING,
        calendar_tentative=True,
    )
    db.add(booking)
    db.commit()
    db.refresh(booking)

    try:
        outputs = await ensure_booking_outputs(db, complex_, booking, court)
    except ValueError as e:
        db.delete(booking)
        db.commit()
        raise HTTPException(status_code=400, detail=str(e))

    return BookingPublicOut(
        id=booking.id,
        court_id=booking.court_id,
        court_name=court.name,
        starts_at=booking.starts_at,
        ends_at=booking.ends_at,
        customer_name=booking.customer_name,
        customer_phone=booking.customer_phone,
        customer_email=booking.customer_email,
        status=booking.status,
        whatsapp_url=outputs.whatsapp_url,
        whatsapp_message=outputs.whatsapp_message,
        calendar_mode=outputs.calendar_mode,
        calendar_tentative=outputs.calendar_tentative,
        message=(
            "Tu reserva quedó registrada como pendiente de confirmación oficial. "
            "Se creó un evento tentativo en el calendario y podés contactar al complejo por WhatsApp."
        ),
    )
