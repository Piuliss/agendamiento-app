from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.models import Complex
from app.services.google_calendar import build_auth_url, exchange_code_for_tokens, missing_google_env

router = APIRouter(prefix="/api/auth/google", tags=["google"])


@router.get("/start")
def google_start(complex_id: int = Query(...), db: Session = Depends(get_db)):
    settings = get_settings()
    if not settings.google_configured:
        raise HTTPException(
            status_code=503,
            detail={"message": "Google OAuth no configurado", "missing": missing_google_env()},
        )
    complex_ = db.get(Complex, complex_id)
    if not complex_:
        raise HTTPException(status_code=404, detail="Complejo no encontrado")
    url = build_auth_url(f"complex:{complex_id}")
    if not url:
        raise HTTPException(status_code=503, detail="No se pudo generar URL de OAuth")
    return RedirectResponse(url)


@router.get("/callback")
async def google_callback(
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    db: Session = Depends(get_db),
):
    settings = get_settings()
    frontend = settings.cors_origin_list[0] if settings.cors_origin_list else "http://localhost:5173"
    if error or not code or not state or not state.startswith("complex:"):
        return RedirectResponse(f"{frontend}/admin/integraciones?google=error")
    try:
        complex_id = int(state.split(":", 1)[1])
    except ValueError:
        return RedirectResponse(f"{frontend}/admin/integraciones?google=error")
    complex_ = db.get(Complex, complex_id)
    if not complex_:
        return RedirectResponse(f"{frontend}/admin/integraciones?google=error")
    try:
        tokens = await exchange_code_for_tokens(code)
    except Exception:
        return RedirectResponse(f"{frontend}/admin/integraciones?google=error")
    complex_.google_refresh_token = tokens.get("refresh_token") or complex_.google_refresh_token
    complex_.google_access_token = tokens.get("access_token")
    db.commit()
    return RedirectResponse(f"{frontend}/admin/integraciones?google=ok")
