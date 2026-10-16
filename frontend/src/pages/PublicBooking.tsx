import { useEffect, useMemo, useState } from 'react';
import { useParams } from 'react-router-dom';
import { api } from '../api';
import type { AvailabilityDay, BookingResult, ComplexPublic } from '../api';

function todayIso() {
  return new Date().toISOString().slice(0, 10);
}

function formatSlot(iso: string) {
  const d = new Date(iso);
  return d.toLocaleString('es-PY', {
    weekday: 'short',
    day: '2-digit',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit',
  });
}

export function PublicBooking() {
  const { slug = 'demo' } = useParams();
  const [complex, setComplex] = useState<ComplexPublic | null>(null);
  const [courtId, setCourtId] = useState<number | null>(null);
  const [availability, setAvailability] = useState<AvailabilityDay[]>([]);
  const [selectedSlot, setSelectedSlot] = useState<string | null>(null);
  const [name, setName] = useState('');
  const [phone, setPhone] = useState('');
  const [email, setEmail] = useState('');
  const [notes, setNotes] = useState('');
  const [result, setResult] = useState<BookingResult | null>(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    api.getComplex(slug).then((c) => {
      setComplex(c);
      const first = c.courts[0];
      if (first) setCourtId(first.id);
    }).catch(() => setError('No se encontró el complejo.'));
  }, [slug]);

  useEffect(() => {
    if (!courtId) return;
    api.getAvailability(slug, courtId, todayIso()).then(setAvailability).catch(() => setError('Sin disponibilidad'));
  }, [slug, courtId]);

  const slots = useMemo(
    () => availability.flatMap((d) => d.slots.map((s) => ({ ...s, day: d.date }))),
    [availability],
  );

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!courtId || !selectedSlot) return;
    setLoading(true);
    setError('');
    try {
      const booking = await api.createBooking(slug, {
        court_id: courtId,
        starts_at: selectedSlot,
        customer_name: name,
        customer_phone: phone,
        customer_email: email,
        customer_notes: notes,
      });
      setResult(booking);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'No se pudo reservar');
    } finally {
      setLoading(false);
    }
  }

  if (result) {
    return (
      <main className="page">
        <div className="card success">
          <h1>Reserva pendiente</h1>
          <p>{result.message}</p>
          <ul className="detail-list">
            <li><strong>Cancha:</strong> {result.court_name}</li>
            <li><strong>Horario:</strong> {formatSlot(result.starts_at)}</li>
            <li><strong>Calendario:</strong> evento tentativo ({result.calendar_mode})</li>
          </ul>
          <a className="btn primary" href={result.whatsapp_url} target="_blank" rel="noreferrer">
            Confirmar por WhatsApp
          </a>
        </div>
      </main>
    );
  }

  return (
    <main className="page">
      <header className="hero-header">
        <h1>{complex?.name ?? 'Reservar cancha'}</h1>
        <p>Elegí cancha, horario y tus datos de contacto.</p>
      </header>

      {error && <p className="error">{error}</p>}

      <section className="card">
        <label>
          Cancha
          <select
            value={courtId ?? ''}
            onChange={(e) => {
              setSelectedSlot(null);
              setCourtId(Number(e.target.value));
            }}
          >
            {complex?.courts.map((c) => (
              <option key={c.id} value={c.id}>{c.name}</option>
            ))}
          </select>
        </label>

        <h2>Horarios disponibles</h2>
        <div className="slot-grid">
          {slots.length === 0 && <p>No hay turnos libres en los próximos días.</p>}
          {slots.map((s) => (
            <button
              type="button"
              key={s.starts_at}
              className={`slot ${selectedSlot === s.starts_at ? 'selected' : ''}`}
              onClick={() => setSelectedSlot(s.starts_at)}
            >
              {formatSlot(s.starts_at)}
            </button>
          ))}
        </div>

        <form onSubmit={submit} className="form-grid">
          <label>
            Nombre
            <input required value={name} onChange={(e) => setName(e.target.value)} />
          </label>
          <label>
            Teléfono
            <input required value={phone} onChange={(e) => setPhone(e.target.value)} />
          </label>
          <label>
            Email (opcional)
            <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} />
          </label>
          <label className="full">
            Comentarios (opcional)
            <textarea value={notes} onChange={(e) => setNotes(e.target.value)} rows={2} />
          </label>
          <button className="btn primary" type="submit" disabled={!selectedSlot || loading}>
            {loading ? 'Enviando…' : 'Solicitar reserva'}
          </button>
        </form>
      </section>
    </main>
  );
}
