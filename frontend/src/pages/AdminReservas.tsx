import { useEffect, useState } from 'react';
import { api } from '../api';
import type { BookingAdmin } from '../api';

function fmt(iso: string) {
  return new Date(iso).toLocaleString('es-PY', { dateStyle: 'short', timeStyle: 'short' });
}

export function AdminReservas() {
  const token = localStorage.getItem('admin_token')!;
  const [bookings, setBookings] = useState<BookingAdmin[]>([]);

  async function load() {
    setBookings(await api.listBookings(token));
  }

  useEffect(() => {
    load();
  }, []);

  async function act(id: number, action: 'confirm' | 'reject') {
    await api.bookingAction(token, id, action);
    await load();
  }

  const pending = bookings.filter((b) => b.status === 'pending');

  return (
    <div>
      <h1>Reservas</h1>
      <p>Contactos guardados en base de datos junto a cada reserva pendiente.</p>

      <h2>Pendientes ({pending.length})</h2>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Fecha</th>
              <th>Cancha</th>
              <th>Cliente</th>
              <th>Teléfono</th>
              <th>Email</th>
              <th>Notas cliente</th>
              <th>Calendario</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {pending.map((b) => (
              <tr key={b.id}>
                <td>{fmt(b.starts_at)}</td>
                <td>{b.court_name}</td>
                <td>{b.customer_name}</td>
                <td><a href={`tel:${b.customer_phone}`}>{b.customer_phone}</a></td>
                <td>{b.customer_email || '—'}</td>
                <td>{b.customer_notes || '—'}</td>
                <td>{b.calendar_tentative ? 'Tentativo' : '—'}</td>
                <td className="actions">
                  <button className="btn small" onClick={() => act(b.id, 'confirm')}>Confirmar</button>
                  <button className="btn small ghost" onClick={() => act(b.id, 'reject')}>Rechazar</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <h2>Todas</h2>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Estado</th>
              <th>Fecha</th>
              <th>Cliente</th>
              <th>Teléfono</th>
            </tr>
          </thead>
          <tbody>
            {bookings.map((b) => (
              <tr key={b.id}>
                <td>{b.status}</td>
                <td>{fmt(b.starts_at)}</td>
                <td>{b.customer_name}</td>
                <td>{b.customer_phone}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
