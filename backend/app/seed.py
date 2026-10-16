from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import hash_password
from app.models import Booking, BookingKind, BookingStatus, Complex, Court, Organization, Teacher


def ensure_demo_data(db: Session) -> Complex:
    existing = db.scalar(select(Complex).where(Complex.slug == "demo"))
    if existing:
        _upgrade_demo_complex(db, existing)
        _ensure_teacher(db, existing)
        _ensure_demo_calendar_bookings(db, existing)
        return existing
    org = Organization(name="Asociación Demo")
    db.add(org)
    db.flush()
    complex_ = Complex(
        organization_id=org.id,
        name="Complejo Pádel Centro",
        slug="demo",
        whatsapp_number="595981234567",
        contact_email="reservas@ejemplo.com",
        public_hours_start=__import__("datetime").time(17, 0),
        published_courts_count=3,
    )
    db.add(complex_)
    db.flush()
    for i, name in enumerate(("Cancha 1", "Cancha 2", "Cancha 3"), start=1):
        db.add(Court(complex_id=complex_.id, name=name, active=True, sort_order=i))
    db.commit()
    db.refresh(complex_)
    _ensure_teacher(db, complex_)
    _ensure_demo_calendar_bookings(db, complex_)
    return complex_


def _upgrade_demo_complex(db: Session, complex_: Complex) -> None:
    if complex_.published_courts_count < 3:
        complex_.published_courts_count = 3
    if complex_.public_hours_start.hour != 17:
        complex_.public_hours_start = __import__("datetime").time(17, 0)
    names = ("Cancha 1", "Cancha 2", "Cancha 3")
    for i, name in enumerate(names, start=1):
        court = db.scalar(
            select(Court).where(Court.complex_id == complex_.id, Court.name == name)
        )
        if not court:
            db.add(Court(complex_id=complex_.id, name=name, active=True, sort_order=i))
    db.commit()


def _ensure_demo_calendar_bookings(db: Session, complex_: Complex) -> None:
    """Tres reservas simultáneas (referencia visual colores)."""
    courts = db.scalars(
        select(Court).where(Court.complex_id == complex_.id).order_by(Court.sort_order, Court.id)
    ).all()
    if len(courts) < 2:
        return
    start = datetime(2026, 10, 20, 16, 0, 0)
    end = datetime(2026, 10, 20, 17, 30, 0)
    demos = [
        ("Escena Ríos", courts[0].id),
        ("Grupo Martínez", courts[1].id if len(courts) > 1 else courts[0].id),
        ("Clase avanzada", courts[2].id if len(courts) > 2 else courts[0].id),
    ]
    for customer, court_id in demos:
        exists = db.scalar(
            select(Booking).where(
                Booking.complex_id == complex_.id,
                Booking.court_id == court_id,
                Booking.starts_at == start,
                Booking.customer_name == customer,
            )
        )
        if exists:
            continue
        db.add(
            Booking(
                complex_id=complex_.id,
                court_id=court_id,
                starts_at=start,
                ends_at=end,
                customer_name=customer,
                customer_phone="0981000000",
                kind=BookingKind.PUBLIC,
                status=BookingStatus.CONFIRMED,
                calendar_tentative=False,
            )
        )
    db.commit()


def _ensure_teacher(db: Session, complex_: Complex) -> None:
    t = db.scalar(
        select(Teacher).where(Teacher.complex_id == complex_.id, Teacher.username == "profesor")
    )
    if t:
        return
    db.add(
        Teacher(
            complex_id=complex_.id,
            username="profesor",
            password_hash=hash_password("profesor"),
            full_name="Profesor Demo",
            active=True,
        )
    )
    db.commit()
