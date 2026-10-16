from urllib.parse import quote

from app.models import Booking, Complex, Court


def build_whatsapp_message(complex_: Complex, court: Court, booking: Booking) -> str:
    fecha = booking.starts_at.strftime("%d/%m/%Y")
    hora = booking.starts_at.strftime("%H:%M")
    lines = [
        "Hola, quiero confirmar mi reserva de pádel.",
        f"Complejo: {complex_.name}",
        f"Cancha: {court.name}",
        f"Fecha: {fecha}",
        f"Hora: {hora}",
        f"Nombre: {booking.customer_name}",
        f"Teléfono: {booking.customer_phone}",
    ]
    if booking.customer_email:
        lines.append(f"Email: {booking.customer_email}")
    if booking.customer_notes:
        lines.append(f"Notas: {booking.customer_notes}")
    lines.append(f"ID reserva: {booking.id}")
    return "\n".join(lines)


def whatsapp_url(phone: str, text: str) -> str | None:
    digits = "".join(c for c in phone if c.isdigit())
    if not digits:
        return None
    return f"https://wa.me/{digits}?text={quote(text)}"
