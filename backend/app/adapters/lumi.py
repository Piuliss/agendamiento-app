"""
Adaptador ERP Lumi (stub configurable).

payment_reference / transaction_reference: solo voucher numérico del procesador.
Texto libre va en notes. Sin número → referencia vacía.
"""

from dataclasses import dataclass

from app.config import get_settings


@dataclass
class LumiPaymentSync:
    booking_id: int
    amount: float | None = None
    payment_reference: str = ""
    notes: str = ""


class LumiAdapter:
    def __init__(self) -> None:
        settings = get_settings()
        self.base_url = settings.lumi_api_url.rstrip("/")
        self.token = settings.lumi_api_token

    @property
    def configured(self) -> bool:
        return bool(self.base_url and self.token)

    async def push_booking_payment(self, payload: LumiPaymentSync) -> dict:
        if not self.configured:
            return {"ok": False, "reason": "Lumi no configurado (LUMI_API_URL, LUMI_API_TOKEN)"}
        # Endpoint real pendiente de spec del cliente
        return {"ok": False, "reason": "Adaptador definido; endpoint no implementado sin spec"}
