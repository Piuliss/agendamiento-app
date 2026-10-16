"""Dos sesiones compiten por el mismo turno: solo una obtiene el bloqueo."""

import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, time
from pathlib import Path

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import Complex, Court, Organization
from app.services.holds import acquire_hold


def _fixture():
    db_path = Path(tempfile.mkstemp(suffix=".sqlite")[1])
    engine = create_engine(
        f"sqlite:///{db_path}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    org = Organization(name="Race Org")
    db.add(org)
    db.flush()
    complex_ = Complex(
        organization_id=org.id,
        name="Race",
        slug="race",
        hours_start=time(8, 0),
        hours_end=time(22, 0),
        public_hours_start=time(8, 0),
        published_courts_count=1,
        whatsapp_number="595981000000",
    )
    db.add(complex_)
    db.flush()
    court = Court(complex_id=complex_.id, name="C1", active=True)
    db.add(court)
    db.commit()
    cid = complex_.id
    court_id = court.id
    db.close()
    return engine, SessionLocal, cid, court_id


def test_race_two_holds_same_slot_only_one_wins():
    engine, SessionLocal, complex_id, court_id = _fixture()
    starts = datetime(2026, 10, 20, 18, 0)
    ends = datetime(2026, 10, 20, 20, 0)

    def attempt(session_id: str) -> bool:
        db = SessionLocal()
        try:
            complex_ = db.get(Complex, complex_id)
            acquire_hold(db, complex_, court_id, starts, ends, session_id)
            return True
        except ValueError:
            db.rollback()
            return False
        finally:
            db.close()

    results: list[bool] = []
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [
            pool.submit(attempt, "session-alpha"),
            pool.submit(attempt, "session-beta"),
        ]
        for f in as_completed(futures):
            results.append(f.result())

    assert sorted(results) == [False, True]
    assert results.count(True) == 1

    db = SessionLocal()
    from app.models import SlotHold

    holds = db.scalars(select(SlotHold)).all()
    assert len(holds) == 1
    db.close()
    engine.dispose()
