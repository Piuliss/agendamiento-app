from datetime import date, datetime, time, timedelta

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import Booking, BookingStatus, CalendarBlock, Complex, Court


def _combine(day: date, t: time) -> datetime:
    return datetime.combine(day, t)


def bookings_overlap(
    start_a: datetime, end_a: datetime, start_b: datetime, end_b: datetime
) -> bool:
    """True si los intervalos se solapan (borde que toca no cuenta como solape)."""
    return start_a < end_b and start_b < end_a


def _active_booking_statuses() -> tuple[BookingStatus, ...]:
    return (BookingStatus.PENDING, BookingStatus.CONFIRMED)


def get_busy_intervals_for_court(
    db: Session,
    complex_id: int,
    court_id: int,
    day_start: datetime,
    day_end: datetime,
) -> list[tuple[datetime, datetime]]:
    statuses = _active_booking_statuses()
    bookings = db.scalars(
        select(Booking).where(
            Booking.complex_id == complex_id,
            Booking.court_id == court_id,
            Booking.status.in_(statuses),
            Booking.starts_at < day_end,
            Booking.ends_at > day_start,
        )
    ).all()
    intervals = [(b.starts_at, b.ends_at) for b in bookings]

    blocks = db.scalars(
        select(CalendarBlock).where(
            CalendarBlock.complex_id == complex_id,
            CalendarBlock.booking_id.is_(None),
            CalendarBlock.starts_at < day_end,
            CalendarBlock.ends_at > day_start,
        )
    ).all()
    intervals.extend((bl.starts_at, bl.ends_at) for bl in blocks)
    return intervals


def slot_conflicts(
    slot_start: datetime,
    slot_end: datetime,
    busy: list[tuple[datetime, datetime]],
) -> bool:
    for b_start, b_end in busy:
        if bookings_overlap(slot_start, slot_end, b_start, b_end):
            return True
    return False


def generate_day_slots(
    target_day: date,
    hours_start: time,
    hours_end: time,
    duration_minutes: int,
) -> list[tuple[datetime, datetime]]:
    if hours_start >= hours_end:
        return []
    start_dt = _combine(target_day, hours_start)
    end_dt = _combine(target_day, hours_end)
    delta = timedelta(minutes=duration_minutes)
    slots: list[tuple[datetime, datetime]] = []
    cursor = start_dt
    while cursor + delta <= end_dt:
        slots.append((cursor, cursor + delta))
        cursor += delta
    return slots


def available_slots_for_court(
    db: Session,
    complex_: Complex,
    court: Court,
    target_day: date,
    now: datetime | None = None,
) -> list[tuple[datetime, datetime]]:
    settings = get_settings()
    day_start = _combine(target_day, time.min)
    day_end = _combine(target_day, time.max)
    busy = get_busy_intervals_for_court(db, complex_.id, court.id, day_start, day_end)
    all_slots = generate_day_slots(
        target_day, complex_.hours_start, complex_.hours_end, settings.slot_duration_minutes
    )
    now = now or datetime.utcnow()
    available: list[tuple[datetime, datetime]] = []
    for s_start, s_end in all_slots:
        if s_start < now:
            continue
        if not slot_conflicts(s_start, s_end, busy):
            available.append((s_start, s_end))
    return available


def assert_booking_allowed(
    db: Session,
    complex_: Complex,
    court_id: int,
    starts_at: datetime,
    ends_at: datetime,
    exclude_booking_id: int | None = None,
    *,
    for_public: bool = True,
) -> None:
    from app.services.complex_rules import is_court_published
    from app.services.schedule import assert_in_public_window, assert_in_teacher_window

    if starts_at >= ends_at:
        raise ValueError("Horario inválido")
    court = db.get(Court, court_id)
    if not court or court.complex_id != complex_.id or not court.active:
        raise ValueError("Cancha no disponible")
    if for_public and not is_court_published(db, complex_, court_id):
        raise ValueError("Cancha no publicada")
    day = starts_at.date()
    if starts_at.time() < complex_.hours_start or ends_at.time() > complex_.hours_end:
        raise ValueError("Fuera del horario de atención")
    if for_public:
        assert_in_public_window(complex_, starts_at, ends_at)
    else:
        assert_in_teacher_window(complex_, starts_at, ends_at)
    busy = get_busy_intervals_for_court(
        db,
        complex_.id,
        court_id,
        _combine(day, time.min),
        _combine(day, time.max),
    )
    for b_start, b_end in busy:
        if exclude_booking_id:
            booking = db.scalar(
                select(Booking).where(
                    Booking.id == exclude_booking_id,
                    Booking.starts_at == b_start,
                    Booking.ends_at == b_end,
                )
            )
            if booking:
                continue
        if bookings_overlap(starts_at, ends_at, b_start, b_end):
            raise ValueError("El horario ya no está disponible")
