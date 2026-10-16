from datetime import datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Complex, SlotHold
from app.services.availability import assert_booking_allowed

HOLD_SECONDS = 60


def _now() -> datetime:
    return datetime.utcnow()


def purge_expired_holds(db: Session) -> None:
    db.execute(delete(SlotHold).where(SlotHold.expires_at <= _now()))


def _active_hold_blocks(
    db: Session,
    complex_id: int,
    court_id: int,
    starts_at: datetime,
    ends_at: datetime,
    *,
    ignore_session_id: str | None = None,
) -> list[SlotHold]:
    purge_expired_holds(db)
    holds = db.scalars(
        select(SlotHold).where(
            SlotHold.complex_id == complex_id,
            SlotHold.court_id == court_id,
            SlotHold.starts_at == starts_at,
            SlotHold.ends_at == ends_at,
            SlotHold.expires_at > _now(),
        )
    ).all()
    if ignore_session_id:
        return [h for h in holds if h.session_id != ignore_session_id]
    return list(holds)


def assert_no_foreign_hold(
    db: Session,
    complex_id: int,
    court_id: int,
    starts_at: datetime,
    ends_at: datetime,
    session_id: str | None,
) -> None:
    foreign = _active_hold_blocks(
        db, complex_id, court_id, starts_at, ends_at, ignore_session_id=session_id
    )
    if foreign:
        raise ValueError("Turno reservado temporalmente por otro usuario")


def acquire_hold(
    db: Session,
    complex_: Complex,
    court_id: int,
    starts_at: datetime,
    ends_at: datetime,
    session_id: str,
) -> SlotHold:
    """Bloquea cancha+intervalo 60s para la sesión (renovable)."""
    hold_id: int | None = None
    try:
        purge_expired_holds(db)
        assert_booking_allowed(
            db,
            complex_,
            court_id,
            starts_at,
            ends_at,
            for_public=True,
            holding_session_id=session_id,
        )
        assert_no_foreign_hold(db, complex_.id, court_id, starts_at, ends_at, session_id)

        db.execute(
            delete(SlotHold).where(
                SlotHold.session_id == session_id,
                SlotHold.starts_at == starts_at,
                SlotHold.ends_at == ends_at,
                SlotHold.court_id != court_id,
            )
        )

        row = db.scalar(
            select(SlotHold).where(
                SlotHold.court_id == court_id,
                SlotHold.starts_at == starts_at,
                SlotHold.ends_at == ends_at,
            )
        )
        expires = _now() + timedelta(seconds=HOLD_SECONDS)
        if row:
            if row.session_id != session_id and row.expires_at > _now():
                raise ValueError("Turno reservado temporalmente por otro usuario")
            row.session_id = session_id
            row.complex_id = complex_.id
            row.expires_at = expires
            hold = row
        else:
            hold = SlotHold(
                complex_id=complex_.id,
                court_id=court_id,
                starts_at=starts_at,
                ends_at=ends_at,
                session_id=session_id,
                expires_at=expires,
            )
            db.add(hold)
        db.flush()
        hold_id = hold.id
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ValueError("Turno reservado temporalmente por otro usuario")
    except ValueError:
        db.rollback()
        raise

    hold = db.get(SlotHold, hold_id)
    if not hold:
        raise ValueError("No se pudo registrar el bloqueo")
    return hold


def release_session_holds(db: Session, session_id: str, *, commit: bool = True) -> None:
    db.execute(delete(SlotHold).where(SlotHold.session_id == session_id))
    if commit:
        db.commit()


def release_hold_interval(
    db: Session,
    court_id: int,
    starts_at: datetime,
    ends_at: datetime,
    session_id: str,
) -> None:
    db.execute(
        delete(SlotHold).where(
            SlotHold.session_id == session_id,
            SlotHold.court_id == court_id,
            SlotHold.starts_at == starts_at,
            SlotHold.ends_at == ends_at,
        )
    )
    db.commit()
