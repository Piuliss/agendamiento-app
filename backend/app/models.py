import enum
from datetime import datetime, time

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    Time,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class BookingStatus(str, enum.Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class BookingKind(str, enum.Enum):
    PUBLIC = "public"
    TEACHER = "teacher"


class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    complexes: Mapped[list["Complex"]] = relationship(back_populates="organization")


class Complex(Base):
    __tablename__ = "complexes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(80), unique=True, nullable=False, index=True)
    whatsapp_number: Mapped[str] = mapped_column(String(30), default="")
    contact_email: Mapped[str] = mapped_column(String(200), default="")
    hours_start: Mapped[time] = mapped_column(Time, default=time(8, 0))
    hours_end: Mapped[time] = mapped_column(Time, default=time(22, 0))
    public_hours_start: Mapped[time] = mapped_column(Time, default=time(17, 0))
    published_courts_count: Mapped[int] = mapped_column(Integer, default=1)
    google_calendar_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    google_refresh_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    google_access_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    google_token_expiry: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    organization: Mapped["Organization"] = relationship(back_populates="complexes")
    courts: Mapped[list["Court"]] = relationship(back_populates="complex", cascade="all, delete-orphan")
    bookings: Mapped[list["Booking"]] = relationship(back_populates="complex")


class Court(Base):
    __tablename__ = "courts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    complex_id: Mapped[int] = mapped_column(ForeignKey("complexes.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    active: Mapped[bool] = mapped_column(default=True)

    complex: Mapped["Complex"] = relationship(back_populates="courts")
    bookings: Mapped[list["Booking"]] = relationship(back_populates="court")

    __table_args__ = (UniqueConstraint("complex_id", "name", name="uq_court_name_per_complex"),)


class SlotHold(Base):
    """Bloqueo corto (60s) mientras el cliente elige en el modal."""

    __tablename__ = "slot_holds"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    complex_id: Mapped[int] = mapped_column(ForeignKey("complexes.id"), nullable=False)
    court_id: Mapped[int] = mapped_column(ForeignKey("courts.id"), nullable=False)
    starts_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    ends_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    session_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)

    __table_args__ = (
        UniqueConstraint("court_id", "starts_at", "ends_at", name="uq_slot_hold_interval"),
    )


class Booking(Base):
    __tablename__ = "bookings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    complex_id: Mapped[int] = mapped_column(ForeignKey("complexes.id"), nullable=False)
    court_id: Mapped[int] = mapped_column(ForeignKey("courts.id"), nullable=False)
    starts_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    ends_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    customer_name: Mapped[str] = mapped_column(String(200), nullable=False)
    customer_phone: Mapped[str] = mapped_column(String(40), nullable=False)
    customer_email: Mapped[str] = mapped_column(String(200), default="")
    customer_notes: Mapped[str] = mapped_column(Text, default="")
    kind: Mapped[BookingKind] = mapped_column(
        Enum(BookingKind), default=BookingKind.PUBLIC, nullable=False
    )
    student_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    teacher_id: Mapped[int | None] = mapped_column(ForeignKey("teachers.id"), nullable=True)
    status: Mapped[BookingStatus] = mapped_column(
        Enum(BookingStatus), default=BookingStatus.PENDING, nullable=False
    )
    google_event_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    calendar_tentative: Mapped[bool] = mapped_column(default=True)
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    complex: Mapped["Complex"] = relationship(back_populates="bookings")
    court: Mapped["Court"] = relationship(back_populates="bookings")


class Teacher(Base):
    __tablename__ = "teachers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    complex_id: Mapped[int] = mapped_column(ForeignKey("complexes.id"), nullable=False)
    username: Mapped[str] = mapped_column(String(80), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(200), nullable=False)
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    active: Mapped[bool] = mapped_column(default=True)

    __table_args__ = (UniqueConstraint("complex_id", "username", name="uq_teacher_username"),)


class CalendarBlock(Base):
    """Eventos de calendario local (p. ej. reserva tentativa sin Google)."""

    __tablename__ = "calendar_blocks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    complex_id: Mapped[int] = mapped_column(ForeignKey("complexes.id"), nullable=False)
    booking_id: Mapped[int | None] = mapped_column(
        ForeignKey("bookings.id"), nullable=True, unique=True
    )
    starts_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    ends_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    title: Mapped[str] = mapped_column(String(200), default="Ocupado")
    source: Mapped[str] = mapped_column(String(50), default="local")
    is_tentative: Mapped[bool] = mapped_column(default=True)
