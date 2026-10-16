"""Integración Google Calendar (OAuth + eventos tentativos)."""

from datetime import datetime
from urllib.parse import urlencode

import httpx

from app.config import get_settings
from app.models import Booking, Complex

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_CALENDAR_API = "https://www.googleapis.com/calendar/v3"


def missing_google_env() -> list[str]:
    settings = get_settings()
    missing = []
    if not settings.google_client_id:
        missing.append("GOOGLE_CLIENT_ID")
    if not settings.google_client_secret:
        missing.append("GOOGLE_CLIENT_SECRET")
    return missing


def build_auth_url(state: str) -> str | None:
    settings = get_settings()
    if not settings.google_configured:
        return None
    params = {
        "client_id": settings.google_client_id,
        "redirect_uri": settings.google_redirect_uri,
        "response_type": "code",
        "scope": "https://www.googleapis.com/auth/calendar.events",
        "access_type": "offline",
        "prompt": "consent",
        "state": state,
    }
    return f"{GOOGLE_AUTH_URL}?{urlencode(params)}"


async def exchange_code_for_tokens(code: str) -> dict:
    settings = get_settings()
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            GOOGLE_TOKEN_URL,
            data={
                "code": code,
                "client_id": settings.google_client_id,
                "client_secret": settings.google_client_secret,
                "redirect_uri": settings.google_redirect_uri,
                "grant_type": "authorization_code",
            },
        )
        resp.raise_for_status()
        return resp.json()


def complex_has_google(complex_: Complex) -> bool:
    return bool(complex_.google_refresh_token or complex_.google_access_token)


async def create_tentative_event(
    complex_: Complex,
    booking: Booking,
    court_name: str,
    summary: str,
) -> str | None:
    if not complex_has_google(complex_) or not complex_.google_access_token:
        return None
    calendar_id = complex_.google_calendar_id or "primary"
    body = {
        "summary": summary,
        "description": (
            f"Reserva pendiente — {court_name}\n"
            f"Cliente: {booking.customer_name}\n"
            f"Tel: {booking.customer_phone}"
        ),
        "start": {"dateTime": booking.starts_at.isoformat() + "Z", "timeZone": "UTC"},
        "end": {"dateTime": booking.ends_at.isoformat() + "Z", "timeZone": "UTC"},
        "status": "tentative",
    }
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{GOOGLE_CALENDAR_API}/calendars/{calendar_id}/events",
            headers={"Authorization": f"Bearer {complex_.google_access_token}"},
            json=body,
        )
        if resp.status_code >= 400:
            return None
        data = resp.json()
        return data.get("id")


async def update_event_status(
    complex_: Complex,
    event_id: str,
    confirmed: bool,
) -> bool:
    if not complex_has_google(complex_) or not complex_.google_access_token:
        return False
    calendar_id = complex_.google_calendar_id or "primary"
    body = {"status": "confirmed" if confirmed else "cancelled"}
    async with httpx.AsyncClient() as client:
        resp = await client.patch(
            f"{GOOGLE_CALENDAR_API}/calendars/{calendar_id}/events/{event_id}",
            headers={"Authorization": f"Bearer {complex_.google_access_token}"},
            json=body,
        )
        return resp.status_code < 400
