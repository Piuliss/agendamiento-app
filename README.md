# Agendamiento de canchas (pádel)

MVP de reservas públicas y panel de administración. Cada reserva genera **siempre** dos salidas:

1. **Evento de calendario tentativo** (Google Calendar si está conectado, o calendario local en SQLite).
2. **Enlace directo a WhatsApp** (`wa.me`) al número del complejo, con el detalle del turno y del cliente.

Los datos de contacto del cliente (nombre, teléfono, email y comentarios) se guardan en la base de datos y se muestran en el panel junto a las reservas pendientes.

## Requisitos

- Node.js 20+
- Python 3.11+

## Backend (FastAPI)

```bash
cd backend
cp .env.example .env
pip install -r requirements.txt
python3 -m uvicorn app.main:app --reload --port 8000
```

Variables útiles en `.env`:

| Variable | Descripción |
|----------|-------------|
| `ADMIN_USERNAME` / `ADMIN_PASSWORD` | Login del panel (por defecto `admin` / `admin`) |
| `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` | OAuth Google (opcional) |
| `LUMI_API_URL` / `LUMI_API_TOKEN` | Adaptador ERP Lumi (stub sin spec) |

API: `http://localhost:8000` — documentación en `/docs`.

## Frontend (React + Vite)

```bash
cd frontend
npm install
npm run dev
```

UI: `http://localhost:5173`

- Reserva pública de ejemplo: `http://localhost:5173/r/demo`
- Panel: `http://localhost:5173/admin/login`

## Tests

```bash
cd backend
python3 -m pytest
```

Incluye pruebas de solapamiento de reservas, huecos disponibles y creación de salidas (calendario + WhatsApp).

## Estructura

- `backend/app` — API, modelos, disponibilidad, integraciones
- `backend/app/adapters/lumi.py` — interfaz Lumi (sin endpoints inventados)
- `frontend/src` — flujo público y back office

## Pendiente para producción

- Completar OAuth Google (refresh de tokens) y free/busy remoto
- Spec y endpoints reales de Lumi
- Multi-complejo completo en UI (el modelo ya soporta varios complejos por organización)
