from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Complex, Court, Organization


def ensure_demo_data(db: Session) -> Complex:
    existing = db.scalar(select(Complex).where(Complex.slug == "demo"))
    if existing:
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
    )
    db.add(complex_)
    db.flush()
    for name in ("Cancha 1", "Cancha 2"):
        db.add(Court(complex_id=complex_.id, name=name, active=True))
    db.commit()
    db.refresh(complex_)
    return complex_
