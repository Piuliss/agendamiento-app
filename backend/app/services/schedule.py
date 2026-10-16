from datetime import datetime, time

from app.models import Complex


def interval_within_window(starts_at: datetime, ends_at: datetime, win_start: time, win_end: time) -> bool:
    if win_start >= win_end:
        return False
    t0, t1 = starts_at.time(), ends_at.time()
    if starts_at.date() != ends_at.date():
        return False
    return t0 >= win_start and t1 <= win_end


def assert_in_public_window(complex_: Complex, starts_at: datetime, ends_at: datetime) -> None:
    win = complex_.public_hours_start, complex_.hours_end
    if not interval_within_window(starts_at, ends_at, *win):
        raise ValueError("El horario debe estar dentro del bloque público")


def assert_in_teacher_window(complex_: Complex, starts_at: datetime, ends_at: datetime) -> None:
    win = complex_.hours_start, complex_.public_hours_start
    if not interval_within_window(starts_at, ends_at, *win):
        raise ValueError("El horario debe estar dentro del bloque de profesores")
