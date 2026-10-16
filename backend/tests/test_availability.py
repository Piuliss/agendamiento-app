from datetime import date, datetime, time, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.database import Base
from app.models import Booking, BookingStatus, Complex, Court, Organization
from app.services.availability import (
    assert_booking_allowed,
    available_slots_for_court,
    bookings_overlap,
    generate_day_slots,
    slot_conflicts,
)


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    org = Organization(name="Test Org")
    session.add(org)
    session.flush()
    complex_ = Complex(
        organization_id=org.id,
        name="Test",
        slug="test",
        hours_start=time(9, 0),
        hours_end=time(12, 0),
    )
    session.add(complex_)
    session.flush()
    court = Court(complex_id=complex_.id, name="C1", active=True)
    session.add(court)
    session.commit()
    yield session, complex_, court
    session.close()


def test_bookings_overlap():
    a0 = datetime(2026, 10, 16, 10, 0)
    a1 = datetime(2026, 10, 16, 11, 0)
    assert bookings_overlap(a0, a1, datetime(2026, 10, 16, 10, 30), datetime(2026, 10, 16, 11, 30))
    assert not bookings_overlap(a0, a1, a1, datetime(2026, 10, 16, 12, 0))


def test_generate_day_slots():
    slots = generate_day_slots(date(2026, 10, 16), time(9, 0), time(12, 0), 60)
    assert len(slots) == 3
    assert slots[0][0].hour == 9


def test_available_slots_exclude_pending_booking(db_session):
    session, complex_, court = db_session
    day = date(2026, 12, 1)
    start = datetime.combine(day, time(10, 0))
    session.add(
        Booking(
            complex_id=complex_.id,
            court_id=court.id,
            starts_at=start,
            ends_at=start + timedelta(hours=1),
            customer_name="A",
            customer_phone="123",
            status=BookingStatus.PENDING,
        )
    )
    session.commit()
    slots = available_slots_for_court(
        session, complex_, court, day, now=datetime.combine(day, time(8, 0))
    )
    assert all(not (s[0].hour == 10) for s in slots)
    assert any(s[0].hour == 9 for s in slots)


def test_assert_booking_allowed_rejects_overlap(db_session):
    session, complex_, court = db_session
    day = date(2026, 12, 2)
    start = datetime.combine(day, time(9, 0))
    session.add(
        Booking(
            complex_id=complex_.id,
            court_id=court.id,
            starts_at=start,
            ends_at=start + timedelta(hours=1),
            customer_name="B",
            customer_phone="456",
            status=BookingStatus.CONFIRMED,
        )
    )
    session.commit()
    with pytest.raises(ValueError, match="disponible"):
        assert_booking_allowed(
            session,
            complex_,
            court.id,
            start,
            start + timedelta(hours=1),
        )


def test_slot_conflicts():
    busy = [(datetime(2026, 10, 16, 10, 0), datetime(2026, 10, 16, 11, 0))]
    assert slot_conflicts(datetime(2026, 10, 16, 10, 30), datetime(2026, 10, 16, 11, 30), busy)
    assert not slot_conflicts(datetime(2026, 10, 16, 11, 0), datetime(2026, 10, 16, 12, 0), busy)
