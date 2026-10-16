"""Cada reserva genera siempre: (1) evento calendario tentativo y (2) enlace WhatsApp."""

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Booking, BookingStatus, CalendarBlock, Complex, Court
from app.services.google_calendar import complex_has_google, create_tentative_event, update_event_status
from app.services.whatsapp import build_whatsapp_message, whatsapp_url


@dataclass
class BookingOutputs:
    whatsapp_url: str
    whatsapp_message: str
    calendar_mode: str  # google | local
    calendar_tentative: bool


def _local_block_title(court_name: str, booking: Booking) -> str:
    return f"[Pendiente] {court_name} — {booking.customer_name}"


def create_local_tentative_event(
    db: Session,
    complex_: Complex,
    booking: Booking,
    court_name: str,
) -> CalendarBlock:
    block = CalendarBlock(
        complex_id=complex_.id,
        booking_id=booking.id,
        starts_at=booking.starts_at,
        ends_at=booking.ends_at,
        title=_local_block_title(court_name, booking),
        source="booking_pending",
        is_tentative=True,
    )
    db.add(block)
    db.flush()
    booking.calendar_tentative = True
    return block


async def ensure_booking_outputs(
    db: Session,
    complex_: Complex,
    booking: Booking,
    court: Court,
) -> BookingOutputs:
    court_name = court.name
    msg = build_whatsapp_message(complex_, court, booking)
    wa = whatsapp_url(complex_.whatsapp_number, msg)
    if not wa:
        raise ValueError(
            "El complejo no tiene número de WhatsApp configurado; no se puede completar la reserva."
        )

    calendar_mode = "local"
    if complex_has_google(complex_):
        event_id = await create_tentative_event(
            complex_,
            booking,
            court_name,
            _local_block_title(court_name, booking),
        )
        if event_id:
            booking.google_event_id = event_id
            booking.calendar_tentative = True
            calendar_mode = "google"
        else:
            create_local_tentative_event(db, complex_, booking, court_name)
    else:
        create_local_tentative_event(db, complex_, booking, court_name)

    db.commit()
    return BookingOutputs(
        whatsapp_url=wa,
        whatsapp_message=msg,
        calendar_mode=calendar_mode,
        calendar_tentative=True,
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
            block.title = f"[Confirmado] {court_name} — {booking.customer_name}"
    elif booking.status == BookingStatus.REJECTED:
        booking.calendar_tentative = False
        if booking.google_event_id:
            await update_event_status(complex_, booking.google_event_id, confirmed=False)
        block = db.scalar(select(CalendarBlock).where(CalendarBlock.booking_id == booking.id))
        if block:
            db.delete(block)
    db.commit()
