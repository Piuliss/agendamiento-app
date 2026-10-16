from datetime import datetime, time, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import Complex, Court, Organization
from app.services.availability import assert_booking_allowed
from app.services.schedule import assert_in_public_window, assert_in_teacher_window


@pytest.fixture
def bundle():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    org = Organization(name="O")
    session.add(org)
    session.flush()
    complex_ = Complex(
        organization_id=org.id,
        name="C",
        slug="s",
        hours_start=time(8, 0),
        public_hours_start=time(17, 0),
        hours_end=time(22, 0),
        published_courts_count=1,
    )
    session.add(complex_)
    session.flush()
    court = Court(complex_id=complex_.id, name="1", active=True, sort_order=1)
    session.add(court)
    session.commit()
    return session, complex_, court


def test_public_vs_teacher_windows(bundle):
    _, complex_, _ = bundle
    day = datetime(2026, 10, 20, 10, 0)
    assert_in_teacher_window(complex_, day, day + timedelta(hours=1))
    with pytest.raises(ValueError):
        assert_in_public_window(complex_, day, day + timedelta(hours=1))
    evening = datetime(2026, 10, 20, 18, 0)
    assert_in_public_window(complex_, evening, evening + timedelta(hours=1))


def test_public_booking_rejects_morning(bundle):
    session, complex_, court = bundle
    start = datetime(2026, 10, 21, 10, 0)
    with pytest.raises(ValueError):
        assert_booking_allowed(session, complex_, court.id, start, start + timedelta(hours=1), for_public=True)
