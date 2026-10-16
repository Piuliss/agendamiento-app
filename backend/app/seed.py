from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import hash_password
from app.models import Complex, Court, Organization, Teacher


def ensure_demo_data(db: Session) -> Complex:
    existing = db.scalar(select(Complex).where(Complex.slug == "demo"))
    if existing:
        if existing.published_courts_count < 2:
            existing.published_courts_count = 2
            db.commit()
        _ensure_teacher(db, existing)
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
        published_courts_count=2,
    )
    db.add(complex_)
    db.flush()
    for i, name in enumerate(("Cancha 1", "Cancha 2"), start=1):
        db.add(Court(complex_id=complex_.id, name=name, active=True, sort_order=i))
    db.commit()
    db.refresh(complex_)
    _ensure_teacher(db, complex_)
    return complex_


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
