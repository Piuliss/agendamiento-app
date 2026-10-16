from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.auth import (
    create_access_token,
    get_current_teacher_id,
    verify_password,
)
from app.database import get_db
from app.models import Complex, Teacher
from app.schemas import LoginRequest, TeacherBookingCreate, TokenOut
from app.services.batch_booking import create_teacher_booking
from app.services.complex_rules import published_courts

router = APIRouter(prefix="/api/teacher", tags=["teacher"])


@router.post("/login", response_model=TokenOut)
def teacher_login(body: LoginRequest, db: Session = Depends(get_db)):
    teacher = db.scalar(
        select(Teacher).where(Teacher.username == body.username, Teacher.active.is_(True))
    )
    if not teacher or not verify_password(body.password, teacher.password_hash):
        raise HTTPException(status_code=401, detail="Credenciales incorrectas")
    token = create_access_token(f"teacher:{teacher.id}", role="teacher")
    return TokenOut(access_token=token)


@router.get("/complex")
def teacher_complex(
    teacher_id: int = Depends(get_current_teacher_id),
    db: Session = Depends(get_db),
):
    teacher = db.get(Teacher, teacher_id)
    if not teacher:
        raise HTTPException(status_code=404, detail="Profesor no encontrado")
    complex_ = db.scalar(
        select(Complex).options(joinedload(Complex.courts)).where(Complex.id == teacher.complex_id)
    )
    if not complex_:
        raise HTTPException(status_code=404, detail="Complejo no encontrado")
    courts = published_courts(db, complex_) or list(complex_.courts)
    return {
        "complex": {
            "name": complex_.name,
            "slug": complex_.slug,
            "hours_start": complex_.hours_start,
            "hours_end": complex_.hours_end,
            "public_hours_start": complex_.public_hours_start,
        },
        "teacher": {"id": teacher.id, "full_name": teacher.full_name},
        "courts": [{"id": c.id, "name": c.name} for c in courts if c.active],
    }


@router.post("/bookings")
async def teacher_create_booking(
    body: TeacherBookingCreate,
    teacher_id: int = Depends(get_current_teacher_id),
    db: Session = Depends(get_db),
):
    teacher = db.get(Teacher, teacher_id)
    if not teacher:
        raise HTTPException(status_code=404, detail="Profesor no encontrado")
    complex_ = db.get(Complex, teacher.complex_id)
    if not complex_:
        raise HTTPException(status_code=404, detail="Complejo no encontrado")
    try:
        booking = await create_teacher_booking(
            db,
            complex_,
            teacher,
            body.court_id,
            body.starts_at,
            body.ends_at,
            body.student_count,
        )
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    return {
        "id": booking.id,
        "status": booking.status,
        "student_count": booking.student_count,
        "message": "Reserva de profesor confirmada.",
    }
