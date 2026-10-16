from datetime import time

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Complex, Court


def published_courts(db: Session, complex_: Complex) -> list[Court]:
    courts = db.scalars(
        select(Court)
        .where(Court.complex_id == complex_.id, Court.active.is_(True))
        .order_by(Court.sort_order, Court.id)
    ).all()
    n = max(0, complex_.published_courts_count)
    return courts[:n]


def is_court_published(db: Session, complex_: Complex, court_id: int) -> bool:
    return any(c.id == court_id for c in published_courts(db, complex_))


def public_window(complex_: Complex) -> tuple[time, time]:
    return complex_.public_hours_start, complex_.hours_end


def teacher_window(complex_: Complex) -> tuple[time, time]:
    return complex_.hours_start, complex_.public_hours_start
