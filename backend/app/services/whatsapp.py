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
    lines.append(
        f"Horario: {booking.starts_at.strftime('%H:%M')}–{booking.ends_at.strftime('%H:%M')}"
    )
    lines.append(f"ID reserva: {booking.id}")
    return "\n".join(lines)


def build_cart_whatsapp_message(
    complex_: Complex,
    contact_name: str,
    contact_phone: str,
    items: list[tuple[Court, Booking]],
    contact_email: str = "",
    contact_notes: str = "",
) -> str:
    lines = [
        "Hola, quiero confirmar mis reservas de pádel.",
        f"Complejo: {complex_.name}",
        f"Nombre: {contact_name}",
        f"Teléfono: {contact_phone}",
    ]
    if contact_email:
        lines.append(f"Email: {contact_email}")
    if contact_notes:
        lines.append(f"Notas: {contact_notes}")
    lines.append("")
    lines.append(f"Turnos solicitados ({len(items)}):")
    for i, (court, booking) in enumerate(items, 1):
        fecha = booking.starts_at.strftime("%d/%m/%Y")
        h0 = booking.starts_at.strftime("%H:%M")
        h1 = booking.ends_at.strftime("%H:%M")
        lines.append(
            f"{i}. {court.name} — {fecha} {h0}–{h1} (ID {booking.id})"
        )
    return "\n".join(lines)


def whatsapp_url(phone: str, text: str) -> str | None:
    digits = "".join(c for c in phone if c.isdigit())
    if not digits:
        return None
    return f"https://wa.me/{digits}?text={quote(text)}"
