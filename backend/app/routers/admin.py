from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.auth import create_access_token, get_current_admin, verify_admin_password
from app.config import get_settings
from app.database import get_db
from app.auth import hash_password
from app.models import Booking, BookingStatus, Complex, Court, Teacher
from app.schemas import (
    BookingAction,
    BookingAdminOut,
    ComplexAdminOut,
    ComplexUpdate,
    CourtCreate,
    CourtOut,
    CourtUpdate,
    GoogleStatusOut,
    IntegrationStatusOut,
    LoginRequest,
    TeacherCreate,
    TeacherOut,
    TokenOut,
)
from app.services.booking_outputs import sync_calendar_after_admin_action
from app.services.google_calendar import (
    build_auth_url,
    complex_has_google,
    missing_google_env,
)

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.post("/login", response_model=TokenOut)
def login(body: LoginRequest):
    if not verify_admin_password(body.username, body.password):
        raise HTTPException(status_code=401, detail="Credenciales incorrectas")
    return TokenOut(access_token=create_access_token(body.username))


def _default_complex(db: Session) -> Complex:
    complex_ = db.scalar(select(Complex).order_by(Complex.id).limit(1))
    if not complex_:
        raise HTTPException(status_code=404, detail="No hay complejos configurados")
    return complex_


@router.get("/complex", response_model=ComplexAdminOut)
def get_complex_admin(db: Session = Depends(get_db), _: str = Depends(get_current_admin)):
    complex_ = db.scalar(
        select(Complex).options(joinedload(Complex.courts)).order_by(Complex.id).limit(1)
    )
    if not complex_:
        raise HTTPException(status_code=404, detail="No hay complejos")
    return ComplexAdminOut(
        id=complex_.id,
        name=complex_.name,
        slug=complex_.slug,
        whatsapp_number=complex_.whatsapp_number,
        contact_email=complex_.contact_email,
        hours_start=complex_.hours_start,
        hours_end=complex_.hours_end,
        public_hours_start=complex_.public_hours_start,
        published_courts_count=complex_.published_courts_count,
        google_calendar_id=complex_.google_calendar_id,
        google_connected=complex_has_google(complex_),
        courts=[CourtOut.model_validate(c) for c in complex_.courts],
    )


@router.patch("/complex", response_model=ComplexAdminOut)
def update_complex(
    body: ComplexUpdate,
    db: Session = Depends(get_db),
    _: str = Depends(get_current_admin),
):
    complex_ = _default_complex(db)
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(complex_, field, value)
    db.commit()
    db.refresh(complex_)
    return get_complex_admin(db=db, _=_)


@router.post("/courts", response_model=CourtOut)
def create_court(
    body: CourtCreate,
    db: Session = Depends(get_db),
    _: str = Depends(get_current_admin),
):
    complex_ = _default_complex(db)
    court = Court(complex_id=complex_.id, name=body.name.strip(), active=True)
    db.add(court)
    db.commit()
    db.refresh(court)
    return court


@router.patch("/courts/{court_id}", response_model=CourtOut)
def update_court(
    court_id: int,
    body: CourtUpdate,
    db: Session = Depends(get_db),
    _: str = Depends(get_current_admin),
):
    complex_ = _default_complex(db)
    court = db.get(Court, court_id)
    if not court or court.complex_id != complex_.id:
        raise HTTPException(status_code=404, detail="Cancha no encontrada")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(court, field, value)
    db.commit()
    db.refresh(court)
    return court


@router.get("/bookings", response_model=list[BookingAdminOut])
def list_bookings(
    from_date: date | None = Query(None, alias="from"),
    to_date: date | None = Query(None, alias="to"),
    db: Session = Depends(get_db),
    _: str = Depends(get_current_admin),
):
    complex_ = _default_complex(db)
    q = (
        select(Booking, Court.name)
        .join(Court, Booking.court_id == Court.id)
        .where(Booking.complex_id == complex_.id)
        .order_by(Booking.starts_at)
    )
    if from_date:
        q = q.where(Booking.starts_at >= from_date)
    if to_date:
        q = q.where(Booking.starts_at < to_date + timedelta(days=1))
    rows = db.execute(q).all()
    return [
        BookingAdminOut(
            id=b.id,
            court_id=b.court_id,
            court_name=court_name,
            starts_at=b.starts_at,
            ends_at=b.ends_at,
            customer_name=b.customer_name,
            customer_phone=b.customer_phone,
            customer_email=b.customer_email,
            customer_notes=b.customer_notes,
            kind=b.kind.value,
            student_count=b.student_count,
            status=b.status,
            calendar_tentative=b.calendar_tentative,
            notes=b.notes,
        )
        for b, court_name in rows
    ]


@router.post("/bookings/{booking_id}/action", response_model=BookingAdminOut)
async def booking_action(
    booking_id: int,
    body: BookingAction,
    db: Session = Depends(get_db),
    _: str = Depends(get_current_admin),
):
    complex_ = _default_complex(db)
    booking = db.get(Booking, booking_id)
    if not booking or booking.complex_id != complex_.id:
        raise HTTPException(status_code=404, detail="Reserva no encontrada")
    court = db.get(Court, booking.court_id)
    if body.action == "confirm":
        booking.status = BookingStatus.CONFIRMED
    else:
        booking.status = BookingStatus.REJECTED
    if body.notes:
        booking.notes = body.notes
    db.commit()
    await sync_calendar_after_admin_action(
        db, complex_, booking, court.name if court else "Cancha"
    )
    db.refresh(booking)
    return BookingAdminOut(
        id=booking.id,
        court_id=booking.court_id,
        court_name=court.name if court else "",
        starts_at=booking.starts_at,
        ends_at=booking.ends_at,
        customer_name=booking.customer_name,
        customer_phone=booking.customer_phone,
        customer_email=booking.customer_email,
        customer_notes=booking.customer_notes,
        kind=booking.kind.value,
        student_count=booking.student_count,
        status=booking.status,
        calendar_tentative=booking.calendar_tentative,
        notes=booking.notes,
    )


@router.get("/teachers", response_model=list[TeacherOut])
def list_teachers(db: Session = Depends(get_db), _: str = Depends(get_current_admin)):
    complex_ = _default_complex(db)
    rows = db.scalars(select(Teacher).where(Teacher.complex_id == complex_.id)).all()
    return rows


@router.post("/teachers", response_model=TeacherOut)
def create_teacher(
    body: TeacherCreate,
    db: Session = Depends(get_db),
    _: str = Depends(get_current_admin),
):
    complex_ = _default_complex(db)
    teacher = Teacher(
        complex_id=complex_.id,
        username=body.username.strip(),
        password_hash=hash_password(body.password),
        full_name=body.full_name.strip(),
        active=True,
    )
    db.add(teacher)
    db.commit()
    db.refresh(teacher)
    return teacher


@router.get("/integrations", response_model=IntegrationStatusOut)
def integrations_status(db: Session = Depends(get_db), _: str = Depends(get_current_admin)):
    settings = get_settings()
    complex_ = _default_complex(db)
    missing = missing_google_env()
    return IntegrationStatusOut(
        google=GoogleStatusOut(
            configured=settings.google_configured,
            connected=complex_has_google(complex_),
            missing_env=missing,
            auth_url=build_auth_url(f"complex:{complex_.id}") if settings.google_configured else None,
            calendar_mode="google" if complex_has_google(complex_) else "local",
        ),
        lumi={
            "configured": bool(settings.lumi_api_url and settings.lumi_api_token),
            "api_url_set": bool(settings.lumi_api_url),
            "note": "Adaptador stub; requiere spec de endpoints",
        },
    )
