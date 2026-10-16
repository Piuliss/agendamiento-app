from datetime import datetime, time, timedelta

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import Booking, BookingStatus, CalendarBlock, Complex, Court, Organization
from app.services.booking_outputs import ensure_booking_outputs


@pytest.fixture
def session_bundle():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    org = Organization(name="Org")
    session.add(org)
    session.flush()
    complex_ = Complex(
        organization_id=org.id,
        name="Complejo",
        slug="c1",
        whatsapp_number="595981111111",
        hours_start=time(8, 0),
        hours_end=time(22, 0),
    )
    session.add(complex_)
    session.flush()
    court = Court(complex_id=complex_.id, name="Cancha 1", active=True)
    session.add(court)
    session.commit()
    return session, complex_, court


@pytest.mark.asyncio
async def test_booking_always_creates_local_calendar_and_whatsapp(session_bundle):
    session, complex_, court = session_bundle
    start = datetime.utcnow().replace(hour=15, minute=0, second=0, microsecond=0) + timedelta(days=2)
    booking = Booking(
        complex_id=complex_.id,
        court_id=court.id,
        starts_at=start,
        ends_at=start + timedelta(hours=1),
        customer_name="Juan Pérez",
        customer_phone="0981123456",
        customer_email="juan@ejemplo.com",
        status=BookingStatus.PENDING,
    )
    session.add(booking)
    session.commit()
    session.refresh(booking)

    outputs = await ensure_booking_outputs(session, complex_, booking, court)
    assert outputs.calendar_tentative is True
    assert outputs.calendar_mode == "local"
    assert outputs.whatsapp_url.startswith("https://wa.me/")
    assert "Juan Pérez" in outputs.whatsapp_message

    block = session.scalar(select(CalendarBlock).where(CalendarBlock.booking_id == booking.id))
    assert block is not None
    assert block.is_tentative is True
    assert booking.customer_phone == "0981123456"
