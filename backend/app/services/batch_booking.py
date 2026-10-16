from sqlalchemy.orm import Session

from app.models import Booking, BookingKind, BookingStatus, Complex, Court, Teacher
from app.services.availability import assert_booking_allowed
from app.services.booking_outputs import attach_booking_calendar
from app.services.whatsapp import build_cart_whatsapp_message, whatsapp_url


async def create_public_cart(
    db: Session,
    complex_: Complex,
    items: list[tuple[int, object, object]],
    contact: dict[str, str],
) -> tuple[list[Booking], str, str]:
    """items: (court_id, starts_at, ends_at)"""
    created: list[tuple[Court, Booking]] = []
    bookings: list[Booking] = []
    for court_id, starts_at, ends_at in items:
        assert_booking_allowed(
            db, complex_, court_id, starts_at, ends_at, for_public=True
        )
        court = db.get(Court, court_id)
        if not court:
            raise ValueError("Cancha no encontrada")
        booking = Booking(
            complex_id=complex_.id,
            court_id=court_id,
            starts_at=starts_at,
            ends_at=ends_at,
            customer_name=contact["name"],
            customer_phone=contact["phone"],
            customer_email=contact.get("email", ""),
            customer_notes=contact.get("notes", ""),
            kind=BookingKind.PUBLIC,
            status=BookingStatus.PENDING,
            calendar_tentative=True,
        )
        db.add(booking)
        db.flush()
        await attach_booking_calendar(db, complex_, booking, court)
        created.append((court, booking))
        bookings.append(booking)
    db.commit()
    msg = build_cart_whatsapp_message(
        complex_,
        contact["name"],
        contact["phone"],
        created,
        contact.get("email", ""),
        contact.get("notes", ""),
    )
    wa = whatsapp_url(complex_.whatsapp_number, msg)
    if not wa:
        raise ValueError("WhatsApp del complejo no configurado")
    return bookings, wa, msg


async def create_teacher_booking(
    db: Session,
    complex_: Complex,
    teacher: Teacher,
    court_id: int,
    starts_at,
    ends_at,
    student_count: int,
) -> Booking:
    assert_booking_allowed(
        db, complex_, court_id, starts_at, ends_at, for_public=False
    )
    court = db.get(Court, court_id)
    if not court:
        raise ValueError("Cancha no encontrada")
    booking = Booking(
        complex_id=complex_.id,
        court_id=court_id,
        starts_at=starts_at,
        ends_at=ends_at,
        customer_name=teacher.full_name,
        customer_phone="",
        customer_notes=f"Profesor: {teacher.username}",
        kind=BookingKind.TEACHER,
        student_count=student_count,
        teacher_id=teacher.id,
        status=BookingStatus.CONFIRMED,
        calendar_tentative=False,
    )
    db.add(booking)
    db.commit()
    db.refresh(booking)
    await attach_booking_calendar(db, complex_, booking, court)
    return booking
