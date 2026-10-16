"""Calendario tentativo por reserva; WhatsApp obligatorio solo en flujo público."""

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Booking, BookingKind, BookingStatus, CalendarBlock, Complex, Court
from app.services.google_calendar import complex_has_google, create_tentative_event, update_event_status
from app.services.whatsapp import build_whatsapp_message, whatsapp_url


@dataclass
class BookingOutputs:
    whatsapp_url: str
    whatsapp_message: str
    calendar_mode: str
    calendar_tentative: bool


def _block_title(court_name: str, booking: Booking, tentative: bool) -> str:
    tag = "Pendiente" if tentative else "Confirmado"
    extra = f" ({booking.student_count} alumnos)" if booking.student_count else ""
    return f"[{tag}] {court_name} — {booking.customer_name}{extra}"


def create_local_calendar_event(
    db: Session,
    complex_: Complex,
    booking: Booking,
    court_name: str,
    tentative: bool,
) -> CalendarBlock:
    block = CalendarBlock(
        complex_id=complex_.id,
        booking_id=booking.id,
        starts_at=booking.starts_at,
        ends_at=booking.ends_at,
        title=_block_title(court_name, booking, tentative),
        source="booking",
        is_tentative=tentative,
    )
    db.add(block)
    db.flush()
    booking.calendar_tentative = tentative
    return block


async def attach_booking_calendar(
    db: Session,
    complex_: Complex,
    booking: Booking,
    court: Court,
) -> str:
    court_name = court.name
    tentative = booking.status == BookingStatus.PENDING
    calendar_mode = "local"
    if complex_has_google(complex_):
        event_id = await create_tentative_event(
            complex_,
            booking,
            court_name,
            _block_title(court_name, booking, tentative),
        )
        if event_id:
            booking.google_event_id = event_id
            booking.calendar_tentative = tentative
            calendar_mode = "google"
        else:
            create_local_calendar_event(db, complex_, booking, court_name, tentative)
    else:
        create_local_calendar_event(db, complex_, booking, court_name, tentative)
    db.commit()
    return calendar_mode


async def ensure_booking_outputs(
    db: Session,
    complex_: Complex,
    booking: Booking,
    court: Court,
) -> BookingOutputs:
    calendar_mode = await attach_booking_calendar(db, complex_, booking, court)
    tentative = booking.calendar_tentative
    if booking.kind == BookingKind.TEACHER:
        return BookingOutputs(
            whatsapp_url="",
            whatsapp_message="",
            calendar_mode=calendar_mode,
            calendar_tentative=tentative,
        )
    msg = build_whatsapp_message(complex_, court, booking)
    wa = whatsapp_url(complex_.whatsapp_number, msg)
    if not wa:
        raise ValueError(
            "El complejo no tiene número de WhatsApp configurado; no se puede completar la reserva."
        )
    return BookingOutputs(
        whatsapp_url=wa,
        whatsapp_message=msg,
        calendar_mode=calendar_mode,
        calendar_tentative=tentative,
    )


async def sync_calendar_after_admin_action(
    db: Session,
    complex_: Complex,
    booking: Booking,
    court_name: str,
) -> None:
    if booking.status == BookingStatus.CONFIRMED:
        booking.calendar_tentative = False
        if booking.google_event_id:
            await update_event_status(complex_, booking.google_event_id, confirmed=True)
        block = db.scalar(select(CalendarBlock).where(CalendarBlock.booking_id == booking.id))
        if block:
            block.is_tentative = False
            block.title = _block_title(court_name, booking, False)
    elif booking.status == BookingStatus.REJECTED:
        booking.calendar_tentative = False
        if booking.google_event_id:
            await update_event_status(complex_, booking.google_event_id, confirmed=False)
        block = db.scalar(select(CalendarBlock).where(CalendarBlock.booking_id == booking.id))
        if block:
            db.delete(block)
    db.commit()
