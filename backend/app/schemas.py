from datetime import date, datetime, time
from typing import Literal

from pydantic import BaseModel, Field

from app.models import BookingStatus


class CourtOut(BaseModel):
    id: int
    name: str
    active: bool

    model_config = {"from_attributes": True}


class ComplexPublicOut(BaseModel):
    id: int
    name: str
    slug: str
    whatsapp_number: str
    hours_start: time
    hours_end: time
    courts: list[CourtOut]

    model_config = {"from_attributes": True}


class SlotOut(BaseModel):
    starts_at: datetime
    ends_at: datetime


class AvailabilityDayOut(BaseModel):
    date: date
    court_id: int
    slots: list[SlotOut]


class BookingCreate(BaseModel):
    court_id: int
    starts_at: datetime
    customer_name: str = Field(min_length=2, max_length=200)
    customer_phone: str = Field(min_length=6, max_length=40)
    customer_email: str = Field(default="", max_length=200)
    customer_notes: str = Field(default="", max_length=500)


class BookingPublicOut(BaseModel):
    id: int
    court_id: int
    court_name: str
    starts_at: datetime
    ends_at: datetime
    customer_name: str
    customer_phone: str
    customer_email: str
    status: BookingStatus
    whatsapp_url: str
    whatsapp_message: str
    calendar_mode: str
    calendar_tentative: bool
    message: str

    model_config = {"from_attributes": True}


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class ComplexAdminOut(BaseModel):
    id: int
    name: str
    slug: str
    whatsapp_number: str
    contact_email: str
    hours_start: time
    hours_end: time
    google_calendar_id: str | None
    google_connected: bool
    courts: list[CourtOut]

    model_config = {"from_attributes": True}


class ComplexUpdate(BaseModel):
    name: str | None = None
    whatsapp_number: str | None = None
    contact_email: str | None = None
    hours_start: time | None = None
    hours_end: time | None = None


class CourtCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)


class CourtUpdate(BaseModel):
    name: str | None = None
    active: bool | None = None


class BookingAdminOut(BaseModel):
    id: int
    court_id: int
    court_name: str
    starts_at: datetime
    ends_at: datetime
    customer_name: str
    customer_phone: str
    customer_email: str
    customer_notes: str
    status: BookingStatus
    calendar_tentative: bool
    notes: str

    model_config = {"from_attributes": True}


class BookingAction(BaseModel):
    action: Literal["confirm", "reject"]
    notes: str = ""


class GoogleStatusOut(BaseModel):
    configured: bool
    connected: bool
    missing_env: list[str]
    auth_url: str | None = None
    calendar_mode: Literal["google", "local"]


class IntegrationStatusOut(BaseModel):
    google: GoogleStatusOut
    lumi: dict[str, str | bool]
